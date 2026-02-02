# inreach_sender.py - v3.5.0
"""Module envoi inReach - Version stable avec MAILERSEND"""

import time
import requests
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
from config import (GARMIN_USERNAME, GARMIN_PASSWORD, MAILERSEND_API_KEY,
                    DELAY_BETWEEN_MESSAGES, INREACH_HEADERS, 
                    PLAYWRIGHT_BROWSER_PATH, PLAYWRIGHT_TIMEOUT)


def send_via_playwright_inreachlink(url, messages):
    """
    Envoie via Playwright pour URLs inreachlink.com
    Gestion dynamique des boutons Send Reply / Send Message
    """
    print(f"🎭 PLAYWRIGHT inReachLink: {len(messages)} messages", flush=True)
    print(f"   URL: {url}", flush=True)
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox'],
                executable_path=PLAYWRIGHT_BROWSER_PATH
            )
            context = browser.new_context()
            page = context.new_page()
            
            # 1. Chargement initial
            print("1. 🌐 Chargement inReachLink...", flush=True)
            page.goto(url, wait_until='networkidle', timeout=PLAYWRIGHT_TIMEOUT)
            time.sleep(2)
            
            # 2. Login Garmin si nécessaire
            if 'sso.garmin.com' in page.url or page.locator('input[type="email"]').count() > 0:
                print("2. 🔐 Login Garmin...", flush=True)
                
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
                
                print("   ✅ Login terminé", flush=True)
            else:
                print("2. ⏭️  Pas de login nécessaire", flush=True)
            
            # 3. Attente page prête
            print("3. ⏳ Attente page ready...", flush=True)
            time.sleep(2)
            print("   ✅ Page prête", flush=True)
            
            # 4. Envoi des messages
            for i, message in enumerate(messages, 1):
                print(f"\n{'─'*50}", flush=True)
                print(f"📤 Message {i}/{len(messages)}", flush=True)
                print(f"{'─'*50}", flush=True)
                
                try:
                    # Délai entre messages
                    if i > 1:
                        print(f"⏳ Délai {DELAY_BETWEEN_MESSAGES}s...", flush=True)
                        time.sleep(DELAY_BETWEEN_MESSAGES)
                        
                        # Attente stabilisation après envoi précédent
                        print("⏳ Stabilisation page...", flush=True)
                        try:
                            page.wait_for_load_state('networkidle', timeout=10000)
                        except:
                            pass
                        time.sleep(2)
                    
                    # Recherche bouton d'ouverture formulaire
                    print("🔍 Recherche boutons Send*...", flush=True)
                    time.sleep(1)
                    
                    # Essayer "Send Reply" en priorité
                    send_reply = page.locator('button:has-text("Send Reply")')
                    send_msg = page.locator('button:has-text("Send Message")')
                    
                    if send_reply.count() > 0:
                        print("   ✅ 'Send Reply' trouvé → clic", flush=True)
                        send_reply.first.wait_for(state="visible", timeout=10000)
                        send_reply.first.click()
                        time.sleep(2)
                    elif send_msg.count() > 0:
                        print("   ✅ 'Send Message' trouvé → clic", flush=True)
                        send_msg.first.wait_for(state="visible", timeout=10000)
                        send_msg.first.click()
                        time.sleep(2)
                    else:
                        print("   ⏭️  Formulaire déjà ouvert", flush=True)
                    
                    # Attente et remplissage textarea
                    print("📝 Attente textarea...", flush=True)
                    textarea = page.locator("textarea").first
                    
                    try:
                        textarea.wait_for(state="visible", timeout=15000)
                    except:
                        print("   ⏳ Retry attente textarea...", flush=True)
                        time.sleep(3)
                        textarea.wait_for(state="visible", timeout=10000)
                    
                    print("📝 Remplissage message...", flush=True)
                    textarea.fill("")
                    time.sleep(0.3)
                    textarea.fill(message)
                    time.sleep(0.5)
                    
                    # Clic bouton Send final
                    print("🚀 Envoi...", flush=True)
                    send_final = page.locator('button:has-text("Send")').last
                    send_final.wait_for(state="visible", timeout=10000)
                    send_final.click()
                    
                    print("⏳ Attente envoi...", flush=True)
                    time.sleep(3)
                    
                    print(f"   ✅ Message {i} envoyé", flush=True)
                    
                except Exception as e:
                    print(f"   ❌ Erreur message {i}: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"\n{'='*50}", flush=True)
            print(f"✅ Envoi terminé: {len(messages)} messages", flush=True)
            print(f"{'='*50}\n", flush=True)
            
            browser.close()
            return True
            
        except Exception as e:
            print(f"❌ Erreur globale Playwright: {e}", flush=True)
            import traceback
            traceback.print_exc()
            if 'browser' in locals():
                browser.close()
            return False


def send_via_post_garmin(url, messages):
    """Envoie via POST pour URLs explore.garmin.com"""
    print(f"📮 POST Garmin: {len(messages)} messages", flush=True)
    
    try:
        parsed = urlparse(url)
        guid = parse_qs(parsed.query).get('extId', [None])[0]
        
        if not guid:
            print("❌ GUID non trouvé dans l'URL", flush=True)
            return False
        
        success_count = 0
        for i, message in enumerate(messages, 1):
            data = {
                'ReplyMessage': message,
                'Guid': guid,
                'ReplyAddress': GARMIN_USERNAME
            }
            
            response = requests.post(url, headers=INREACH_HEADERS, data=data, timeout=30)
            
            if response.status_code == 200:
                success_count += 1
                print(f"   ✅ Message {i}/{len(messages)}", flush=True)
            else:
                print(f"   ❌ Message {i} - HTTP {response.status_code}", flush=True)
            
            if i < len(messages):
                time.sleep(DELAY_BETWEEN_MESSAGES)
        
        return success_count == len(messages)
        
    except Exception as e:
        print(f"❌ Erreur POST: {e}", flush=True)
        return False


def send_via_email(reply_email, messages):
    """Envoie via email MailerSend"""
    if not MAILERSEND_API_KEY:
        print("❌ MAILERSEND_API_KEY non configurée", flush=True)
        return False
    
    try:
        # Combiner tous les messages
        combined = "\n\n---\n\n".join([
            f"Message {i}/{len(messages)}:\n{msg}" 
            for i, msg in enumerate(messages, 1)
        ])
        
        # API MailerSend
        url = "https://api.mailersend.com/v1/email"
        
        headers = {
            "Authorization": f"Bearer {MAILERSEND_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "from": {
                "email": "inreach@trial-0r83ql3zw7mgzw1j.mlsender.net",
                "name": "Garmin inReach"
            },
            "to": [
                {
                    "email": reply_email
                }
            ],
            "subject": "GRIB Weather Data Response",
            "text": combined
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 202:
            print(f"✅ Email envoyé ({len(messages)} messages)", flush=True)
            return True
        else:
            print(f"❌ Email erreur HTTP {response.status_code}", flush=True)
            return False
            
    except Exception as e:
        print(f"❌ Erreur email: {e}", flush=True)
        return False


def send_to_inreach(url, messages, reply_email=None):
    """
    Routeur intelligent pour envoi inReach
    Détecte automatiquement la méthode selon l'URL
    """
    print(f"\n{'='*70}", flush=True)
    print(f"📤 ENVOI INREACH: {len(messages)} messages", flush=True)
    print(f"{'='*70}\n", flush=True)
    
    # Choix de la méthode selon l'URL
    if 'inreachlink.com' in url:
        print("🎯 Mode: PLAYWRIGHT (inreachlink.com)", flush=True)
        return send_via_playwright_inreachlink(url, messages)
        
    elif 'garmin.com' in url and 'textmessage' in url and 'extId' in url:
        print("🎯 Mode: POST (explore.garmin.com)", flush=True)
        return send_via_post_garmin(url, messages)
        
    elif reply_email:
        print("🎯 Mode: EMAIL (MailerSend)", flush=True)
        return send_via_email(reply_email, messages)
        
    else:
        print(f"❌ URL non supportée: {url}", flush=True)
        return False
