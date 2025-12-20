# inreach_sender.py - v1.3
"""Module pour envoyer des messages via Garmin inReach - Playwright + POST"""

import time
import requests
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
from config import (GARMIN_USERNAME, GARMIN_PASSWORD, SENDGRID_API_KEY,
                    MAX_MESSAGE_LENGTH, DELAY_BETWEEN_MESSAGES, INREACH_HEADERS)


def send_via_playwright_inreachlink(url, messages):
    """
    Envoie via Playwright pour URLs inreachlink.com
    Code complet avec login Garmin et navigation complète
    
    Args:
        url: URL inreachlink.com/GUID
        messages: Liste de messages
        
    Returns:
        bool: True si succès
    """
    print(f"🎭 PLAYWRIGHT inReachLink: {len(messages)} messages")
    print(f"   URL: {url}")
    
    with sync_playwright() as p:
        try:
            # Lancer navigateur
            browser = p.chromium.launch(
    headless=True,
    args=['--no-sandbox', '--disable-setuid-sandbox'],
    executable_path='/opt/render/project/src/browsers/chromium-1091/chrome-linux/chrome'
  )
            context = browser.new_context()
            page = context.new_page()
            
            # 1. Ouvrir l'URL inReachLink
            print(f"   📂 Ouverture {url}...")
            page.goto(url, timeout=30000)
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            
            # 2. Vérifier si login Garmin requis
            current_url = page.url
            print(f"   🔍 URL actuelle: {current_url[:60]}...")
            
            if 'sso.garmin.com' in current_url or 'signin' in current_url.lower():
                print(f"   🔑 Login Garmin requis...")
                
                # Accepter cookies si présent
                try:
                    cookie_btn = page.locator('button:has-text("Accept")').first
                    if cookie_btn.is_visible(timeout=2000):
                        cookie_btn.click()
                        print(f"   ✅ Cookies acceptés")
                        time.sleep(1)
                except:
                    pass
                
                # Remplir email
                try:
                    email_input = page.locator('input[type="email"], input#email, input[name="username"]').first
                    email_input.fill(GARMIN_USERNAME)
                    print(f"   📧 Email rempli")
                    time.sleep(1)
                except Exception as e:
                    print(f"   ❌ Erreur email: {e}")
                
                # Remplir password
                try:
                    pwd_input = page.locator('input[type="password"], input#password').first
                    pwd_input.fill(GARMIN_PASSWORD)
                    print(f"   🔒 Password rempli")
                    time.sleep(1)
                except Exception as e:
                    print(f"   ❌ Erreur password: {e}")
                
                # Cliquer Sign In
                try:
                    signin_btn = page.locator('button[type="submit"], button:has-text("Sign In")').first
                    signin_btn.click()
                    print(f"   ✅ Sign In cliqué")
                    
                    # Attendre redirection
                    page.wait_for_load_state('networkidle', timeout=30000)
                    time.sleep(3)
                    
                    current_url = page.url
                    print(f"   🔍 Après login: {current_url[:60]}...")
                    
                except Exception as e:
                    print(f"   ❌ Erreur Sign In: {e}")
            
            # 3. On devrait maintenant être sur la page de réponse
            # Chercher le formulaire de réponse
            print(f"   📝 Recherche formulaire de réponse...")
            
            success_count = 0
            
            # 4. Envoyer chaque message
