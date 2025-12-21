#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service de traitement automatique des fichiers GRIB pour Garmin InReach
VERSION MONOLITHIQUE - Tous les modules integres
"""

VERSION = "2.3.0"
VERSION_DATE = "2025-12-20"

import os
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/opt/render/project/src/.browsers'

import time
import imaplib
import email
import base64
import zlib
import re
import requests
import schedule
from datetime import datetime
from threading import Thread, Event
from urllib.parse import urlparse, parse_qs
from flask import Flask, jsonify

# Playwright
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
    print("✅ Playwright disponible")
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  Playwright non disponible")

# SendGrid pour envoi emails
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    SENDGRID_AVAILABLE = True
    print("✅ SendGrid disponible")
except ImportError:
    SENDGRID_AVAILABLE = False
    print("⚠️  SendGrid non disponible")

# Configuration
GARMIN_USERNAME = os.environ.get('GARMIN_USERNAME', 'garminced@gmail.com')
GARMIN_PASSWORD = os.environ.get('GARMIN_PASSWORD')
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

# Configuration Email
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
SAILDOCS_EMAIL = "query@saildocs.com"

# Configuration InReach
MAX_MESSAGE_LENGTH = 120
DELAY_BETWEEN_MESSAGES = 5
PORT = int(os.environ.get('PORT', 10000))

# Flask app
app = Flask(__name__)
last_check_time = None
last_status = "Démarrage..."
thread_started = Event()

@app.route('/')
def index():
    return jsonify({"service": "GRIB InReach", "status": "running"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/status')
def status():
    return jsonify({
        "service": "GRIB InReach Service",
        "status": last_status,
        "last_check": str(last_check_time)
    })

# ===========================================
# FONCTIONS UTILITAIRES
# ===========================================

def encode_and_split_grib(grib_data):
    """Compresse et découpe fichier GRIB"""
    print(f"\n{'='*60}")
    print("ENCODAGE GRIB")
    print(f"{'='*60}")
    
    # Compression
    compressed = zlib.compress(grib_data, level=9)
    ratio = (1 - len(compressed)/len(grib_data)) * 100
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

# ===========================================
# ENVOI INREACH AVEC PLAYWRIGHT
# ===========================================

def send_to_inreach_playwright(url, messages):
    """Envoi via Playwright pour inreachlink.com"""
    print(f"🎭 PLAYWRIGHT: {len(messages)} messages")
    print(f"   URL: {url}")
    
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright non disponible")
        return False
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox'],
                executable_path='/opt/render/project/src/browsers/chromium-1091/chrome-linux/chrome'
            )
            context = browser.new_context()
            page = context.new_page()
            
            # 1. Charger page
            print("1. 🌐 Chargement inReachLink...")
            page.goto(url, wait_until='networkidle', timeout=30000)
            time.sleep(2)
            
            # 2. Login Garmin si nécessaire
            if 'sso.garmin.com' in page.url or page.locator('input[type="email"]').count() > 0:
                print("2. 🔐 Login Garmin...")
                
                email_input = page.locator('input[type="email"]')
                if email_input.count() > 0:
                    email_input.fill(GARMIN_USERNAME)
                    time.sleep(1)
                    page.keyboard.press('Enter')
                    page.wait_for_load_state('networkidle', timeout=15000)
                    time.sleep(2)
                
                password_input = page.locator('input[type="password"]')
                if password_input.count() > 0:
                    password_input.fill(GARMIN_PASSWORD)
                    time.sleep(1)
                    page.keyboard.press('Enter')
                    page.wait_for_load_state('networkidle', timeout=15000)
                    time.sleep(3)
                
                print("   ✅ Login terminé")
            
            # 3. Attendre formulaire
            print("3. ⏳ Attente formulaire...")
            page.wait_for_selector('textarea', timeout=20000)
            time.sleep(2)
            print("   ✅ Formulaire prêt")
            
            # 4. Envoyer chaque message
            for i, message in enumerate(messages, 1):
                try:
                    print(f"   📤 Message {i}/{len(messages)}")
                    
                    page.wait_for_load_state('networkidle', timeout=10000)
                    time.sleep(2)
                    
                    # CRITIQUE: Re-localiser textarea à chaque fois
                    textarea = page.locator('textarea').first
                    textarea.wait_for(state='visible', timeout=10000)
                    
                    # Vider puis remplir
                    textarea.fill('')
                    time.sleep(0.5)
                    textarea.fill(message)
                    time.sleep(1)
                    
                    # Envoyer
                    send_button = page.locator('button:has-text("Send"), input[type="submit"]').first
                    send_button.click()
                    time.sleep(3)
                    
                    print(f"      ✅ Message {i}/{len(messages)} envoyé")
                    
                    if i < len(messages):
                        time.sleep(DELAY_BETWEEN_MESSAGES)
                
                except Exception as e:
                    print(f"      ❌ Erreur message {i}: {e}")
                    continue
            
            print(f"\n✅ Playwright terminé - {len(messages)} messages traités")
            browser.close()
            return True
            
        except Exception as e:
            print(f"❌ Erreur Playwright: {e}")
            if 'browser' in locals():
                browser.close()
            return False

# ===========================================
# ENVOI INREACH PAR EMAIL
# ===========================================

def send_to_inreach_email(reply_email, messages):
    """Envoi via SendGrid"""
    print(f"📧 EMAIL SendGrid: {len(messages)} messages")
    
    if not SENDGRID_AVAILABLE or not SENDGRID_API_KEY:
        print("❌ SendGrid non configuré")
        return False
    
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        
        combined = "\n\n---\n\n".join(
            [f"Message {i}/{len(messages)}:\n{msg}" for i, msg in enumerate(messages, 1)]
        )
        
        email_content = Mail(
            from_email=GARMIN_USERNAME,
            to_emails=reply_email,
            subject='GRIB Weather Data',
            plain_text_content=combined
        )
        
        response = sg.send(email_content)
        
        if response.status_code in [200, 201, 202]:
            print(f"✅ Email envoyé")
            return True
        else:
            print(f"⚠️  Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur email: {e}")
        return False

# ===========================================
# TRAITEMENT GRIB COMPLET
# ===========================================

def process_grib_request(grib_request, inreach_url, reply_email=None):
    """Traite une requête GRIB complète"""
    global last_status
    
    print(f"\n{'='*70}")
    print(f"🌊 TRAITEMENT GRIB")
    print(f"{'='*70}")
    print(f"Requête: {grib_request}")
    print(f"URL: {inreach_url}")
    print(f"{'='*70}\n")
    
    try:
        # 1. Envoyer à Saildocs
        print("📤 Étape 1/3: Envoi à Saildocs...")
        if not send_to_saildocs(grib_request):
            return False
        
        # 2. Attendre réponse
        print("⏳ Étape 2/3: Attente réponse Saildocs...")
        grib_data = wait_for_saildocs_response()
        if not grib_data:
            return False
        
        # 3. Encoder et envoyer
        print("🔧 Étape 3/3: Encodage et envoi...")
        messages = encode_and_split_grib(grib_data)
        
        # Router vers bon endpoint
        if 'inreachlink.com' in inreach_url:
            success = send_to_inreach_playwright(inreach_url, messages)
        elif reply_email:
            success = send_to_inreach_email(reply_email, messages)
        else:
            print("❌ Aucune méthode d'envoi disponible")
            return False
        
        if success:
            print(f"\n✅✅✅ GRIB ENVOYÉ ({len(messages)} messages) ✅✅✅\n")
            last_status = f"✅ GRIB envoyé: {len(messages)} msg"
            return True
        else:
            last_status = "❌ Échec envoi GRIB"
            return False
            
    except Exception as e:
        print(f"❌ Erreur process_grib: {e}")
        last_status = f"❌ Erreur: {str(e)}"
        return False

def send_to_saildocs(grib_request):
    """Envoie requête à Saildocs par email"""
    if not SENDGRID_AVAILABLE:
        print("❌ SendGrid requis pour Saildocs")
        return False
    
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        
        message = Mail(
            from_email=GARMIN_USERNAME,
            to_emails=SAILDOCS_EMAIL,
            subject='send',
            plain_text_content=f"send {grib_request}"
        )
        
        response = sg.send(message)
        print(f"✅ Demande GRIB envoyée à Saildocs")
        return True
        
    except Exception as e:
        print(f"❌ Erreur envoi Saildocs: {e}")
        return False

def wait_for_saildocs_response(timeout=300):
    """Attend réponse de Saildocs"""
    print(f"⏳ Attente réponse Saildocs (max {timeout}s)...")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            mail.login(GARMIN_USERNAME, GARMIN_PASSWORD)
            mail.select('inbox')
            
            status, messages = mail.search(None, '(UNSEEN FROM "query@saildocs.com")')
            
            if status == 'OK' and messages[0]:
                email_ids = messages[0].split()
                
                for email_id in email_ids:
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    for part in msg.walk():
                        if part.get_content_type() == 'application/octet-stream':
                            grib_data = part.get_payload(decode=True)
                            print(f"✅ GRIB reçu: {len(grib_data)} octets")
                            mail.store(email_id, '+FLAGS', '\\Seen')
                            mail.logout()
                            return grib_data
            
            mail.logout()
            
        except Exception as e:
            print(f"⚠️  Erreur vérification: {e}")
        
        time.sleep(10)
    
    print("❌ Timeout attente Saildocs")
    return None

# ===========================================
# SURVEILLANCE EMAILS
# ===========================================

def check_gmail():
    """Vérifie emails pour requêtes GRIB"""
    global last_check_time, last_status
    
    print(f"\n{'='*70}")
    print(f"🔄 VÉRIFICATION - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")
    
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(GARMIN_USERNAME, GARMIN_PASSWORD)
        mail.select('inbox')
        
        status, messages = mail.search(None, '(UNSEEN FROM "inreach")')
        
        if status != 'OK':
            print("⚠️  Erreur recherche")
            return
        
        email_ids = messages[0].split()
        print(f"📬 {len(email_ids)} email(s) inReach\n")
        
        if len(email_ids) == 0:
            print("✅ Aucun nouveau message")
            last_status = "✅ Aucun nouveau message"
            return
        
        for i, email_id in enumerate(email_ids, 1):
            print(f"📧 EMAIL {i}/{len(email_ids)}")
            
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Extraire corps
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = msg.get_payload(decode=True).decode()
            
            print(f"   Corps: {body[:100]}...")
            
            # Extraire URL
            url_match = re.search(r'(https://[^\s]*inreach[^\s]*)', body)
            if not url_match:
                print("   ⚠️  Pas d'URL inReach\n")
                continue
            
            inreach_url = url_match.group(1)
            print(f"   URL: {inreach_url}")
            
            # Détecter requête GRIB
            grib_match = re.search(r'(gfs|ecmwf)[:\s]*([\d\w\s,\-\|\.NSEW]+)', body, re.IGNORECASE)
            
            if grib_match:
                grib_request = grib_match.group(0).strip()
                print(f"   🌊 GRIB: {grib_request}\n")
                
                process_grib_request(grib_request, inreach_url)
            
            mail.store(email_id, '+FLAGS', '\\Seen')
        
        mail.logout()
        last_check_time = datetime.now()
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        last_status = f"❌ Erreur: {str(e)}"

# ===========================================
# SCHEDULER
# ===========================================

def run_scheduler():
    """Thread pour vérifications périodiques"""
    print("🚨 THREAD SCHEDULER ACTIF\n")
    
    schedule.every(5).minutes.do(check_gmail)
    
    # Première vérification immédiate
    check_gmail()
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# ===========================================
# MAIN
# ===========================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 DÉMARRAGE GRIB INREACH SERVICE")
    print("="*60)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Port: {PORT}")
    print("="*60 + "\n")
    
    if not GARMIN_USERNAME or not GARMIN_PASSWORD:
        print("❌ GARMIN_USERNAME/PASSWORD manquants")
        sys.exit(1)
    
    print(f"✅ Identifiants: {GARMIN_USERNAME}")
    
    # Démarrer scheduler
    print("🔧 Démarrage scheduler...")
    scheduler_thread = Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    thread_started.set()
    
    print("\n🌐 Démarrage Flask...")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=PORT)
