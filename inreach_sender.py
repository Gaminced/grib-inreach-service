# inreach_sender.py - v3.1.3
"""Module envoi inReach - Recherche dynamique tous boutons Send*"""

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
    RECHERCHE DYNAMIQUE:
    - Détecte TOUS les boutons commençant par "Send" (Reply, Message, etc)
    - Clic sur le premier trouvé pour ouvrir le formulaire
    - Remplissage et envoi
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
            print("   ✅ Page prête", flush=True)
            
            # 4. Envoyer chaque message
            for i, message in enumerate(messages, 1):
                print(f"\n{'─'*50}", flush=True)
                print(f"📤 Message {i}/{len(messages)}", flush=True)
                print(f"{'─'*50}", flush=True)
                
                try:
                    if i > 1:
                        print(f"⏳ Délai {DELAY_BETWEEN_MESSAGES}s entre messages...", flush=True)
                        time.sleep(DELAY_BETWEEN_MESSAGES)
                        
                        # ATTENTE SUPPLÉMENTAIRE après envoi précédent
                        print("⏳ Attente stabilisation page...", flush=True)
                        page.wait_for_load_state('networkidle', timeout=15000)
                        time.sleep(3)
                    
                    # ═══════════════════════════════════════════════════
                    # ÉTAPE A: RECHERCHE DYNAMIQUE de TOUS boutons Send*
                    # Détecte: "Send Reply", "Send Message", etc.
                    # ═══════════════════════════════════════════════════
                    print("🔍 Recherche boutons 'Send*'...", flush=True)
                    time.sleep(2)
                    
                    # Chercher TOUS les boutons contenant "Send" au début du texte
                    # Patterns possibles: "Send Reply", "Send Message", "Send", etc.
                    send_buttons = page.locator('button').filter(has_text="Send")
                    
                    # Compter combien de boutons "Send*" sont présents
                    send_count = send_buttons.count()
                    print(f"   🔢 {send_count} bouton(s) 'Send*' trouvé(s)", flush=True)
                    
                    # Lister tous les boutons trouvés pour debug
                    if send_count > 0:
                        for idx in range(send_count):
                            btn_text = send_buttons.nth(idx).text_content()
                            print(f"      - Bouton {idx+1}: '{btn_text}'", flush=True)
                    
                    # Chercher spécifiquement les boutons d'ouverture de formulaire
                    # (pas le bouton final "Send" dans le formulaire)
                    open_form_btn = None
                    
                    # Essayer "Send Reply" en priorité
                    send_reply = page.locator('button:has-text("Send Reply")')
                    if send_reply.count() > 0:
                        open_form_btn = send_reply.first
                        print("   ✅ Bouton 'Send Reply' trouvé", flush=True)
                    else:
                        # Essayer "Send Message"
                        send_msg = page.locator('button:has-text("Send Message")')
                        if send_msg.count() > 0:
                            open_form_btn = send_msg.first
                            print("   ✅ Bouton 'Send Message' trouvé", flush=True)
                    
                    # Si bouton d'ouverture trouvé, cliquer
                    if open_form_btn:
                        print("   🖱️  Clic pour ouvrir formulaire...", flush=True)
                        open_form_btn.wait_for(state="visible", timeout=10000)
                        open_form_btn.click()
                        time.sleep(2)
                    else:
                        print("   ⏭️  Pas de bouton ouverture → formulaire déjà ouvert", flush=True)
                    
                    # ═══════════════════════════════════════════════════
                    # ÉTAPE B: REMPLIR le textarea
                    # ═══════════════════════════════════════════════════
                    print("📝 Attente textarea...", flush=True)
                    
                    # Attendre que textarea soit visible
                    textarea = page.locator("textarea").first
                    textarea.wait_for(state="visible", timeout=30000)
                    time.sleep(1)
                    
                    print("📝 Remplissage message...", flush=True)
                    textarea.fill("")
                    time.sleep(0.5)
                    textarea.fill(message)
                    time.sleep(1)
                    
                    # ═══════════════════════════════════════════════════
                    # ÉTAPE C: CLIQUER sur bouton "Send" FINAL
                    # (le dernier "Send" trouvé = celui dans le formulaire)
                    # ═══════════════════════════════════════════════════
                    print("🚀 Recherche bouton Send final...", flush=True)
                    
                    # Prendre le DERNIER bouton "Send" = celui du formulaire
                    send_final = page.locator('button:has-text("Send")').last
                    send_final.wait_for(state="visible", timeout=15000)
                    time.sleep(0.5)
                    
                    print("🚀 Clic bouton Send...", flush=True)
                    send_final.click()
                    
                    # Attendre fermeture du formulaire
                    print("⏳ Attente fermeture formulaire...", flush=True)
                    page.wait_for_selector("textarea", state="detached", timeout=20000)
                    time.sleep(2)
                    
                    print(f"   ✅ Message {i} envoyé", flush=True)
                    
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
