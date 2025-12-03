#!/usr/bin/env python3
"""
Service GRIB InReach - Railway.app
Tourne en continu pour traiter les requêtes GRIB automatiquement
"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
import base64
import zlib
import time
import re
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import requests

# ============================================================
# CONFIGURATION - Variables d'environnement
# ============================================================

GMAIL_USER = os.environ.get('GMAIL_USER', 'garminced@gmail.com')
GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD')  # À définir dans Railway

SAILDOCS_EMAIL = "query@saildocs.com"
SAILDOCS_RESPONSE_EMAIL = "query-reply@saildocs.com"
SERVICE_EMAIL = "no.reply.inreach@garmin.com"

MAX_MESSAGE_LENGTH = 120
DELAY_BETWEEN_MESSAGES = 5
CHECK_INTERVAL = 60  # Vérifier emails toutes les 60 secondes

# Headers pour EUR (ajustez selon votre région)
INREACH_HEADERS = {
    'authority': 'eur.explore.garmin.com',
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'origin': 'https://eur.explore.garmin.com',
    'sec-ch-ua': '"Chromium";v="106", "Not;A=Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'x-requested-with': 'XMLHttpRequest',
}

INREACH_COOKIES = {'BrowsingMode': 'Desktop'}

# ============================================================
# FONCTIONS
# ============================================================

def log(message):
    """Log avec timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def connect_gmail():
    """Connexion à Gmail via IMAP"""
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASSWORD)
        log("✓ Connecté à Gmail")
        return mail
    except Exception as e:
        log(f"❌ Erreur connexion Gmail: {e}")
        return None

def check_for_grib_requests(mail):
    """Vérifie les nouveaux emails avec requêtes GRIB depuis inReach"""
    try:
        mail.select("inbox")
        status, messages = mail.search(None, f'(FROM "{SERVICE_EMAIL}" UNSEEN)')
        
        if status != "OK" or not messages[0]:
            return []
        
        email_ids = messages[0].split()
        requests_list = []
        
        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            
            if status != "OK":
                continue
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Récupérer le corps
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()
                    
                    # Chercher requête GRIB
                    grib_pattern = re.compile(r'(ecmwf|gfs|icon):[0-9nNsSwWeE,|]+', re.IGNORECASE)
                    match = grib_pattern.search(body)
                    
                    if not match:
                        continue
                    
                    grib_request = match.group(0)
                    
                    # Extraire URL de réponse
                    reply_url_pattern = re.compile(r'https://[^\s]+garmin\.com/textmessage/txtmsg\?[^\s]+')
                    reply_match = reply_url_pattern.search(body)
                    
                    if not reply_match:
                        log(f"⚠ Requête sans URL: {grib_request}")
                        continue
                    
                    reply_url = reply_match.group(0)
                    
                    log(f"✓ Requête trouvée: {grib_request}")
                    
                    requests_list.append({
                        'request': grib_request,
                        'reply_url': reply_url
                    })
        
        return requests_list
        
    except Exception as e:
        log(f"❌ Erreur lecture emails: {e}")
        return []

def send_to_saildocs(grib_request):
    """Envoie la requête à Saildocs"""
    try:
        msg = MIMEText(f"send {grib_request}")
        msg['Subject'] = "GRIB Request"
        msg['From'] = GMAIL_USER
        msg['To'] = SAILDOCS_EMAIL
        
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        log(f"✓ Envoyé à Saildocs")
        return True
        
    except Exception as e:
        log(f"❌ Erreur Saildocs: {e}")
        return False

def wait_for_saildocs_response(mail, timeout=300):
    """Attend la réponse Saildocs avec GRIB"""
    log("⏳ Attente Saildocs...")
    
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
                                        log(f"✓ GRIB reçu: {len(grib_data)} octets")
                                        return grib_data
            
            time.sleep(10)
            
        except Exception as e:
            log(f"⚠ Erreur attente: {e}")
            time.sleep(10)
    
    log("❌ Timeout Saildocs")
    return None

def encode_grib_to_messages(grib_data):
    """Encode GRIB en messages de 120 caractères"""
    
    # Compression
    compressed = zlib.compress(grib_data, level=9)
    ratio = (1 - len(compressed) / len(grib_data)) * 100
    log(f"Compression: {len(grib_data)} → {len(compressed)} octets ({ratio:.1f}%)")
    
    # Base64
    encoded = base64.b64encode(compressed).decode('utf-8')
    
    # Découpage
    chunks = [encoded[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(encoded), MAX_MESSAGE_LENGTH)]
    total = len(chunks)
    
    log(f"Découpage: {total} messages")
    
    # Formatage
    messages = []
    for i, chunk in enumerate(chunks):
        msg = f"msg {i+1}/{total}:\\n{chunk}\\nend"
        messages.append(msg)
    
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
    
    try:
        guid = extract_guid_from_url(url)
        log(f"GUID: {guid}")
    except Exception as e:
        log(f"❌ Erreur GUID: {e}")
        return False
    
    success_count = 0
    
    for i, message in enumerate(messages, 1):
        try:
            data = {
                'ReplyMessage': message,
                'Guid': guid,
                'ReplyAddress': GMAIL_USER,
            }
            
            response = requests.post(
                url,
                cookies=INREACH_COOKIES,
                headers=INREACH_HEADERS,
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                log(f"✓ Message {i}/{len(messages)} envoyé")
                success_count += 1
            else:
                log(f"⚠ Message {i}/{len(messages)} - Status: {response.status_code}")
            
            if i < len(messages):
                time.sleep(DELAY_BETWEEN_MESSAGES)
                
        except Exception as e:
            log(f"❌ Erreur message {i}: {e}")
    
    return success_count == len(messages)

def process_grib_requests():
    """Traite les requêtes GRIB"""
    
    mail = connect_gmail()
    if not mail:
        return
    
    requests_list = check_for_grib_requests(mail)
    
    if not requests_list:
        log("Aucune nouvelle requête")
        mail.logout()
        return
    
    for req in requests_list:
        log(f"=== TRAITEMENT: {req['request']} ===")
        
        if not send_to_saildocs(req['request']):
            continue
        
        grib_data = wait_for_saildocs_response(mail, timeout=300)
        
        if not grib_data:
            log("❌ Pas de GRIB reçu")
            continue
        
        messages = encode_grib_to_messages(grib_data)
        
        if send_messages_to_inreach(req['reply_url'], messages):
            log("✓ Requête traitée avec succès!")
        else:
            log("⚠ Envoi incomplet")
    
    mail.logout()

# ============================================================
# MAIN LOOP
# ============================================================

if __name__ == "__main__":
    log("=== SERVICE GRIB INREACH DÉMARRÉ ===")
    log(f"Gmail: {GMAIL_USER}")
    log(f"Check interval: {CHECK_INTERVAL}s")
    
    # Boucle infinie
    while True:
        try:
            process_grib_requests()
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            log("⚠ Arrêt demandé")
            break
        except Exception as e:
            log(f"❌ Erreur: {e}")
            time.sleep(CHECK_INTERVAL)
