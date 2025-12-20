# main.py - Version 2.3.2
# Date: 2025-12-19
# Changements: Suppression configuration PLAYWRIGHT_BROWSERS_PATH (utilise path par défaut)


import os
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/opt/render/project/src/browsers'
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from anthropic import Anthropic
from playwright.sync_api import sync_playwright
import time
import re
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
SENDGRID_FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL')
GARMIN_USERNAME = os.getenv('GARMIN_USERNAME')
GARMIN_PASSWORD = os.getenv('GARMIN_PASSWORD')

# Initialisation des clients
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

def send_email(to_email, subject, content):
    """Envoie un email via SendGrid"""
    try:
        message = Mail(
            from_email=SENDGRID_FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            plain_text_content=content
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"Email envoyé à {to_email} - Status: {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"Erreur envoi email: {str(e)}")
        return False

def send_inreach_message_playwright(imei, message_text):
    """Envoie un message via inReach en utilisant Playwright"""
    logger.info(f"Envoi message Playwright vers IMEI: {imei}")
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            # 1. Page de login
            logger.info("Accès page login Garmin")
            page.goto('https://explore.garmin.com/login', timeout=30000)
            page.wait_for_load_state('networkidle')
            
            # Accepter les cookies si présents
            try:
                cookie_button = page.locator('button:has-text("Accept")')
                if cookie_button.is_visible(timeout=2000):
                    cookie_button.click()
                    logger.info("Cookies acceptés")
            except:
                pass
            
            # 2. Remplir login
            logger.info("Remplissage formulaire login")
            page.fill('input[type="email"]', GARMIN_USERNAME)
            page.fill('input[type="password"]', GARMIN_PASSWORD)
            page.click('button[type="submit"]')
            
            # Attendre redirection après login
            page.wait_for_load_state('networkidle', timeout=30000)
            time.sleep(2)
            
            # 3. Navigation vers messages
            logger.info("Navigation vers page messages")
            page.goto('https://explore.garmin.com/messages', timeout=30000)
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            
            # 4. Cliquer sur "Compose"
            logger.info("Clic sur bouton Compose")
            page.click('button:has-text("Compose")')
            time.sleep(2)
            
            # 5. Sélectionner le device
            logger.info(f"Sélection device IMEI: {imei}")
            page.click(f'text="{imei}"')
            time.sleep(1)
            
            # 6. Remplir le message
            logger.info("Saisie du message")
            page.fill('textarea[placeholder*="message"]', message_text)
            time.sleep(1)
            
            # 7. Envoyer
            logger.info("Envoi du message")
            page.click('button:has-text("Send")')
            
            # Attendre confirmation
            time.sleep(3)
            
            browser.close()
            logger.info("Message envoyé avec succès via Playwright")
            return True
            
        except Exception as e:
            logger.error(f"Erreur Playwright: {str(e)}")
            try:
                browser.close()
            except:
                pass
            return False

def call_claude_api(user_message, conversation_history=None):
    """Appelle l'API Claude avec historique de conversation"""
    try:
        messages = conversation_history if conversation_history else []
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        system_prompt = """Tu es un assistant météo marine spécialisé pour les navigateurs.
Tu réponds de manière concise et précise aux questions sur:
- Les prévisions météo marines
- Les fichiers GRIB
- La navigation hauturière
- Les conditions de mer

Réponds toujours en français, de manière claire et directe.
Limite tes réponses à 300 caractères maximum pour transmission satellite."""

        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=system_prompt,
            messages=messages
        )
        
        assistant_message = response.content[0].text
        messages.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        return assistant_message, messages
        
    except Exception as e:
        logger.error(f"Erreur API Claude: {str(e)}")
        return f"Erreur: {str(e)}", messages

# Stockage temporaire des conversations (en production, utiliser Redis/DB)
conversations = {}

@app.route('/webhook/inreach', methods=['POST'])
def inreach_webhook():
    """Webhook pour recevoir les messages inReach"""
    try:
        data = request.json
        logger.info(f"Webhook reçu: {json.dumps(data, indent=2)}")
        
        # Extraction des informations
        imei = data.get('imei')
        message_text = data.get('text', '').strip()
        timestamp = data.get('timestamp')
        
        if not imei or not message_text:
            logger.error("IMEI ou message manquant")
            return jsonify({'error': 'IMEI or message missing'}), 400
        
        logger.info(f"Message de {imei}: {message_text}")
        
        # Gestion de l'historique de conversation
        conversation_id = imei
        conversation_history = conversations.get(conversation_id, [])
        
        # Appel à Claude
        response_text, updated_history = call_claude_api(message_text, conversation_history)
        
        # Sauvegarde de l'historique
        conversations[conversation_id] = updated_history
        
        logger.info(f"Réponse Claude: {response_text}")
        
        # Envoi de la réponse via inReach
        success = send_inreach_message_playwright(imei, response_text)
        
        if success:
            return jsonify({
                'status': 'success',
                'response_sent': response_text,
                'conversation_length': len(updated_history)
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to send response'
            }), 500
            
    except Exception as e:
        logger.error(f"Erreur webhook: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/test/chat', methods=['POST'])
def test_chat():
    """Endpoint de test pour l'intégration chat"""
    try:
        data = request.json
        imei = data.get('imei', 'TEST_IMEI')
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': 'Message required'}), 400
        
        conversation_id = imei
        conversation_history = conversations.get(conversation_id, [])
        
        response_text, updated_history = call_claude_api(message, conversation_history)
        conversations[conversation_id] = updated_history
        
        return jsonify({
            'status': 'success',
            'response': response_text,
            'conversation_length': len(updated_history)
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur test chat: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/test/send', methods=['POST'])
def test_send():
    """Endpoint de test pour l'envoi de messages"""
    try:
        data = request.json
        imei = data.get('imei')
        message = data.get('message')
        
        if not imei or not message:
            return jsonify({'error': 'IMEI and message required'}), 400
        
        success = send_inreach_message_playwright(imei, message)
        
        if success:
            return jsonify({'status': 'success', 'message': 'Message sent'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Failed to send'}), 500
            
    except Exception as e:
        logger.error(f"Erreur test send: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'active_conversations': len(conversations)
    }), 200

@app.route('/', methods=['GET'])
def home():
    """Page d'accueil"""
    return jsonify({
        'service': 'GRIB inReach Service with Chat',
        'version': '2.3.1',
        'endpoints': {
            'webhook': '/webhook/inreach',
            'test_chat': '/test/chat',
            'test_send': '/test/send',
            'health': '/health'
        }
    }), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
