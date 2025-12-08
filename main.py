#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service de traitement automatique des fichiers GRIB pour Garmin InReach
avec module Claude AI intégré
Surveille les emails, télécharge les fichiers GRIB, les traite avec Saildocs, 
et renvoie les données météo vers le Garmin InReach.
NOUVEAU: Support des requêtes Claude AI via "claude <max_words>: <question>"
"""

import os
import sys
import time
import imaplib
import email
import smtplib
import base64
import zlib
import re
import requests
import schedule
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from threading import Thread, Event
from urllib.parse import urlparse, parse_qs
from flask import Flask, jsonify

# ==========================================
# CONFIGURATION
# ==========================================

# Variables d'environnement (définies dans Render)
GARMIN_USERNAME = os.environ.get('GARMIN_USERNAME', 'garminced@gmail.com')
GARMIN_PASSWORD = os.environ.get('GARMIN_PASSWORD')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')  # NOUVEAU: Clé Anthropic

# Configuration Email - SMTP SSL sur port 465 (comme Termux)
GMAIL_HOST = "smtp.gmail.com"
GMAIL_PORT = 465  # SSL direct
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

# Adresses Saildocs et Garmin
SAILDOCS_EMAIL = "query@saildocs.com"
SAILDOCS_RESPONSE_EMAIL = "query-reply@saildocs.com"

# Configuration messages inReach
MAX_MESSAGE_LENGTH = 120
DELAY_BETWEEN_MESSAGES = 5

# Configuration du port pour Render
PORT = int(os.environ.get('PORT', 10000))

# Headers HTTP pour Garmin inReach
INREACH_HEADERS = {
    'authority': 'eur.explore.garmin.com',
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'origin': 'https://eur.explore.garmin.com',
    'sec-ch-ua': '"Chromium";v="106", "Not;A=Brand";v="99", "Google Chrome";v="106.0.5249.119"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest',
}

INREACH_COOKIES = {
    'BrowsingMode': 'Desktop',
}

# ==========================================
# APPLICATION FLASK (pour le Health Check)
# ==========================================

app = Flask(__name__)

# Variable globale pour le statut
last_check_time = None
last_status = "Démarrage..."
thread_started = Event()  # Event pour synchroniser le démarrage du thread

@app.route('/')
def index():
    """Page d'accueil"""
    return jsonify({
        "service": "GRIB InReach Service with Claude AI",
        "status": "running",
        "last_check": str(last_check_time),
        "message": last_status,
        "features": ["GRIB files", "Claude AI queries"]
    })

