# inreach_sender.py - v3.0.0
"""Module pour envoyer des messages via Garmin inReach - Playwright + POST + Email"""

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
                executable_path=PLAYWRIGHT_BROWSER_PATH
            )
            context = browser.new_context()
            page = context.new_page()
            
            # 1. Charger la page inReachLink
            print("1. 🌐 Chargement inReachLink...")
            page.goto(url, wait_until='networkidle', timeout=PLAYWRIGHT_TIMEOUT)
            time.sleep(2)
            
            # 2. Détecter si login Garmin nécessaire
            if 'sso.garmin.com' in page.url or page.locator('input[type="email"]').count() > 0:
                print("2. 🔐 Login Garmin détecté...")
                
                # Email
                email_input = page.locator('input[type="email"]')
                if email_input.count() > 0:
                    print("   ✍️  Saisie email...")
                    email_input.fill(GARMIN_USERNAME)
                    time.sleep(1)
                    page.keyboard.press('Enter')
                    page.wait_for_load_state('networkidle', timeout=15000)
                    time.sleep(2)
                
                # Password
                password_input = page.locator('input[type="password"]')
                if password_input.count() > 0:
                    print("   🔑 Saisie mot de passe...")
                    password_input.fill(GARMIN_PASSWORD)
                    time.sleep(1)
                    page.keyboard.press('Enter')
                    page.wait_for_load_state('networkidle', timeout=15000)
                    time.sleep(3)
                
                print("   ✅ Login terminé")
            else:
                print("2. ⏭️  Pas de login nécessaire")
            
            # 3. Attendre que le formulaire soit chargé
            print("3. ⏳ Attente formulaire...")
            page.wait_for_selector('textarea', timeout=20000)
            time.sleep(2)
            print("   ✅ Formulaire prêt")
            
            # 4. Envoyer chaque message
            for i, message in enumerate(messages, 1):
                try:
                    print(f"   📤 Message {i}/{len(messages)}: {len(message)} chars")
                    
                    # IMPORTANT: Attendre que la page soit prête entre chaque message
                    page.wait_for_load_state('networkidle', timeout=10000)
                    time.sleep(2)
                    
                    # CRITIQUE: Re-localiser textarea à CHAQUE fois (il peut être recréé)
                    textarea = page.locator('textarea').first
                    textarea.wait_for(state='visible', timeout=10000)
                    
                    # Vider d'abord le textarea
                    textarea.fill('')
                    time.sleep(0.5)
                    
                    # Remplir le message
                    textarea.fill(message)
                    time.sleep(1)
                    
                    # Cliquer sur le bouton d'envoi
                    send_button = page.locator('button:has-text("Send"), input[type="submit"]').first
                    send_button.click()
                    
                    # Attendre confirmation
                    time.sleep(3)
                    
                    # Vérifier succès
                    if 'sent' in page.content().lower() or 'success' in page.content().lower():
                        print(f"      ✅ Message {i}/{len(messages)} confirmé")
                    else:
                        print(f"      ⚠️  Message {i}/{len(messages)} envoyé (pas de confirmation)")
                    
                    # Délai entre messages
                    if i < len(messages):
                        print(f"      ⏳ Pause {DELAY_BETWEEN_MESSAGES}s...")
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


def send_via_post_garmin(url, messages):
    """
    Envoie via POST pour URLs explore.garmin.com
    
    Args:
        url: URL explore.garmin.com avec extId
        messages: Liste de messages
        
    Returns:
        bool: True si succès
    """
    print(f"📮 POST Garmin: {len(messages)} messages")
    print(f"   URL: {url}")
    
    try:
        # Extraire GUID
        parsed = urlparse(url)
        guid = parse_qs(parsed.query).get('extId', [None])[0]
        
        if not guid:
            print("❌ GUID (extId) non trouvé dans URL")
            return False
        
        print(f"   ✅ GUID: {guid}")
        
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
                    headers=INREACH_HEADERS,
                    data=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    print(f"   ✅ Message {i}/{len(messages)} envoyé (Status: {response.status_code})")
                    success_count += 1
                else:
                    print(f"   ⚠️  Message {i}/{len(messages)} - Status: {response.status_code}")
                
                if i < len(messages):
                    time.sleep(DELAY_BETWEEN_MESSAGES)
                    
            except Exception as e:
                print(f"   ❌ Erreur message {i}/{len(messages)}: {e}")
        
        print(f"\n{'✅' if success_count == len(messages) else '⚠️ '} POST terminé: {success_count}/{len(messages)} messages envoyés")
        return success_count == len(messages)
        
    except Exception as e:
        print(f"❌ Erreur POST: {e}")
        return False


def send_via_email(reply_email, messages):
    """
    Envoie via email SendGrid (fallback)
    
    Args:
        reply_email: Email de destination
        messages: Liste de messages
        
    Returns:
        bool: True si succès
    """
    print(f"📧 EMAIL SendGrid: {len(messages)} messages")
    print(f"   Destinataire: {reply_email}")
    
    if not SENDGRID_API_KEY:
        print("❌ SendGrid non configuré")
        return False
    
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        
        # Combiner tous les messages en un seul email
        combined_message = "\n\n---\n\n".join(
            [f"Message {i}/{len(messages)}:\n{msg}" for i, msg in enumerate(messages, 1)]
        )
        
        email_content = Mail(
            from_email=GARMIN_USERNAME,
            to_emails=reply_email,
            subject='GRIB Weather Data Response',
            plain_text_content=combined_message
        )
        
        response = sg.send(email_content)
        
        if response.status_code in [200, 201, 202]:
            print(f"   ✅ Email envoyé (Status: {response.status_code})")
            return True
        else:
            print(f"   ⚠️  Email Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur email: {e}")
        return False


def send_to_inreach(url, messages, reply_email=None):
    """
    Routeur intelligent pour envoi inReach
    
    Détecte automatiquement le type d'URL:
    - inreachlink.com → Playwright (navigation complète)
    - explore.garmin.com avec extId → POST direct
    - Sinon → Email (si reply_email disponible)
    
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