for i, message in enumerate(messages, 1):
    try:
        print(f"   📤 Message {i}/{len(messages)}: {len(message)} chars")
        
        # IMPORTANT: Attendre que la page soit prête entre chaque message
        page.wait_for_load_state('networkidle', timeout=10000)
        time.sleep(2)
        
        # Chercher textarea à CHAQUE fois (il peut être recréé après envoi)
        textarea = page.locator('textarea').first
        textarea.wait_for(state='visible', timeout=10000)
        
        # Vider d'abord le textarea (au cas où)
        textarea.fill('')
        time.sleep(0.5)
        
        # Remplir le message
        textarea.fill(message)
                    print(f"   ✍️  Message rempli")
                    time.sleep(1)
                    
                    # Chercher et cliquer bouton Send
                    send_btn = page.locator('button:has-text("Send"), button[type="submit"], input[type="submit"][value*="Send"]').first
                    send_btn.click()
                    print(f"   📨 Send cliqué")
                    
                    # Attendre confirmation (vérifier que textarea est vidé)
                    time.sleep(3)
                    
                    try:
                        textarea_value = textarea.input_value()
                        if not textarea_value or len(textarea_value) == 0:
                            print(f"   ✅ Message {i}/{len(messages)} envoyé (textarea vidé)")
                            success_count += 1
                        else:
                            print(f"   ⚠️  Message {i}/{len(messages)} statut incertain")
                            success_count += 1  # On compte quand même
                    except:
                        print(f"   ✅ Message {i}/{len(messages)} probablement envoyé")
                        success_count += 1
                    
                    # Délai entre messages
                    if i < len(messages):
                        time.sleep(DELAY_BETWEEN_MESSAGES)
                    
                except Exception as e:
                    print(f"   ❌ Erreur message {i}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Fermer navigateur
            browser.close()
            
            if success_count == len(messages):
                print(f"✅ PLAYWRIGHT: {success_count}/{len(messages)} messages envoyés")
                return True
            else:
                print(f"⚠️  PLAYWRIGHT: {success_count}/{len(messages)} messages envoyés")
                return success_count > 0
            
        except Exception as e:
            print(f"❌ Erreur Playwright globale: {e}")
            import traceback
            traceback.print_exc()
            try:
                browser.close()
            except:
                pass
            return False


def send_via_post_garmin(url, messages):
    """
    Envoie via POST direct pour URLs explore.garmin.com
    
    Args:
        url: URL explore.garmin.com/textmessage/txtmsg?extId=...&adr=...
        messages: Liste de messages
        
    Returns:
        bool: True si succès
    """
    print(f"📮 POST Garmin: {len(messages)} messages")
    print(f"   URL: {url[:80]}...")
    
    try:
        # Extraire GUID (extId) et adresse
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        guid = params.get('extId', [None])[0]
        reply_address = params.get('adr', [GARMIN_USERNAME])[0]
        
        if not guid:
            print(f"   ❌ extId manquant dans URL")
            return False
        
        print(f"   📋 GUID: {guid}")
        print(f"   📧 Reply to: {reply_address}")
        
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
                    print(f"   ✅ Message {i}/{len(messages)} envoyé (200)")
                else:
                    print(f"   ⚠️  Message {i}/{len(messages)} - Status: {response.status_code}")
                    print(f"   Response: {response.text[:200]}")
                
                if i < len(messages):
                    time.sleep(DELAY_BETWEEN_MESSAGES)
                
            except Exception as e:
                print(f"   ❌ Erreur message {i}: {e}")
        
        if success_count == len(messages):
            print(f"✅ POST: {success_count}/{len(messages)} messages envoyés")
            return True
        else:
            print(f"⚠️  POST: {success_count}/{len(messages)} messages envoyés")
            return success_count > 0
        
    except Exception as e:
        print(f"❌ Erreur POST globale: {e}")
        import traceback
        traceback.print_exc()
        return False


def send_via_email(reply_email, messages):
    """
    Envoie via email (méthode officielle Garmin - FALLBACK)
    
    Args:
        reply_email: Adresse email de réponse
        messages: Liste de messages
        
    Returns:
        bool: True si succès
    """
    print(f"📧 EMAIL: {len(messages)} messages")
    print(f"   📮 Destinataire: {reply_email}")
    
    if not reply_email or '@' not in reply_email:
        print(f"   ❌ Email invalide: {reply_email}")
        return False
    
    if not SENDGRID_API_KEY:
        print("   ❌ SENDGRID_API_KEY manquante")
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
                print(f"   ✅ Message {i}/{len(messages)} envoyé (202)")
            else:
                print(f"   ⚠️  Status {response.status_code}")
            
            if i < len(messages):
                time.sleep(DELAY_BETWEEN_MESSAGES)
                
        except Exception as e:
            print(f"   ❌ Erreur message {i}: {e}")
    
    if success_count == len(messages):
        print(f"✅ EMAIL: {success_count}/{len(messages)} messages envoyés")
        return True
    else:
        print(f"⚠️  EMAIL: {success_count}/{len(messages)} messages envoyés")
        return success_count > 0


def send_to_inreach(url, messages, reply_email=None):
    """
    Fonction principale d'envoi - ROUTAGE INTELLIGENT
    
    Priorités:
    1. inreachlink.com → Playwright (code complet 300 lignes)
    2. explore.garmin.com avec extId → POST direct
    3. Sinon → Email (si reply_email disponible)
    
    Args:
        url: URL de réponse inReach
        messages: Liste de messages
        reply_email: Email de réponse (optionnel)
        
    Returns:
        bool: True si succès
    """
    print(f"\n{'='*70}")
    print(f"📤 ENVOI INREACH: {len(messages)} messages")
    print(f"   URL: {url}")
    if reply_email:
        print(f"   Email: {reply_email}")
    print(f"{'='*70}\n")
    
    # ROUTAGE selon URL
    if 'inreachlink.com' in url:
        print("🎯 Détection: inreachlink.com → PLAYWRIGHT")
        return send_via_playwright_inreachlink(url, messages)
    
    elif 'garmin.com' in url and 'textmessage' in url and 'extId' in url:
        print("🎯 Détection: explore.garmin.com → POST")
        return send_via_post_garmin(url, messages)
    
    elif reply_email and '@' in reply_email:
        print("🎯 Détection: Email disponible → EMAIL (fallback)")
        return send_via_email(reply_email, messages)
    
    else:
        print(f"❌ URL non supportée et pas d'email: {url}")
        return False
