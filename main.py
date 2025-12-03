#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service de traitement automatique des fichiers GRIB pour Garmin InReach
Surveille les emails, télécharge les fichiers GRIB, les traite avec Saildocs, 
et renvoie les données météo vers le Garmin InReach.
VERSION CORRIGÉE - Configuration SMTP identique à Termux
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
from threading import Thread
from urllib.parse import urlparse, parse_qs
from flask import Flask, jsonify

# ==========================================
# CONFIGURATION
# ==========================================

# Variables d'environnement (définies dans Render)
GARMIN_USERNAME = os.environ.get('GARMIN_USERNAME', 'garminced@gmail.com')
GARMIN_PASSWORD = os.environ.get('GARMIN_PASSWORD')

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

@app.route('/')
def index():
    """Page d'accueil"""
    return jsonify({
        "service": "GRIB InReach Service",
        "status": "running",
        "last_check": str(last_check_time),
        "message": last_status
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
        "service": "GRIB InReach Service",
        "status": "running",
        "current_status": last_status,
        "last_check_time": str(last_check_time) if last_check_time else "Aucune vérification encore",
        "garmin_username": GARMIN_USERNAME if GARMIN_USERNAME else "Non configuré",
        "sendgrid_configured": "✅ Oui" if os.environ.get('SENDGRID_API_KEY') else "❌ Non",
        "verification_frequency": "Toutes les heures",
        "next_check": "Dans moins d'1 heure" if last_check_time else "Imminent",
        "service_active_since": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "instructions": "Le service vérifie automatiquement les emails toutes les heures. Consultez les logs Render pour plus de détails."
    })

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

def check_for_grib_requests(mail):
    """Vérifie les nouveaux emails avec requêtes GRIB depuis inReach"""
    global last_status, last_check_time
    
    try:
        mail.select("inbox")
        # Cherche TOUS les emails non lus (on filtrera après)
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
                    print(f"  Body complet:\n{body}\n")
                    
                    # Chercher requête GRIB - pattern amélioré pour capturer toute la ligne
                    grib_pattern = re.compile(r'(ecmwf|gfs|icon):[^\s\n]+', re.IGNORECASE)
                    match = grib_pattern.search(body)
                    
                    if not match:
                        # Si pas trouvé, essayer de chercher sur plusieurs lignes
                        body_single_line = body.replace('\n', ' ').replace('\r', ' ')
                        match = grib_pattern.search(body_single_line)
                    
                    if not match:
                        print(f"⚠ Email inReach sans requête GRIB valide")
                        continue
                    
                    grib_request = match.group(0)
                    
                    # Extraire URL de réponse
                    reply_url_pattern = re.compile(r'https://[^\s]+garmin\.com/textmessage/txtmsg\?[^\s]+')
                    reply_match = reply_url_pattern.search(body)
                    
                    if not reply_match:
                        print(f"⚠ Requête sans URL de réponse: {grib_request}")
                        continue
                    
                    reply_url = reply_match.group(0)
                    
                    print(f"✅ Requête trouvée: {grib_request}")
                    print(f"  URL: {reply_url[:60]}...")
                    
                    requests_list.append({
                        'request': grib_request,
                        'reply_url': reply_url
                    })
        
        last_check_time = datetime.now()
        last_status = f"✅ Vérification terminée - {len(requests_list)} demande(s) trouvée(s)"
        
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
        
        # Récupérer la clé API SendGrid depuis les variables d'environnement
        sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
        if not sendgrid_api_key:
            last_status = "❌ ERREUR: Variable SENDGRID_API_KEY non définie"
            print(last_status)
            return False
        
        # Construire la requête pour l'API SendGrid
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
        msg = f"msg {i+1}/{total}:\\n{chunk}\\nend"
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

def send_messages_to_inreach(url, messages):
    """Envoie les messages vers inReach via POST"""
    
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

def process_grib_workflow():
    """Processus complet de traitement des fichiers GRIB"""
    global last_status, last_check_time
    
    print(f"\n{'='*60}")
    print(f"🔄 DÉMARRAGE TRAITEMENT GRIB - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    if not check_credentials():
        return
    
    mail = connect_gmail()
    if not mail:
        return
    
    try:
        requests_list = check_for_grib_requests(mail)
        
        if not requests_list:
            print("✅ Aucune nouvelle requête GRIB")
            last_status = "✅ Aucune nouvelle demande GRIB"
            return
        
        for req in requests_list:
            print(f"\n{'='*60}")
            print(f"TRAITEMENT: {req['request']}")
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
            
            print(f"\n✅ REQUÊTE TRAITÉE!\n")
        
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
    print("\n" + "="*60)
    print("⏰ PLANIFICATION AUTOMATIQUE")
    print("="*60)
    print("📅 Fréquence : Vérification toutes les heures")
    print("🔧 Thread de planification démarré")
    print("="*60 + "\n")
    
    try:
        # Planification toutes les heures
        schedule.every(1).hours.do(process_grib_workflow)
        print("✅ Planification configurée : prochaine vérification dans 1 heure")
        
        # Exécution immédiate au démarrage
        print("🚀 Lancement de la première vérification immédiate...\n")
        process_grib_workflow()
        print("\n✅ Première vérification terminée")
        print(f"⏰ Prochaine vérification automatique : dans 1 heure\n")
        
    except Exception as e:
        print(f"❌ ERREUR dans la première vérification: {e}")
        import traceback
        traceback.print_exc()
    
    # Boucle de vérification du planificateur
    print("🔄 Service actif - Vérifications automatiques toutes les heures")
    print("=" * 60 + "\n")
    
    while True:
        try:
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

def main():
    """Point d'entrée principal"""
    global last_status
    
    print("\n" + "="*60)
    print("🚀 DÉMARRAGE DU SERVICE GRIB INREACH")
    print("="*60)
    print(f"📅 Date: {datetime.now()}")
    print(f"🔧 Port: {PORT}")
    print(f"👤 Utilisateur Garmin: {GARMIN_USERNAME}")
    print(f"📧 SMTP: {GMAIL_HOST}:{GMAIL_PORT} (SSL)")
    print("="*60 + "\n")
    
    last_status = "🚀 Service démarré"
    
    # CORRECTION: Démarrage des tâches planifiées dans un thread (non bloquant)
    print("🔧 Démarrage du thread de planification...")
    schedule_thread = Thread(target=run_scheduled_tasks, daemon=True)
    schedule_thread.start()
    
    # Attente que le thread démarre
    time.sleep(2)
    print("✅ Thread de planification démarré avec succès\n")
    
    # Démarrage du serveur Flask (bloquant - doit être en dernier)
    print(f"🌐 Démarrage du serveur HTTP sur le port {PORT}...")
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du service demandé")
        last_status = "🛑 Service arrêté"
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