@app.route('/health')
def health():
    """Endpoint de santé pour le monitoring"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "last_check": str(last_check_time)
    }), 200

@app.route('/status')
def status():
    """Statut détaillé du service"""
    return jsonify({
        "service": "GRIB InReach Service with Claude AI",
        "status": "running",
        "current_status": last_status,
        "last_check_time": str(last_check_time) if last_check_time else "Aucune vérification encore",
        "garmin_username": GARMIN_USERNAME if GARMIN_USERNAME else "Non configuré",
        "sendgrid_configured": "✅ Oui" if os.environ.get('SENDGRID_API_KEY') else "❌ Non",
        "anthropic_configured": "✅ Oui" if ANTHROPIC_API_KEY else "❌ Non",
        "verification_frequency": "Toutes les heures",
        "next_check": "Dans moins d'1 heure" if last_check_time else "Imminent",
        "service_active_since": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "features": {
            "grib": "Format: ecmwf:24n,34n,72w,60w|8,8|12,48|wind,press",
            "claude": "Format: claude <max_words>: <question>"
        },
        "instructions": "Le service vérifie automatiquement les emails toutes les heures. Consultez les logs Render pour plus de détails."
    })

# ==========================================
# MODULE CLAUDE AI
# ==========================================

def query_claude(prompt, max_words=50):
    """
    Envoie une requête à l'API Claude d'Anthropic et retourne la réponse
    
    Args:
        prompt (str): La question à poser à Claude
        max_words (int): Nombre maximum de mots pour la réponse TOTALE (sera découpée en messages)
    
    Returns:
        list: Liste de messages (max 4) ou un seul message d'erreur
    """
    global last_status
    
    if not ANTHROPIC_API_KEY:
        error_msg = "❌ ERREUR: Variable ANTHROPIC_API_KEY non définie"
        print(error_msg)
        last_status = error_msg
        return ["Claude AI non configuré. Veuillez définir ANTHROPIC_API_KEY."]
    
    try:
        print(f"🤖 Envoi de la requête Claude: {prompt[:50]}...")
        
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Construction du système pour une réponse complète
        system_message = f"You are a helpful assistant for sailors at sea. Provide clear, practical, and complete answers in approximately {max_words} words. Be informative and well-structured. The response will be sent via satellite in multiple messages if needed."
        
        data = {
            "model": "claude-sonnet-4-20250514",  # Claude Sonnet 4.5 (le plus récent et efficace)
            "max_tokens": max_words * 3,  # Approximation: marge pour assurer la limite en mots
            "system": system_message,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            answer = result['content'][0]['text'].strip()
            
            # Récupérer les informations d'usage
            usage = result.get('usage', {})
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            
            # Calcul du coût (prix Claude Sonnet 4.5 en décembre 2024)
            # Input: $3 per million tokens
            # Output: $15 per million tokens
            input_cost = (input_tokens / 1_000_000) * 3.0
            output_cost = (output_tokens / 1_000_000) * 15.0
            total_cost = input_cost + output_cost
            
            print(f"✅ Réponse Claude reçue: {len(answer)} caractères")
            print(f"💰 Tokens: {input_tokens} input + {output_tokens} output")
            print(f"💵 Coût: ${total_cost:.6f} (${input_cost:.6f} + ${output_cost:.6f})")
            
            # Récupérer le solde du compte (nécessite une requête supplémentaire)
            try:
                balance_url = "https://api.anthropic.com/v1/organization/usage"
                balance_response = requests.get(balance_url, headers={"x-api-key": ANTHROPIC_API_KEY}, timeout=10)
                
                if balance_response.status_code == 200:
                    balance_data = balance_response.json()
                    # L'API retourne les crédits en centimes
                    balance_cents = balance_data.get('balance', {}).get('amount', 0)
                    balance_dollars = balance_cents / 100.0
                    print(f"💳 Crédit restant: ${balance_dollars:.2f}")
                    
                    # Ajouter le crédit au dernier message
                    credit_info = f"\n[Cost: ${total_cost:.4f} | Credit: ${balance_dollars:.2f}]"
                else:
                    print(f"⚠️  Impossible de récupérer le solde (Status: {balance_response.status_code})")
                    credit_info = f"\n[Cost: ${total_cost:.4f}]"
            except Exception as e:
                print(f"⚠️  Erreur récupération solde: {e}")
                credit_info = f"\n[Cost: ${total_cost:.4f}]"
            
            # Découper la réponse en plusieurs messages si nécessaire
            # Limite: environ 110 caractères par message pour laisser de la marge
            max_chars_per_message = 110
            messages = []
            
            # Découper par phrases pour éviter de couper au milieu d'une phrase
            sentences = re.split(r'([.!?]\s+)', answer)
            current_message = ""
            
            for i in range(0, len(sentences), 2):
                sentence = sentences[i]
                if i + 1 < len(sentences):
                    sentence += sentences[i + 1]  # Ajouter le séparateur
                
                # Si ajouter cette phrase dépasse la limite
                if len(current_message) + len(sentence) > max_chars_per_message:
                    if current_message:
                        messages.append(current_message.strip())
                        current_message = sentence
                    else:
                        # Phrase trop longue, la couper par mots
                        words = sentence.split()
                        temp_msg = ""
                        for word in words:
                            if len(temp_msg) + len(word) + 1 <= max_chars_per_message:
                                temp_msg += word + " "
                            else:
                                if temp_msg:
                                    messages.append(temp_msg.strip())
                                temp_msg = word + " "
                        current_message = temp_msg
                else:
                    current_message += sentence
            
            # Ajouter le dernier message
            if current_message:
                messages.append(current_message.strip())
            
            # Limiter à 4 messages maximum
            if len(messages) > 4:
                print(f"⚠️  Réponse trop longue ({len(messages)} messages), truncation à 4 messages")
                # Recombiner et tronquer
                full_text = " ".join(messages)
                messages = []
                for i in range(4):
                    start = i * max_chars_per_message
                    end = (i + 1) * max_chars_per_message
                    if start < len(full_text):
                        msg = full_text[start:end].strip()
                        if i == 3 and end < len(full_text):
                            msg += "..."
                        messages.append(msg)
            
            # Ajouter l'info de coût au dernier message
            if messages:
                messages[-1] += credit_info
            
            print(f"📨 Réponse découpée en {len(messages)} message(s)")
            for i, msg in enumerate(messages, 1):
                print(f"   Message {i}/{len(messages)}: {len(msg)} chars")
            
            last_status = f"✅ Réponse Claude envoyée ({len(messages)} messages, ${total_cost:.4f})"
            return messages
        else:
            error_msg = f"❌ Erreur Anthropic API: Status {response.status_code}"
            print(f"{error_msg} - {response.text}")
            last_status = error_msg
            return [f"Erreur Claude: {response.status_code}"]
            
    except Exception as e:
        error_msg = f"❌ Erreur lors de la requête Claude: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        last_status = error_msg
        return [f"Erreur: {str(e)}"]

def parse_claude_request(body):
    """
    Parse une requête Claude du format: claude <max_words>: <question>
    
    Args:
        body (str): Le corps de l'email
    
    Returns:
        tuple: (max_words, question) ou (None, None) si pas de requête Claude
    """
    # Pattern: claude 20: What are trade winds?
    # Accepte aussi "gpt" pour compatibilité avec l'ancien code
    claude_pattern = re.compile(r'(claude|gpt)\s+(\d+)\s*:\s*(.+)', re.IGNORECASE | re.DOTALL)
    match = claude_pattern.search(body)
    
    if match:
        max_words = int(match.group(2))
        question = match.group(3).strip()
        
        # Nettoyer la question (enlever les retours à la ligne, etc.)
        question = ' '.join(question.split())
        
        return max_words, question
    
    return None, None

# ==========================================
# FONCTIONS DE TRAITEMENT GRIB
# ==========================================

def check_credentials():
    """Vérifie que les identifiants Garmin sont configurés"""
    global last_status
    if not GARMIN_USERNAME or not GARMIN_PASSWORD:
        last_status = "❌ ERREUR: Variables GARMIN_USERNAME et GARMIN_PASSWORD non définies"
        print(last_status)
        return False
    print(f"✅ Identifiants Garmin configurés pour: {GARMIN_USERNAME}")
    return True

def connect_gmail():
    """Connexion à Gmail via IMAP"""
    global last_status
    try:
        print(f"📧 Connexion IMAP à Gmail: {GARMIN_USERNAME}")
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(GARMIN_USERNAME, GARMIN_PASSWORD)
        print("✅ Connexion IMAP réussie")
        return mail
    except Exception as e:
        last_status = f"❌ Erreur connexion IMAP: {str(e)}"
        print(last_status)
        return None

def check_for_requests(mail):
    """
    Vérifie les nouveaux emails avec requêtes GRIB ou Claude depuis inReach
    MODIFIÉ: Gère maintenant les deux types de requêtes
    """
    global last_status, last_check_time
    
    try:
        mail.select("inbox")
        print("🔍 Recherche des emails non lus...")
        status, messages = mail.search(None, 'UNSEEN')
        
        if status != "OK":
            last_status = "❌ Erreur lors de la recherche d'emails"
            return []
        
        email_ids = messages[0].split()
        print(f"📬 {len(email_ids)} email(s) non lu(s) trouvé(s)")
        
        requests_list = []
        
        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            
            if status != "OK":
                continue
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Vérifier que l'email vient bien d'inReach
                    from_addr = msg.get('From', '').lower()
                    if 'inreach' not in from_addr and 'garmin' not in from_addr:
                        print(f"⏭ Email ignoré (pas inReach): {from_addr}")
                        continue
                    
                    # Récupérer le corps
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                break
                    else:
                        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    
                    # DEBUG: Afficher le contenu de l'email
                    print(f"\n📧 EMAIL TROUVÉ:")
                    print(f"  From: {msg.get('From', 'Unknown')}")
                    print(f"  Subject: {msg.get('Subject', 'No subject')}")
                    print(f"  Body (200 premiers chars): {body[:200]}")
                    
                    # Extraire URL de réponse
                    reply_url_pattern = re.compile(r'https://[^\s]+garmin\.com/textmessage/txtmsg\?[^\s]+')
                    reply_match = reply_url_pattern.search(body)
                    
                    if not reply_match:
                        print("⚠ Email sans URL de réponse valide")
                        continue
                    
                    reply_url = reply_match.group(0)
                    
                    # NOUVEAU: Vérifier si c'est une requête Claude
                    max_words, question = parse_claude_request(body)
                    
                    if question:
                        print(f"✅ Requête Claude trouvée: {question[:50]}...")
                        print(f"  Max words: {max_words}")
                        print(f"  URL: {reply_url[:60]}...")
                        
                        requests_list.append({
                            'type': 'claude',
                            'max_words': max_words,
                            'question': question,
                            'reply_url': reply_url
                        })
                        continue
                    
                    # Chercher requête GRIB
                    grib_pattern = re.compile(r'(ecmwf|gfs|icon):[^\s\n]+', re.IGNORECASE)
                    match = grib_pattern.search(body)
                    
                    if not match:
                        # Si pas trouvé, essayer de chercher sur plusieurs lignes
                        body_single_line = body.replace('\n', ' ').replace('\r', ' ')
                        match = grib_pattern.search(body_single_line)
                    
                    if match:
                        grib_request = match.group(0)
                        print(f"✅ Requête GRIB trouvée: {grib_request}")
                        print(f"  URL: {reply_url[:60]}...")
                        
                        requests_list.append({
                            'type': 'grib',
                            'request': grib_request,
                            'reply_url': reply_url
                        })
                    else:
                        print(f"⚠ Email inReach sans requête valide (ni GRIB ni Claude)")
        
        last_check_time = datetime.now()
        grib_count = sum(1 for r in requests_list if r['type'] == 'grib')
        claude_count = sum(1 for r in requests_list if r['type'] == 'claude')
        last_status = f"✅ Vérification terminée - {grib_count} GRIB, {claude_count} Claude"
        
        return requests_list
        
    except Exception as e:
        last_status = f"❌ Erreur lors de la vérification des emails: {str(e)}"
        print(last_status)
        import traceback
        traceback.print_exc()
        return []

def send_to_saildocs(grib_request):
    """Envoie la requête à Saildocs via SendGrid API"""
    global last_status
    
    try:
        print(f"🌊 Envoi de la demande GRIB à Saildocs via SendGrid...")
        
        sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
        if not sendgrid_api_key:
            last_status = "❌ ERREUR: Variable SENDGRID_API_KEY non définie"
            print(last_status)
            return False
        
        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {sendgrid_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "personalizations": [{
                "to": [{"email": SAILDOCS_EMAIL}],
                "subject": "GRIB Request"
            }],
            "from": {"email": GARMIN_USERNAME},
            "content": [{
                "type": "text/plain",
                "value": f"send {grib_request}"
            }]
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 202:
            print(f"✅ Demande GRIB envoyée à Saildocs: {grib_request}")
            last_status = "✅ Demande GRIB envoyée à Saildocs"
            return True
        else:
            last_status = f"❌ Erreur SendGrid: Status {response.status_code}"
            print(f"{last_status} - {response.text}")
            return False
        
    except Exception as e:
        last_status = f"❌ Erreur lors de l'envoi à Saildocs: {str(e)}"
        print(last_status)
        import traceback
        traceback.print_exc()
        return False

def wait_for_saildocs_response(mail, timeout=300):
    """Attend la réponse Saildocs avec GRIB"""
    print("⏳ Attente de la réponse Saildocs...")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            mail.select("inbox")
            status, messages = mail.search(None, f'(FROM "{SAILDOCS_RESPONSE_EMAIL}" UNSEEN)')
            
            if status == "OK" and messages[0]:
                email_ids = messages[0].split()
                
                for email_id in email_ids:
                    status, msg_data = mail.fetch(email_id, "(RFC822)")
                    
                    if status != "OK":
                        continue
                    
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            for part in msg.walk():
                                if part.get_content_disposition() == "attachment":
                                    filename = part.get_filename()
                                    if filename and ('.grb' in filename.lower() or '.grib' in filename.lower()):
                                        grib_data = part.get_payload(decode=True)
                                        print(f"✅ GRIB reçu: {filename} ({len(grib_data)} octets)")
                                        return grib_data
            
            time.sleep(10)
            
        except Exception as e:
            print(f"⚠ Erreur attente: {e}")
            time.sleep(10)
    
    print("❌ Timeout Saildocs (aucun GRIB reçu)")
    return None

def encode_grib_to_messages(grib_data):
    """Encode GRIB en messages de 120 caractères"""
    
    print(f"\n{'='*60}")
    print("ENCODAGE GRIB")
    print(f"{'='*60}")
    
    # Compression
    compressed = zlib.compress(grib_data, level=9)
    ratio = (1 - len(compressed) / len(grib_data)) * 100
    print(f"1. Compression: {len(grib_data)} → {len(compressed)} octets ({ratio:.1f}%)")
    
    # Base64
    encoded = base64.b64encode(compressed).decode('utf-8')
    print(f"2. Base64: {len(encoded)} caractères")
    
    # Découpage
    chunks = [encoded[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(encoded), MAX_MESSAGE_LENGTH)]
    total = len(chunks)
    
    print(f"3. Découpage: {total} messages")
    
    # Formatage
    messages = []
    for i, chunk in enumerate(chunks):
        msg = f"msg {i+1}/{total}:\n{chunk}\nend"
        messages.append(msg)
        print(f"   Message {i+1}/{total}: {len(chunk)} chars")
    
    print(f"{'='*60}\n")
    
    return messages

def extract_guid_from_url(url):
    """Extrait le GUID (extId) de l'URL inReach"""
    parsed = urlparse(url)
    guid_list = parse_qs(parsed.query).get('extId')
    if not guid_list:
        raise ValueError("GUID (extId) non trouvé dans l'URL")
    return guid_list[0]

