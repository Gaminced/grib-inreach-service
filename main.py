#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service de traitement automatique des fichiers GRIB pour Garmin InReach
avec modules Claude AI et Mistral AI integres
Surveille les emails, telecharge les fichiers GRIB, les traite avec Saildocs, 
et renvoie les donnees meteo vers le Garmin InReach.
SUPPORT: Claude AI via "claude <max_words>: <question>"
SUPPORT: Mistral AI via "mistral <max_words>: <question>"
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

# Variables d'environnement (definies dans Render)
GARMIN_USERNAME = os.environ.get('GARMIN_USERNAME', 'garminced@gmail.com')
GARMIN_PASSWORD = os.environ.get('GARMIN_PASSWORD')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')  # Cle Anthropic Claude
MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY')  # NOUVEAU: Cle Mistral

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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Origin': 'https://explore.garmin.com',
    'Referer': 'https://explore.garmin.com/'
}

INREACH_COOKIES = {}

# ==========================================
# APPLICATION FLASK (pour le Health Check)
# ==========================================

app = Flask(__name__)

# Variable globale pour le statut
last_check_time = None
last_status = "Demarrage..."
thread_started = Event()

@app.route('/')
def index():
    """Page d'accueil"""
    return jsonify({
        "service": "GRIB InReach Service with Multi-AI",
        "status": "running",
        "last_check": str(last_check_time),
        "message": last_status,
        "features": ["GRIB files", "Claude AI queries", "Mistral AI queries"]
    })

