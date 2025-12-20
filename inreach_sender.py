# inreach_sender.py - v1.0
"""Module pour envoyer des messages via Garmin inReach"""

import time
import requests
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
from config import (GARMIN_USERNAME, GARMIN_PASSWORD, SENDGRID_API_KEY,
                    MAX_MESSAGE_LENGTH, DELAY_BETWEEN_MESSAGES, INREACH_HEADERS)


def extract_guid_from_url(url):
    """
    Extrait le GUID d'une URL inReach
    Supporte 2 formats:
    1. https://inreachlink.com/GUID
    2. https://eur.explore.garmin.com/textmessage/txtmsg?extId=...&adr=...
    """
    parsed = urlparse(url)
    
    # Format 1: inreachlink.com/GUID
    if 'inreachlink.com' in parsed.netloc:
        guid = parsed.path.strip('/')
        if guid:
            print(f"✅ GUID extrait (inreachlink): {guid}")
            return guid
    
    # Format 2: garmin.com avec extId
    if 'garmin.com' in parsed.netloc:
        params = parse_qs(parsed.query)
        if 'extId' in params:
            guid = params['extId'][0]
            print(f"✅ GUID extrait (garmin extId): {guid}")
            return guid
    
    print(f"❌ URL non reconnue: {url}")
    raise ValueError(f"GUID non trouvé dans l'URL")


def send_via_playwright(url, messages):
    """
    Envoie des messages via Playwright (pour URLs inreachlink.com)
    
    Args:
        url: URL inreachlink.com
        messages: Liste de messages à envoyer
        
    Returns:
        bool: True si succès
    """
    print(f"🎭 Envoi via Playwright: {len(messages)} messages")
    
    try:
        guid = extract_guid_from_url(url)
    except ValueError as e:
        print(f"❌ {e}")
        return False
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 1. Ouvrir l'URL
            print(f"   📂 Ouverture URL...")
            page.goto(url, timeout=30000)
            page.wait_for_load_state('networkidle')
            
            # 2. Login si nécessaire
            if 'login' in page.url.lower():
                print(f"   🔑 Login requis...")
                page.fill('input[type="email"]', GARMIN_USERNAME)
                page.fill('input[type="password"]', GARMIN_PASSWORD)
                page.click('button[type="submit"]')
                page.wait_for_load_state('networkidle')
            
            success_count = 0
            
            # 3. Envoyer chaque message
            for i, message in enumerate(messages, 1):
                try:
                    print(f"   📤 Message {i}/{len(messages)}: {len(message)} chars")
                    
                    # Trouver et remplir le champ message
                    textarea = page.locator('textarea').first
                    textarea.fill(message)
                    
                    # Cliquer sur Send
                    send_button = page.locator('button:has-text("Send")').first
                    send_button.click()
                    
                    # Attendre confirmation
                    time.sleep(2)
                    
                    success_count += 1
                    print(f"   ✅ Message {i}/{len(messages)} envoyé")
                    
                    if i < len(messages):
                        time.sleep(DELAY_BETWEEN_MESSAGES)
                        
                except Exception as e:
                    print(f"   ❌ Erreur message {i}: {e}")
            
            browser.close()
            
            if success_count == len(messages):
                print(f"✅ Playwright: Tous messages envoyés!")
                return True
            else:
                print(f"⚠️  Playwright: {success_count}/{len(messages)} envoyés")
                return False
                
        except Exception as e:
            print(f"❌ Erreur Playwright: {e}")
            try:
                browser.close()
            except:
                pass
            return False


def send_via_post(url, messages):
    """
    Envoie des messages via POST direct (pour URLs explore.garmin.com)
    
    Args:
        url: URL explore.garmin.com/textmessage/txtmsg
        messages: Liste de messages
        
    Returns:
        bool: True si succès
    """
    print(f"📮 Envoi via POST: {len(messages)} messages")
    
    try:
        guid = extract_guid_from_url(url)
    except ValueError as e:
        print(f"❌ {e}")
        return False
    
    # Extraire adresse de réponse depuis URL
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    reply_address = params.get('adr', [GARMIN_USERNAME])[0]
    
    post_url = "https://explore.garmin.com/textmessage/txtmsg"
    success_count = 0
    
    for i, message in enumerate(messages, 1):
        try:
            print(f"   📤 Message {i}/{len(messages)}: {len(message)} chars")
            
            data = {
                'ReplyMessage': message,
                'Guid': guid,
                'ReplyAddress': reply_address
            }
            
            response = requests.post(
                post_url,
                data=data,
                headers=INREACH_HEADERS,
                timeout=30
            )
            
            if response.status_code == 200:
                success_count += 1
                print(f"   ✅ Message {i}/{len(messages)} envoyé")
            else:
                print(f"   ❌ Status {response.status_code}")
            
            if i < len(messages):
                time.sleep(DELAY_BETWEEN_MESSAGES)
                
        except Exception as e:
            print(f"   ❌ Erreur message {i}: {e}")
    
    if success_count == len(messages):
        print(f"✅ POST: Tous messages envoyés!")
        return True
    else:
        print(f"⚠️  POST: {success_count}/{len(messages)} envoyés")
        return False


def send_via_email(reply_email, messages):
    """
    Envoie des messages par email (méthode officielle Garmin)
    
    Args:
        reply_email: Adresse email de réponse
        messages: Liste de messages
        
    Returns:
        bool: True si succès
    """
    print(f"📧 Envoi via EMAIL: {len(messages)} messages")
    print(f"   📮 Destinataire: {reply_email}")
    
    if not reply_email or '@' not in reply_email:
        print(f"❌ Email invalide: {reply_email}")
        return False
    
    if not SENDGRID_API_KEY:
        print("❌ SENDGRID_API_KEY manquante")
        return False
    
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }
    
    success_count = 0
    
    for i, message in enumerate(messages, 1):
        try:
            print(f"   📨 Message {i}/{len(messages)}")
            
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
            
            if response.status_code == 202:
                success_count += 1
                print(f"   ✅ Message {i}/{len(messages)} envoyé")
            else:
                print(f"   ❌ Status {response.status_code}")
            
            if i < len(messages):
                time.sleep(DELAY_BETWEEN_MESSAGES)
                
        except Exception as e:
            print(f"   ❌ Erreur message {i}: {e}")
    
    if success_count == len(messages):
        print(f"✅ EMAIL: Tous messages envoyés!")
        return True
    else:
        print(f"⚠️  EMAIL: {success_count}/{len(messages)} envoyés")
        return False


def send_to_inreach(url, messages, reply_email=None):
    """
    Fonction principale d'envoi - choisit automatiquement la méthode
    
    Args:
        url: URL de réponse inReach
        messages: Liste de messages
        reply_email: Email de réponse (optionnel)
        
    Returns:
        bool: True si succès
    """
    print(f"\n📤 ENVOI INREACH: {len(messages)} messages")
    print(f"   URL: {url[:60]}...")
    
    # Priorité 1: Email si disponible (méthode officielle)
    if reply_email and '@' in reply_email:
        return send_via_email(reply_email, messages)
    
    # Priorité 2: Détection automatique selon URL
    if 'inreachlink.com' in url:
        return send_via_playwright(url, messages)
    elif 'garmin.com' in url and 'textmessage' in url:
        return send_via_post(url, messages)
    else:
        print(f"❌ URL non supportée: {url}")
        return False