def send_message_to_inreach(url, message):
    """
    Envoie UN SEUL message vers inReach via POST
    """
    try:
        guid = extract_guid_from_url(url)
        
        data = {
            'ReplyMessage': message,
            'Guid': guid,
            'ReplyAddress': GARMIN_USERNAME,
        }
        
        response = requests.post(
            url,
            cookies=INREACH_COOKIES,
            headers=INREACH_HEADERS,
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"✅ Message envoyé (Status: {response.status_code})")
            return True
        else:
            print(f"⚠ Status: {response.status_code}")
            print(f"  Réponse: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur envoi message: {e}")
        return False

def send_messages_to_inreach(url, messages):
    """Envoie plusieurs messages vers inReach via POST"""
    
    print(f"📤 Envoi de {len(messages)} messages vers inReach")
    
    try:
        guid = extract_guid_from_url(url)
        print(f"✅ GUID extrait: {guid}")
    except Exception as e:
        print(f"❌ Erreur GUID: {e}")
        return False
    
    success_count = 0
    
    for i, message in enumerate(messages, 1):
        try:
            data = {
                'ReplyMessage': message,
                'Guid': guid,
                'ReplyAddress': GARMIN_USERNAME,
            }
            
            response = requests.post(
                url,
                cookies=INREACH_COOKIES,
                headers=INREACH_HEADERS,
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"✅ Message {i}/{len(messages)} envoyé (Status: {response.status_code})")
                success_count += 1
            else:
                print(f"⚠ Message {i}/{len(messages)} - Status: {response.status_code}")
                print(f"  Réponse: {response.text[:200]}")
            
            if i < len(messages):
                time.sleep(DELAY_BETWEEN_MESSAGES)
                
        except Exception as e:
            print(f"❌ Erreur message {i}/{len(messages)}: {e}")
    
    if success_count == len(messages):
        print(f"\n✅ TOUS LES {len(messages)} MESSAGES ENVOYÉS!")
        return True
    else:
        print(f"\n⚠ {success_count}/{len(messages)} messages envoyés")
        return False

