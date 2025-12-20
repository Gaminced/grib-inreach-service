# email_monitor.py - v1.0
"""Module pour surveiller Gmail et détecter les requêtes"""

import imaplib
import email
import re
from config import GARMIN_USERNAME, GARMIN_PASSWORD, IMAP_HOST, IMAP_PORT
from utils import parse_ai_request


def connect_gmail():
    """
    Connexion à Gmail via IMAP
    
    Returns:
        imaplib.IMAP4_SSL: Connexion ou None
    """
    try:
        print(f"📧 Connexion IMAP: {GARMIN_USERNAME}")
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(GARMIN_USERNAME, GARMIN_PASSWORD)
        print("✅ Connexion IMAP réussie")
        return mail
    except Exception as e:
        print(f"❌ Erreur IMAP: {e}")
        return None


def check_for_requests(mail):
    """
    Vérifie les emails non lus pour requêtes GRIB/AI
    
    Args:
        mail: Connexion IMAP
        
    Returns:
        list: Liste de dictionnaires avec les requêtes trouvées
    """
    try:
        mail.select("inbox")
        print("🔍 Recherche emails non lus...")
        
        status, messages = mail.search(None, 'UNSEEN')
        
        if status != "OK":
            print("❌ Erreur recherche emails")
            return []
        
        email_ids = messages[0].split()
        print(f"📬 {len(email_ids)} email(s) non lu(s)")
        
        requests_list = []
        
        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            
            if status != "OK":
                continue
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Vérifier expéditeur
                    from_addr = msg.get('From', '').lower()
                    if 'inreach' not in from_addr and 'garmin' not in from_addr:
                        print(f"⏭ Email ignoré (pas inReach): {from_addr}")
                        continue
                    
                    # Extraire corps
                    body = extract_email_body(msg)
                    
                    print(f"\n📧 EMAIL:")
                    print(f"  From: {msg.get('From', 'Unknown')}")
                    print(f"  Subject: {msg.get('Subject', 'No subject')}")
                    print(f"  Body: {len(body)} chars")
                    
                    # Extraire Reply-To
                    reply_to = msg.get('Reply-To', '') or msg.get('From', '')
                    
                    # Extraire URL de réponse
                    reply_url = extract_reply_url(body)
                    if not reply_url:
                        print("⚠️  Email sans URL de réponse")
                        continue
                    
                    print(f"✅ URL: {reply_url[:60]}...")
                    print(f"📮 Reply-To: {reply_to}")
                    
                    # Vérifier requête AI
                    provider, max_words, question = parse_ai_request(body)
                    
                    if question:
                        print(f"✅ Requête {provider.upper()}: {question[:50]}...")
                        requests_list.append({
                            'type': 'ai',
                            'provider': provider,
                            'max_words': max_words,
                            'question': question,
                            'reply_url': reply_url,
                            'reply_email': reply_to
                        })
                        continue
                    
                    # Chercher requête GRIB
                    grib_pattern = re.compile(r'(ecmwf|gfs|icon):[^\s\n]+', re.IGNORECASE)
                    match = grib_pattern.search(body)
                    
                    if not match:
                        body_single_line = body.replace('\n', ' ')
                        match = grib_pattern.search(body_single_line)
                    
                    if match:
                        grib_request = match.group(0)
                        print(f"✅ Requête GRIB: {grib_request}")
                        
                        requests_list.append({
                            'type': 'grib',
                            'request': grib_request,
                            'reply_url': reply_url,
                            'reply_email': reply_to
                        })
                    else:
                        print(f"⚠ Email sans requête valide")
        
        grib_count = sum(1 for r in requests_list if r['type'] == 'grib')
        ai_count = sum(1 for r in requests_list if r['type'] == 'ai')
        print(f"✅ Trouvé: {grib_count} GRIB, {ai_count} AI")
        
        return requests_list
        
    except Exception as e:
        print(f"❌ Erreur vérification: {e}")
        import traceback
        traceback.print_exc()
        return []


def extract_email_body(msg):
    """
    Extrait le corps d'un email multipart
    
    Args:
        msg: Message email
        
    Returns:
        str: Corps du message
    """
    body_parts = []
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type in ["text/plain", "text/html"]:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        decoded = payload.decode('utf-8', errors='ignore')
                        body_parts.append(decoded)
                except:
                    pass
        return "\n\n".join(body_parts)
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                return payload.decode('utf-8', errors='ignore')
            return str(msg.get_payload())
        except:
            return str(msg.get_payload())


def extract_reply_url(body):
    """
    Extrait l'URL de réponse inReach depuis le corps
    
    Args:
        body: Corps de l'email
        
    Returns:
        str: URL ou None
    """
    # Format 1: inreachlink.com
    inreach_pattern = re.compile(r'https://inreachlink\.com/[A-Za-z0-9_-]+', re.IGNORECASE)
    match = inreach_pattern.search(body)
    
    if match:
        return match.group(0).strip()
    
    # Format 2: garmin.com
    garmin_pattern = re.compile(r'https://[^\s]+garmin\.com/[^\s]+', re.IGNORECASE)
    match = garmin_pattern.search(body)
    
    if match:
        return match.group(0).strip().rstrip('.,;)\'"<>')
    
    return None