@app.route('/health')
def health():
    """Endpoint de sante pour le monitoring"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "last_check": str(last_check_time)
    }), 200

@app.route('/status')
def status():
    """Statut detaille du service"""
    return jsonify({
        "service": "GRIB InReach Service with Multi-AI",
        "status": "running",
        "current_status": last_status,
        "last_check_time": str(last_check_time) if last_check_time else "Aucune verification encore",
        "garmin_username": GARMIN_USERNAME if GARMIN_USERNAME else "Non configure",
        "sendgrid_configured": "? Oui" if os.environ.get('SENDGRID_API_KEY') else "? Non",
        "anthropic_configured": "? Oui" if ANTHROPIC_API_KEY else "? Non",
        "mistral_configured": "? Oui" if MISTRAL_API_KEY else "? Non",
        "verification_frequency": "Toutes les heures",
        "features": {
            "grib": "Format: ecmwf:24n,34n,72w,60w|8,8|12,48|wind,press",
            "claude": "Format: claude <max_words>: <question>",
            "mistral": "Format: mistral <max_words>: <question>"
        },
        "pricing": {
            "claude_sonnet_4.5": "$3/$15 per M tokens (in/out)",
            "mistral_large": "$2/$6 per M tokens (in/out) - 3x cheaper!"
        }
    })

# ==========================================
# MODULE CLAUDE AI
# ==========================================

def query_claude(prompt, max_words=50):
    """
    Envoie une requete a l'API Claude d'Anthropic et retourne la reponse
    
    Args:
        prompt (str): La question a poser a Claude
        max_words (int): Nombre maximum de mots pour la reponse TOTALE
    
    Returns:
        list: Liste de messages (max 4) ou un seul message d'erreur
    """
    global last_status
    
    if not ANTHROPIC_API_KEY:
        error_msg = "? ERREUR: Variable ANTHROPIC_API_KEY non definie"
        print(error_msg)
        last_status = error_msg
        return ["Claude AI non configure. Veuillez definir ANTHROPIC_API_KEY."]
    
    try:
        print(f"? Envoi de la requete Claude: {prompt[:50]}...")
        
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        system_message = f"You are a helpful assistant for sailors at sea. Provide clear, practical, and complete answers in approximately {max_words} words. Be informative and well-structured."
        
        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": max_words * 3,
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
            
            # Recuperer les informations d'usage
            usage = result.get('usage', {})
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            
            # Calcul du cout (Claude Sonnet 4.5)
            input_cost = (input_tokens / 1_000_000) * 3.0
            output_cost = (output_tokens / 1_000_000) * 15.0
            total_cost = input_cost + output_cost
            
            print(f"? Reponse Claude recue: {len(answer)} caracteres")
            print(f"? Tokens: {input_tokens} in + {output_tokens} out")
            print(f"? Cout: ${total_cost:.6f}")
            
            # Decouper la reponse avec VRAIE limite InReach
            # Calcul : [C XX/XX] = 11 chars max + message + [$X.XXXX] = 10 chars = 21 chars overhead
            # Limite InReach = 120 chars, donc message max = 120 - 21 = 99 chars
            # On prend 95 pour etre sur
            messages = split_into_messages(answer, max_chars_per_message=95)
            
            # Ajouter numerotation avec initiale C (Claude) et cout
            total_msgs = len(messages)
            numbered_messages = []
            
            for i, msg in enumerate(messages, 1):
                if i == total_msgs:
                    # Dernier message : ajouter le cout
                    numbered_msg = f"[C {i}/{total_msgs}] {msg} [${total_cost:.4f}]"
                else:
                    numbered_msg = f"[C {i}/{total_msgs}] {msg}"
                
                # Verification de securite finale
                if len(numbered_msg) > 120:
                    excess = len(numbered_msg) - 117  # 117 pour laisser place a "..."
                    msg = msg[:-excess]
                    if i == total_msgs:
                        numbered_msg = f"[C {i}/{total_msgs}] {msg}... [${total_cost:.4f}]"
                    else:
                        numbered_msg = f"[C {i}/{total_msgs}] {msg}..."
                
                numbered_messages.append(numbered_msg)
            
            print(f"? Reponse Claude decoupee en {total_msgs} message(s)", flush=True)
            for i, msg in enumerate(numbered_messages, 1):
                print(f"   [C {i}/{total_msgs}]: {len(msg)} chars - '{msg[:60]}...'", flush=True)
            
            last_status = f"? Claude: {total_msgs} msg, ${total_cost:.4f}"
            return numbered_messages
        else:
            error_msg = f"? Erreur Anthropic API: {response.status_code}"
            print(f"{error_msg} - {response.text}")
            last_status = error_msg
            return [f"Erreur Claude: {response.status_code}"]
            
    except Exception as e:
        error_msg = f"? Erreur Claude: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        last_status = error_msg
        return [f"Erreur: {str(e)}"]

# ==========================================
# MODULE MISTRAL AI
# ==========================================

def query_mistral(prompt, max_words=50):
    """
    Envoie une requete a l'API Mistral AI et retourne la reponse
    
    Args:
        prompt (str): La question a poser a Mistral
        max_words (int): Nombre maximum de mots pour la reponse TOTALE
    
    Returns:
        list: Liste de messages (max 4) ou un seul message d'erreur
    """
    global last_status
    
    if not MISTRAL_API_KEY:
        error_msg = "? ERREUR: Variable MISTRAL_API_KEY non definie"
        print(error_msg)
        last_status = error_msg
        return ["Mistral AI non configure. Veuillez definir MISTRAL_API_KEY."]
    
    try:
        print(f"? Envoi de la requete Mistral: {prompt[:50]}...")
        
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        
        system_message = f"You are a helpful assistant for sailors at sea. Provide clear, practical, and complete answers in approximately {max_words} words. Be informative and well-structured."
        
        data = {
            "model": "mistral-large-latest",  # Mistral Large (meilleur modele)
            "messages": [
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": max_words * 3
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            answer = result['choices'][0]['message']['content'].strip()
            
            # Recuperer les informations d'usage
            usage = result.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            
            # Calcul du cout (Mistral Large)
            input_cost = (input_tokens / 1_000_000) * 2.0
            output_cost = (output_tokens / 1_000_000) * 6.0
            total_cost = input_cost + output_cost
            
            print(f"? Reponse Mistral recue: {len(answer)} caracteres")
            print(f"? Tokens: {input_tokens} in + {output_tokens} out")
            print(f"? Cout: ${total_cost:.6f}")
            
            # Decouper la reponse avec VRAIE limite InReach
            # Calcul : [M XX/XX] = 11 chars max + message + [$X.XXXX] = 10 chars = 21 chars overhead
            # Limite InReach = 120 chars, donc message max = 120 - 21 = 99 chars
            # On prend 95 pour etre sur
            messages = split_into_messages(answer, max_chars_per_message=95)
            
            # Ajouter numerotation avec initiale M (Mistral) et cout
            total_msgs = len(messages)
            numbered_messages = []
            
            for i, msg in enumerate(messages, 1):
                if i == total_msgs:
                    # Dernier message : ajouter le cout
                    numbered_msg = f"[M {i}/{total_msgs}] {msg} [${total_cost:.4f}]"
                else:
                    numbered_msg = f"[M {i}/{total_msgs}] {msg}"
                
                # Verification de securite finale
                if len(numbered_msg) > 120:
                    excess = len(numbered_msg) - 117  # 117 pour laisser place a "..."
                    msg = msg[:-excess]
                    if i == total_msgs:
                        numbered_msg = f"[M {i}/{total_msgs}] {msg}... [${total_cost:.4f}]"
                    else:
                        numbered_msg = f"[M {i}/{total_msgs}] {msg}..."
                    print(f"   ??  Message {i} tronque de {excess} chars pour respecter 120 limite", flush=True)
                
                numbered_messages.append(numbered_msg)
            
            print(f"? Reponse Mistral decoupee en {total_msgs} message(s)", flush=True)
            for i, msg in enumerate(numbered_messages, 1):
                print(f"   [M {i}/{total_msgs}]: {len(msg)} chars - '{msg[:60]}...'", flush=True)
            
            last_status = f"? Mistral: {total_msgs} msg, ${total_cost:.4f}"
            return numbered_messages
        else:
            error_msg = f"? Erreur Mistral API: {response.status_code}"
            print(f"{error_msg} - {response.text}")
            last_status = error_msg
            return [f"Erreur Mistral: {response.status_code}"]
            
    except Exception as e:
        error_msg = f"? Erreur Mistral: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        last_status = error_msg
        return [f"Erreur: {str(e)}"]

# ==========================================
# FONCTIONS UTILITAIRES
# ==========================================

def split_into_messages(text, max_chars_per_message=105):
    """
    Decoupe un texte en plusieurs messages de taille limitee
    Decoupe intelligemment par phrases
    """
    messages = []
    
    # Decouper par phrases
    sentences = re.split(r'([.!?]\s+)', text)
    current_message = ""
    
    for i in range(0, len(sentences), 2):
        sentence = sentences[i]
        if i + 1 < len(sentences):
            sentence += sentences[i + 1]
        
        if len(current_message) + len(sentence) > max_chars_per_message:
            if current_message:
                messages.append(current_message.strip())
                current_message = sentence
            else:
                # Phrase trop longue, couper par mots
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
    
    # CRITIQUE: Toujours ajouter le dernier message
    if current_message and current_message.strip():
        messages.append(current_message.strip())
    
    # Limiter a 10 messages maximum (augmente de 4 a 10)
    if len(messages) > 10:
        print(f"??  Reponse trop longue ({len(messages)} messages), truncation a 10", flush=True)
        # Recalculer avec taille optimale
        chars_per_msg = len(text) // 10 + 10
        messages = []
        for i in range(10):
            start = i * chars_per_msg
            end = min((i + 1) * chars_per_msg, len(text))
            if start < len(text):
                msg = text[start:end].strip()
                if i == 9 and end < len(text):
                    msg += "..."
                messages.append(msg)
    
    # Verification finale
    if not messages:
        print("??  ATTENTION: split_into_messages a genere 0 messages!", flush=True)
        messages = [text[:max_chars_per_message]]
    
    print(f"   ? Decoupage: {len(text)} chars ? {len(messages)} message(s)", flush=True)
    for i, msg in enumerate(messages, 1):
        print(f"      Msg {i}: {len(msg)} chars - Debut: '{msg[:40]}...'", flush=True)
    
    return messages

def parse_ai_request(body):
    """
    Parse une requete AI du format: <provider> <max_words>: <question>
    Supporte: claude, mistral, gpt (alias pour claude)
    
    Returns:
        tuple: (provider, max_words, question) ou (None, None, None)
    """
    # Pattern: claude/mistral/gpt 150: How do tides work?
    ai_pattern = re.compile(r'(claude|mistral|gpt)\s+(\d+)\s*:\s*(.+)', re.IGNORECASE | re.DOTALL)
    match = ai_pattern.search(body)
    
    if match:
        provider = match.group(1).lower()
        # Alias: gpt ? claude
        if provider == 'gpt':
            provider = 'claude'
        max_words = int(match.group(2))
        question = match.group(3).strip()
        question = ' '.join(question.split())
        
        return provider, max_words, question
    
    return None, None, None

# ==========================================
# FONCTIONS DE TRAITEMENT GRIB
# ==========================================

def check_credentials():
    """Verifie que les identifiants Garmin sont configures"""
    global last_status
    if not GARMIN_USERNAME or not GARMIN_PASSWORD:
        last_status = "? ERREUR: Variables GARMIN_USERNAME et GARMIN_PASSWORD non definies"
        print(last_status)
        return False
    print(f"? Identifiants Garmin configures pour: {GARMIN_USERNAME}")
    return True

def connect_gmail():
    """Connexion a Gmail via IMAP"""
    global last_status
    try:
        print(f"? Connexion IMAP a Gmail: {GARMIN_USERNAME}")
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(GARMIN_USERNAME, GARMIN_PASSWORD)
        print("? Connexion IMAP reussie")
        return mail
    except Exception as e:
        last_status = f"? Erreur connexion IMAP: {str(e)}"
        print(last_status)
        return None

def check_for_requests(mail):
    """
    Verifie les nouveaux emails avec requetes GRIB, Claude ou Mistral
    """
    global last_status, last_check_time
    
    try:
        mail.select("inbox")
        print("? Recherche des emails non lus...", flush=True)
        status, messages = mail.search(None, 'UNSEEN')
        
        if status != "OK":
            last_status = "? Erreur lors de la recherche d'emails"
            print(last_status, flush=True)
            return []
        
        email_ids = messages[0].split()
        print(f"? {len(email_ids)} email(s) non lu(s) trouve(s)", flush=True)
        
        requests_list = []
        
        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            
            if status != "OK":
                continue
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Verifier que l'email vient bien d'inReach
                    from_addr = msg.get('From', '').lower()
                    if 'inreach' not in from_addr and 'garmin' not in from_addr:
                        print(f"? Email ignore (pas inReach): {from_addr}")
                        continue
                    
                    # Recuperer le corps (chercher dans TOUTES les parties)
                    body = ""
                    body_parts = []
                    
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            # Accepter text/plain ET text/html
                            if content_type in ["text/plain", "text/html"]:
                                try:
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        decoded = payload.decode('utf-8', errors='ignore')
                                        body_parts.append(decoded)
                                except Exception as e:
                                    print(f"      ?? Erreur decodage partie: {e}", flush=True)
                        # Joindre toutes les parties
                        body = "\n\n".join(body_parts)
                    else:
                        try:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                body = payload.decode('utf-8', errors='ignore')
                            else:
                                body = str(msg.get_payload())
                        except:
                            body = str(msg.get_payload())
                    
                    print(f"\n? EMAIL TROUVE:", flush=True)
                    print(f"  From: {msg.get('From', 'Unknown')}", flush=True)
                    print(f"  Subject: {msg.get('Subject', 'No subject')}", flush=True)
                    print(f"  Parties trouvees: {len(body_parts)}", flush=True)
                    print(f"  Body total length: {len(body)} chars", flush=True)
                    print(f"  Body preview (500 chars): {body[:500]}", flush=True)
                    
                    # Extraire URL de reponse (chercher dans TOUT le body)
                    # Format 1: https://inreachlink.com/GUID (GUID peut contenir: A-Z, a-z, 0-9, -, _)
                    # Format 2: https://...garmin.com/textmessage/txtmsg?...
                    
                    # IMPORTANT: Extraire aussi l'adresse email de reponse
                    reply_to = msg.get('Reply-To', '')
                    if not reply_to:
                        reply_to = msg.get('From', '')
                    
                    print(f"? Reply-To address: {reply_to}", flush=True)
                    
                    # Chercher d'abord specifiquement inreachlink.com
                    inreach_pattern = re.compile(r'https://inreachlink\.com/[A-Za-z0-9_-]+', re.IGNORECASE)
                    inreach_match = inreach_pattern.search(body)
                    
                    if inreach_match:
                        reply_url = inreach_match.group(0).strip()
                        print(f"? URL inReachLink trouvee: {reply_url}", flush=True)
                    else:
                        # Chercher format garmin.com
                        garmin_pattern = re.compile(r'https://[^\s]+garmin\.com/[^\s]+', re.IGNORECASE)
                        garmin_match = garmin_pattern.search(body)
                        
                        if garmin_match:
                            reply_url = garmin_match.group(0).strip().rstrip('.,;)\'"<>')
                            print(f"? URL Garmin trouvee: {reply_url}", flush=True)
                        else:
                            print("?? Email sans URL de reponse valide", flush=True)
                            print(f"   Body COMPLET ({len(body)} chars):", flush=True)
                            # Afficher chaque partie separement
                            if body_parts:
                                for i, part_text in enumerate(body_parts, 1):
                                    print(f"   --- Partie {i}/{len(body_parts)} ({len(part_text)} chars) ---", flush=True)
                                    print(repr(part_text[:600]), flush=True)
                            else:
                                print(repr(body[:1000]), flush=True)
                            continue
                    
                    # Verifier si c'est une requete AI
                    provider, max_words, question = parse_ai_request(body)
                    
                    if question:
                        print(f"? Requete {provider.upper()} trouvee: {question[:50]}...")
                        print(f"  Max words: {max_words}")
                        
                        requests_list.append({
                            'type': 'ai',
                            'provider': provider,
                            'max_words': max_words,
                            'question': question,
                            'reply_url': reply_url,
                            'reply_email': reply_to
                        })
                        continue
                    
                    # Chercher requete GRIB
                    grib_pattern = re.compile(r'(ecmwf|gfs|icon):[^\s\n]+', re.IGNORECASE)
                    match = grib_pattern.search(body)
                    
                    if not match:
                        body_single_line = body.replace('\n', ' ').replace('\r', ' ')
                        match = grib_pattern.search(body_single_line)
                    
                    if match:
                        grib_request = match.group(0)
                        print(f"? Requete GRIB trouvee: {grib_request}")
                        
                        requests_list.append({
                            'type': 'grib',
                            'request': grib_request,
                            'reply_url': reply_url,
                            'reply_email': reply_to
                        })
                    else:
                        print(f"? Email inReach sans requete valide")
        
        last_check_time = datetime.now()
        grib_count = sum(1 for r in requests_list if r['type'] == 'grib')
        ai_count = sum(1 for r in requests_list if r['type'] == 'ai')
        last_status = f"? Verif: {grib_count} GRIB, {ai_count} AI"
        
        return requests_list
        
    except Exception as e:
        last_status = f"? Erreur verification emails: {str(e)}"
        print(last_status)
        import traceback
        traceback.print_exc()
        return []

def send_to_saildocs(grib_request):
    """Envoie la requete a Saildocs via SendGrid API"""
    global last_status
    
    try:
        print(f"? Envoi demande GRIB a Saildocs...")
        
        sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
        if not sendgrid_api_key:
            last_status = "? SENDGRID_API_KEY non definie"
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
            print(f"? Demande GRIB envoyee")
            return True
        else:
            print(f"? Erreur SendGrid: {response.status_code}")
            return False
        
    except Exception as e:
        print(f"? Erreur envoi Saildocs: {e}")
        return False

def wait_for_saildocs_response(mail, timeout=300):
    """Attend la reponse Saildocs avec GRIB"""
    print(f"? Attente reponse Saildocs (max {timeout}s)...", flush=True)
    print(f"   Recherche emails de: {SAILDOCS_RESPONSE_EMAIL}", flush=True)
    
    start_time = time.time()
    check_count = 0
    
    while time.time() - start_time < timeout:
        try:
            check_count += 1
            elapsed = int(time.time() - start_time)
            
            if check_count % 6 == 1:  # Log toutes les minutes
                print(f"   ??  {elapsed}s ecoulees... (verification #{check_count})", flush=True)
            
            mail.select("inbox")
            status, messages = mail.search(None, f'(FROM "{SAILDOCS_RESPONSE_EMAIL}" UNSEEN)')
            
            if status == "OK" and messages[0]:
                email_ids = messages[0].split()
                print(f"   ? {len(email_ids)} email(s) de Saildocs trouve(s)", flush=True)
                
                for email_id in email_ids:
                    status, msg_data = mail.fetch(email_id, "(RFC822)")
                    
                    if status != "OK":
                        continue
                    
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            print(f"   ? Analyse des pieces jointes...", flush=True)
                            has_attachment = False
                            
                            for part in msg.walk():
                                if part.get_content_disposition() == "attachment":
                                    has_attachment = True
                                    filename = part.get_filename()
                                    print(f"      Fichier trouve: {filename}", flush=True)
                                    
                                    if filename and ('.grb' in filename.lower() or '.grib' in filename.lower()):
                                        grib_data = part.get_payload(decode=True)
                                        print(f"   ? GRIB recu: {len(grib_data)} octets", flush=True)
                                        return grib_data
                                    else:
                                        print(f"      ??  Pas un fichier GRIB", flush=True)
                            
                            if not has_attachment:
                                print(f"      ??  Email sans piece jointe", flush=True)
            
            time.sleep(10)
            
        except Exception as e:
            print(f"   ??  Erreur attente: {e}", flush=True)
            import traceback
            traceback.print_exc()
            time.sleep(10)
    
    print(f"? Timeout Saildocs apres {timeout}s", flush=True)
    return None

def encode_grib_to_messages(grib_data):
    """Encode GRIB en messages de 120 caracteres"""
    
    print(f"\n{'='*60}")
    print("ENCODAGE GRIB")
    print(f"{'='*60}")
    
    compressed = zlib.compress(grib_data, level=9)
    ratio = (1 - len(compressed) / len(grib_data)) * 100
    print(f"1. Compression: {len(grib_data)} ? {len(compressed)} octets ({ratio:.1f}%)")
    
    encoded = base64.b64encode(compressed).decode('utf-8')
    print(f"2. Base64: {len(encoded)} caracteres")
    
    chunks = [encoded[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(encoded), MAX_MESSAGE_LENGTH)]
    total = len(chunks)
    
    print(f"3. Decoupage: {total} messages")
    
    messages = []
    for i, chunk in enumerate(chunks):
        msg = f"msg {i+1}/{total}:\n{chunk}\nend"
        messages.append(msg)
    
    print(f"{'='*60}\n")
    
    return messages

def extract_guid_from_url(url):
    """
    Extrait le GUID de l'URL inReach
    Format 1 (nouveau): https://inreachlink.com/GUID
    Format 2 (ancien): https://...garmin.com/textmessage/txtmsg?extId=GUID&...
    """
    parsed = urlparse(url)
    
    # Format 1: GUID dans le chemin (inreachlink.com)
    if 'inreachlink.com' in url:
        # Le GUID est apres le dernier /
        guid = parsed.path.split('/')[-1]
        if guid:
            print(f"      ? GUID extrait du chemin: {guid}", flush=True)
            return guid
    
    # Format 2: GUID dans le parametre extId (garmin.com)
    guid_list = parse_qs(parsed.query).get('extId')
    if guid_list:
        print(f"      ? GUID extrait de extId: {guid_list[0]}", flush=True)
        return guid_list[0]
    
    # Si aucun format ne fonctionne
    print(f"      ? URL: {url}", flush=True)
    raise ValueError(f"GUID non trouve dans l'URL. Format non reconnu.")

def send_messages_to_inreach_via_email(reply_email, messages):
    """
    Envoie des messages vers inReach en repondant par EMAIL
    C'est la methode officielle supportee par Garmin!
    """
    
    print(f"? Envoi de {len(messages)} messages par EMAIL", flush=True)
    print(f"   ? Destinataire: {reply_email}", flush=True)
    
    if not reply_email or '@' not in reply_email:
        print(f"? Adresse email invalide: {reply_email}", flush=True)
        return False
    
    sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
    if not sendgrid_api_key:
        print("? SENDGRID_API_KEY non definie", flush=True)
        return False
    
    success_count = 0
    
    for i, message in enumerate(messages, 1):
        try:
            print(f"   ? Envoi message {i}/{len(messages)}...", flush=True)
            
            # API SendGrid pour envoyer un email
            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                "Authorization": f"Bearer {sendgrid_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "personalizations": [{
                    "to": [{"email": reply_email}]
                }],
                "from": {"email": GARMIN_USERNAME},
                "subject": "inReach Reply",
                "content": [{
                    "type": "text/plain",
                    "value": message
                }]
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 202:  # SendGrid retourne 202 Accepted
                print(f"   ? Message {i}/{len(messages)} envoye - Status: 202", flush=True)
                success_count += 1
            else:
                print(f"   ? Message {i}/{len(messages)} - Status: {response.status_code}", flush=True)
                print(f"   Response: {response.text[:200]}", flush=True)
            
            # Delai entre les messages
            if i < len(messages):
                time.sleep(DELAY_BETWEEN_MESSAGES)
                
        except Exception as e:
            print(f"   ? Erreur message {i}: {e}", flush=True)
    
    if success_count == len(messages):
        print(f"? Tous les messages envoyes par email avec succes!", flush=True)
    else:
        print(f"? {success_count}/{len(messages)} messages envoyes", flush=True)
    
    return success_count == len(messages)

def send_messages_to_inreach(url, messages):
    """
    OBSOL?TE - Garde pour compatibilite mais ne fonctionne pas
    Utiliser send_messages_to_inreach_via_email() a la place
    """
    print(f"?? send_messages_to_inreach est obsolete!", flush=True)
    print(f"   Utilisez send_messages_to_inreach_via_email() a la place", flush=True)
    return False

def process_workflow():
    """Processus complet de traitement"""
    global last_status, last_check_time
    
    print("\n" + "="*70, flush=True)
    print(f"? TRAITEMENT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("="*70 + "\n", flush=True)
    
    if not check_credentials():
        return
    
    mail = connect_gmail()
    if not mail:
        return
    
    try:
        requests_list = check_for_requests(mail)
        
        if not requests_list:
            print("? Aucune nouvelle requete", flush=True)
            last_status = "? Aucune demande"
            return
        
        print(f"\n? {len(requests_list)} REQU?TE(S) TROUVEE(S)!", flush=True)
        
        for idx, req in enumerate(requests_list, 1):
            print(f"\n{'='*70}", flush=True)
            print(f"? Traitement requete {idx}/{len(requests_list)}", flush=True)
            print(f"   Type: {req['type']}", flush=True)
            print(f"{'='*70}", flush=True)
            
            # TRAITEMENT AI
            if req['type'] == 'ai':
                provider = req['provider']
                print(f"\n{'='*70}")
                print(f"{'='*70}")
                print(f"TRAITEMENT {provider.upper()}: {req['question'][:50]}...")
                print(f"Max words demande: {req['max_words']}")
                print(f"{'='*70}")
                
                # Appeler le bon fournisseur AI
                if provider == 'claude':
                    messages = query_claude(req['question'], req['max_words'])
                elif provider == 'mistral':
                    messages = query_mistral(req['question'], req['max_words'])
                else:
                    messages = [f"Provider inconnu: {provider}"]
                
                print(f"\n{'='*70}")
                print(f"? TOTAL DE {len(messages)} MESSAGES ? ENVOYER POUR {provider.upper()}")
                print(f"{'='*70}")
                
                # Afficher un apercu de tous les messages avant envoi
                for i, msg in enumerate(messages, 1):
                    preview = msg[:80] + "..." if len(msg) > 80 else msg
                    print(f"   Preview msg {i}/{len(messages)}: {preview}")
                
                print(f"\n{'='*70}")
                print(f"ENVOI DES {len(messages)} MESSAGES PAR EMAIL")
                print(f"{'='*70}\n")
                
                # Envoyer tous les messages via email
                if send_messages_to_inreach_via_email(req['reply_email'], messages):
                    print(f"??? SUCC?S COMPLET {provider.upper()}: {len(messages)} messages envoyes ???")
                    last_status = f"? {provider.upper()}: {len(messages)} msg OK"
                else:
                    print(f"?????? ECHEC {provider.upper()} ??????")
                    last_status = f"? {provider.upper()} echec"
                
                print("="*70 + "\n")
            
            # TRAITEMENT GRIB
            elif req['type'] == 'grib':
                print(f"\n{'='*70}", flush=True)
                print(f"TRAITEMENT GRIB: {req['request']}", flush=True)
                print(f"{'='*70}\n", flush=True)
                
                print("? Etape 1/4: Envoi a Saildocs...", flush=True)
                if not send_to_saildocs(req['request']):
                    print("? Echec envoi Saildocs", flush=True)
                    continue
                
                print("? Etape 2/4: Attente reponse Saildocs (max 5 min)...", flush=True)
                grib_data = wait_for_saildocs_response(mail, timeout=300)
                
                if not grib_data:
                    print("? Pas de reponse Saildocs recue", flush=True)
                    continue
                
                print(f"? GRIB recu: {len(grib_data)} octets", flush=True)
                
                print("? Etape 3/4: Encodage et decoupage...", flush=True)
                messages = encode_grib_to_messages(grib_data)
                print(f"? {len(messages)} messages GRIB prets", flush=True)
                
                print(f"? Etape 4/4: Envoi vers inReach ({len(messages)} messages)...", flush=True)
                if send_messages_to_inreach_via_email(req['reply_email'], messages):
                    print(f"??? GRIB ENVOYE AVEC SUCC?S ({len(messages)} msg) ???", flush=True)
                    last_status = f"? GRIB envoye ({len(messages)} msg)"
                else:
                    print(f"? Echec envoi vers inReach", flush=True)
                    last_status = f"? Echec GRIB"
                
                print(f"\n? REQU?TE GRIB TRAITEE!\n", flush=True)
        
    except Exception as e:
        print(f"? Erreur workflow: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            mail.logout()
        except:
            pass
        print(f"\n{'='*60}")
        print("FIN TRAITEMENT")
        print(f"{'='*60}\n")

# ==========================================
# PLANIFICATION
# ==========================================

def run_scheduled_tasks():
    """Execute les taches planifiees"""
    print("\n? THREAD ACTIF", flush=True)
    thread_started.set()
    
    print("\n" + "="*60, flush=True)
    print("? PLANIFICATION", flush=True)
    print("="*60, flush=True)
    print("? Verification toutes les 5 MINUTES", flush=True)
    print("? Claude AI + Mistral AI actives", flush=True)
    print("="*60 + "\n", flush=True)
    
    try:
        # CHANGEMENT: Verification toutes les 5 minutes au lieu d'1 heure
        schedule.every(5).minutes.do(process_workflow)
        
        def heartbeat():
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f"? {current_time} - Service actif et en ecoute", flush=True)
        
        # Heartbeat toutes les 2 minutes pour confirmer que le service tourne
        schedule.every(2).minutes.do(heartbeat)
        
        print("? Premiere verification immediate...\n", flush=True)
        process_workflow()
        print("\n? Premiere verification terminee", flush=True)
        print(f"? Prochaine verification dans 5 minutes\n", flush=True)
        
    except Exception as e:
        print(f"? ERREUR: {e}", flush=True)
        import traceback
        traceback.print_exc()
    
    print("? Service actif - Verifications automatiques toutes les 5 minutes", flush=True)
    print("? Heartbeat toutes les 2 minutes", flush=True)
    print("=" * 60 + "\n", flush=True)
    
    loop_count = 0
    while True:
        try:
            loop_count += 1
            if loop_count % 5 == 0:  # Log toutes les 5 minutes
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f"? Loop #{loop_count} - {current_time} - En ecoute...", flush=True)
            
            schedule.run_pending()
            time.sleep(60)
        except Exception as e:
            print(f"? ERREUR boucle: {e}", flush=True)
            time.sleep(60)

# ==========================================
# DEMARRAGE
# ==========================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("? DEMARRAGE SERVICE GRIB INREACH + MULTI-AI")
    print("="*60)
    print(f"? {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"? Email: {GARMIN_USERNAME}")
    print(f"? Claude: {'?' if ANTHROPIC_API_KEY else '?'}")
    print(f"? Mistral: {'?' if MISTRAL_API_KEY else '?'}")
    print(f"? Port: {PORT}")
    print("="*60 + "\n")
    
    if not check_credentials():
        sys.exit(1)
    
    if not ANTHROPIC_API_KEY:
        print("??  Claude desactive (ANTHROPIC_API_KEY manquante)")
    
    if not MISTRAL_API_KEY:
        print("??  Mistral desactive (MISTRAL_API_KEY manquante)")
    
    print("? Demarrage thread...")
    scheduler_thread = Thread(target=run_scheduled_tasks, daemon=True)
    scheduler_thread.start()
    
    if thread_started.wait(timeout=10):
        print("? Thread actif\n")
    else:
        print("??  Thread ne repond pas\n")
    
    print(f"? Demarrage Flask sur port {PORT}...")
    print("="*60 + "\n")
    
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False)
    except KeyboardInterrupt:
        print("\n? Arret utilisateur")
    except Exception as e:
        print(f"\n? ERREUR CRITIQUE: {e}")
        sys.exit(1)