def process_workflow():
    """
    Processus complet de traitement des requêtes GRIB et Claude
    MODIFIÉ: Gère maintenant les deux types de requêtes
    """
    global last_status, last_check_time
    
    print(f"\n{'='*60}")
    print(f"🔄 DÉMARRAGE TRAITEMENT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    if not check_credentials():
        return
    
    mail = connect_gmail()
    if not mail:
        return
    
    try:
        requests_list = check_for_requests(mail)
        
        if not requests_list:
            print("✅ Aucune nouvelle requête")
            last_status = "✅ Aucune nouvelle demande"
            return
        
        for req in requests_list:
            print(f"\n{'='*60}")
            
            # TRAITEMENT CLAUDE
            if req['type'] == 'claude':
                print(f"TRAITEMENT Claude: {req['question'][:50]}...")
                print(f"{'='*60}\n")
                
                # Obtenir la réponse de Claude (peut retourner plusieurs messages)
                messages = query_claude(req['question'], req['max_words'])
                
                # Envoyer les messages vers inReach avec délai entre chaque
                success = True
                for i, message in enumerate(messages, 1):
                    print(f"📤 Envoi message {i}/{len(messages)}...")
                    if not send_message_to_inreach(req['reply_url'], message):
                        print(f"❌ Échec envoi message {i}/{len(messages)}")
                        success = False
                        break
                    
                    # Délai entre les messages (sauf pour le dernier)
                    if i < len(messages):
                        print(f"⏳ Attente {DELAY_BETWEEN_MESSAGES}s avant le prochain message...")
                        time.sleep(DELAY_BETWEEN_MESSAGES)
                
                if success:
                    last_status = f"✅ Réponse Claude envoyée ({len(messages)} messages)"
                    print(f"\n✅ REQUÊTE CLAUDE TRAITÉE - {len(messages)} message(s) envoyé(s)!\n")
                else:
                    print(f"\n❌ Échec partiel envoi réponse Claude\n")
            
            # TRAITEMENT GRIB
            elif req['type'] == 'grib':
                print(f"TRAITEMENT GRIB: {req['request']}")
                print(f"{'='*60}\n")
                
                if not send_to_saildocs(req['request']):
                    continue
                
                grib_data = wait_for_saildocs_response(mail, timeout=300)
                
                if not grib_data:
                    print("❌ Pas de GRIB reçu")
                    continue
                
                messages = encode_grib_to_messages(grib_data)
                
                if send_messages_to_inreach(req['reply_url'], messages):
                    last_status = f"✅ GRIB traité et envoyé avec succès ({len(messages)} messages)"
                
                print(f"\n✅ REQUÊTE GRIB TRAITÉE!\n")
        
    except Exception as e:
        print(f"❌ Erreur dans le workflow: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            mail.logout()
            print("📧 Déconnexion de la boîte email")
        except:
            pass
        print(f"\n{'='*60}")
        print("FIN DU TRAITEMENT")
        print(f"{'='*60}\n")

# ==========================================
# PLANIFICATION DES TÂCHES
# ==========================================

def run_scheduled_tasks():
    """Exécute les tâches planifiées"""
    print("\n🚨 ENTRÉE DANS run_scheduled_tasks() - THREAD ACTIF")
    thread_started.set()
    
    print("\n" + "="*60)
    print("⏰ PLANIFICATION AUTOMATIQUE")
    print("="*60)
    print("📅 Fréquence : Vérification toutes les heures")
    print("🔧 Thread de planification démarré")
    print("🤖 Module Claude AI activé")
    print("="*60 + "\n")
    
    try:
        # Planification toutes les heures
        schedule.every(1).hours.do(process_workflow)
        
        # Heartbeat toutes les 10 minutes
        def heartbeat():
            print(f"💓 Heartbeat - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Service actif")
        
        schedule.every(10).minutes.do(heartbeat)
        
        print("✅ Planification configurée : prochaine vérification dans 1 heure")
        print("✅ Heartbeat configuré : toutes les 10 minutes")
        
        # Exécution immédiate au démarrage
        print("🚀 Lancement de la première vérification immédiate...\n")
        process_workflow()
        print("\n✅ Première vérification terminée")
        print(f"⏰ Prochaine vérification automatique : dans 1 heure\n")
        
    except Exception as e:
        print(f"❌ ERREUR dans la première vérification: {e}")
        import traceback
        traceback.print_exc()
    
    # Boucle de vérification du planificateur
    print("🔄 Service actif - Vérifications automatiques toutes les heures")
    print("💓 Heartbeat actif - Signal toutes les 10 minutes")
    print("🤖 Claude AI prêt pour les requêtes")
    print("=" * 60 + "\n")
    
    loop_count = 0
    while True:
        try:
            loop_count += 1
            if loop_count % 10 == 0:
                print(f"🔄 Boucle active - Itération {loop_count} - {datetime.now().strftime('%H:%M:%S')}")
            
            schedule.run_pending()
            time.sleep(60)
        except Exception as e:
            print(f"❌ ERREUR dans la boucle de planification: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(60)

# ==========================================
# DÉMARRAGE DU SERVICE
# ==========================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 DÉMARRAGE DU SERVICE GRIB INREACH + CLAUDE AI")
    print("="*60)
    print(f"📅 Date/Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📧 Email configuré: {GARMIN_USERNAME}")
    print(f"🤖 Claude AI: {'✅ Activé' if ANTHROPIC_API_KEY else '❌ Non configuré'}")
    print(f"🌐 Port Flask: {PORT}")
    print("="*60 + "\n")
    
    # Vérifier les credentials au démarrage
    if not check_credentials():
        print("❌ ARRÊT DU SERVICE - Identifiants manquants")
        sys.exit(1)
    
    if not ANTHROPIC_API_KEY:
        print("⚠️  AVERTISSEMENT: ANTHROPIC_API_KEY non configurée - Module Claude désactivé")
    
    # Démarrer le thread de planification
    print("🔧 Démarrage du thread de planification...")
    scheduler_thread = Thread(target=run_scheduled_tasks, daemon=True)
    scheduler_thread.start()
    print("✅ Thread de planification démarré")
    
    # Attendre que le thread démarre
    print("⏳ Attente de confirmation du thread...")
    if thread_started.wait(timeout=10):
        print("✅ Thread de planification confirmé actif\n")
    else:
        print("⚠️  Thread de planification ne répond pas (continuons quand même)\n")
    
    # Démarrer Flask
    print(f"🌐 Démarrage du serveur Flask sur le port {PORT}...")
    print("="*60 + "\n")
    
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False)
    except KeyboardInterrupt:
        print("\n\n🛑 Arrêt du service demandé par l'utilisateur")
        print("="*60)
    except Exception as e:
        print(f"\n\n❌ ERREUR CRITIQUE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
