# inreach_sender.py - v3.1.0
"""Module envoi inReach - Gestion dynamique boutons Send Reply / Dismiss"""

import time
import requests
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
from config import (GARMIN_USERNAME, GARMIN_PASSWORD, SENDGRID_API_KEY,
                    DELAY_BETWEEN_MESSAGES, INREACH_HEADERS, 
                    PLAYWRIGHT_BROWSER_PATH, PLAYWRIGHT_TIMEOUT)


def send_via_playwright_inreachlink(url, messages):
    """
    Envoie via Playwright pour URLs inreachlink.com
    GESTION DYNAMIQUE:
    - Détecte "Send Reply" si présent → clic avant remplissage
    - Sinon entre directement le message
    - Après envoi: vérifie et clique "Dismiss" si présent
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
            
            # 1. Charger page
            print("1. 🌐 Chargement inReachLink...", flush=True)
            page.goto(url, wait_until='networkidle', timeout=PLAYWRIGHT_TIMEOUT)
            time.sleep(2)
            
            # 2. Login si nécessaire
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
                print("2. ⏭️  Pas de login", flush=True)
            
            # 3. Attendre que la page soit prête
            print("3. ⏳ Attente page ready...", flush=True)
            time.sleep(2)
            
            # 4. Envoyer chaque message
            for i, message in enumerate(messages, 1):
                print(f"\n📤 Message {i}/{len(messages)}", flush=True)
                
                try:
                    if i > 1:
                        time.sleep(DELAY_BETWEEN_MESSAGES)
                    
                    # ═══════════════════════════════════════════════════
                    # ÉTAPE A: RECHERCHE DYNAMIQUE du bouton "Send Reply"
                    # ═══════════════════════════════════════════════════
                    print("🔍 Recherche bouton 'Send Reply'...", flush=True)
                    
                    # Chercher spécifiquement "Send Reply" (texte exact)
                    send_reply_btn = page.locator('button:has-text("Send Reply")')
                    
                    if send_reply_btn.count() > 0:
                        # CAS 1: Bouton "Send Reply" existe
                        print("   ✅ Bouton 'Send Reply' trouvé → clic", flush=True)
                        send_reply_btn.first.click()
                        time.sleep(1)  # Attendre ouverture formulaire
                    else:
                        # CAS 2: Pas de "Send Reply" 
                        print("   ⏭️  Pas de 'Send Reply' → formulaire déjà ouvert", flush=True)
                    
                    # ═══════════════════════════════════════════════════
                    # ÉTAPE B: REMPLIR le textarea
                    # ═══════════════════════════════════════════════════
                    print("📝 Remplissage message...", flush=True)
                    
                    # Attendre que textarea soit visible
                    textarea = page.locator("textarea").first
                    textarea.wait_for(state="visible", timeout=20000)
                    
                    # Remplir le message
                    textarea.fill("")
                    time.sleep(0.5)
                    textarea.fill(message)
                    time.sleep(0.5)
                    
                    # ═══════════════════════════════════════════════════
                    # ÉTAPE C: CLIQUER sur bouton "Send" final
                    # ═══════════════════════════════════════════════════
                    print("🚀 Clic bouton Send...", flush=True)
                    
                    # Bouton "Send" dans le formulaire (dernier bouton Send trouvé)
                    send_button = page.locator('button:has-text("Send")').last
                    send_button.wait_for(state="visible", timeout=15000)
                    send_button.click()
                    
                    # Attendre fermeture du formulaire
                    page.wait_for_selector("textarea", state="detached", timeout=20000)
                    time.sleep(1)
                    
                    print(f"   ✅ Message {i} envoyé", flush=True)
                    
                    # ═══════════════════════════════════════════════════
                    # ÉTAPE D: VÉRIFIER bouton "Dismiss" après envoi
                    # ═══════════════════════════════════════════════════
                    print("🔔 Recherche notification 'Dismiss'...", flush=True)
                    
                    # Attendre un peu que la notification apparaisse
                    time.sleep(1.5)
                    
                    # Chercher bouton Dismiss (texte exact ou aria-label)
                    dismiss_btn = page.locator('button:has-text("Dismiss"), button[aria-label*="Dismiss"]')
                    
                    if dismiss_btn.count() > 0:
                        print("   ✅ Notification trouvée → clic Dismiss", flush=True)
                        dismiss_btn.first.click()
                        time.sleep(0.5)
                    else:
                        print("   ⏭️  Pas de notification Dismiss", flush=True)
                    
                except Exception as e:
                    print(f"   ❌ Erreur message {i}: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"\n✅ Playwright terminé - {len(messages)} messages traités", flush=True)
            browser.close()
            return True
            
        except Exception as e:
            print(f"❌ Erreur Playwright globale: {e}", flush=True)
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
            return False
        
        success_count = 0
        for i, message in enumerate(messages, 1):
            data = {'ReplyMessage': message, 'Guid': guid, 'ReplyAddress': GARMIN_USERNAME}
            response = requests.post(url, headers=INREACH_HEADERS, data=data, timeout=30)
            
            if response.status_code == 200:
                success_count += 1
                print(f"   ✅ Message {i}/{len(messages)}", flush=True)
            
            if i < len(messages):
                time.sleep(DELAY_BETWEEN_MESSAGES)
        
        return success_count == len(messages)
    except Exception as e:
        print(f"❌ Erreur POST: {e}", flush=True)
        return False


def send_via_email(reply_email, messages):
    """Envoie via email SendGrid"""
    if not SENDGRID_API_KEY:
        return False
    
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        combined = "\n\n---\n\n".join([f"Message {i}/{len(messages)}:\n{msg}" for i, msg in enumerate(messages, 1)])
        
        email_content = Mail(
            from_email=GARMIN_USERNAME,
            to_emails=reply_email,
            subject='GRIB Weather Data Response',
            plain_text_content=combined
        )
        
        response = sg.send(email_content)
        return response.status_code in [200, 201, 202]
    except Exception as e:
        print(f"❌ Erreur email: {e}", flush=True)
        return False


def send_to_inreach(url, messages, reply_email=None):
    """Routeur intelligent pour envoi inReach"""
    print(f"\n{'='*70}", flush=True)
    print(f"📤 ENVOI INREACH: {len(messages)} messages", flush=True)
    print(f"{'='*70}\n", flush=True)
    
    if 'inreachlink.com' in url:
        print("🎯 Mode: PLAYWRIGHT", flush=True)
        return send_via_playwright_inreachlink(url, messages)
    elif 'garmin.com' in url and 'textmessage' in url and 'extId' in url:
        print("🎯 Mode: POST", flush=True)
        return send_via_post_garmin(url, messages)
    elif reply_email:
        print("🎯 Mode: EMAIL", flush=True)
        return send_via_email(reply_email, messages)
    else:
        print(f"❌ URL non supportée", flush=True)
        return False
