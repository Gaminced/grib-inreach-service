# inreach_sender.py - v3.1.0
"""
Module envoi inReach - Gestion robuste multi-messages Playwright

CORRECTION PRINCIPALE :
- Après chaque envoi, l'UI Garmin doit être réarmée
- Re-sélection systématique du bouton Send
- Attente explicite de la réactivation du bouton ou du reset du textarea
"""

import time
import requests
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, TimeoutError
from config import (
    GARMIN_USERNAME,
    GARMIN_PASSWORD,
    SENDGRID_API_KEY,
    DELAY_BETWEEN_MESSAGES,
    INREACH_HEADERS,
    PLAYWRIGHT_BROWSER_PATH,
    PLAYWRIGHT_TIMEOUT
)


def send_via_playwright_inreachlink(url, messages):
    print(f"🎭 PLAYWRIGHT inReachLink: {len(messages)} messages", flush=True)

    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
                executable_path=PLAYWRIGHT_BROWSER_PATH
            )
            context = browser.new_context()
            page = context.new_page()

            # 1. Chargement page
            page.goto(url, wait_until="networkidle", timeout=PLAYWRIGHT_TIMEOUT)
            time.sleep(2)

            # 2. Login Garmin si nécessaire
            if "sso.garmin.com" in page.url or page.locator('input[type="email"]').count() > 0:
                print("🔐 Login Garmin...", flush=True)

                if page.locator('input[type="email"]').count() > 0:
                    page.fill('input[type="email"]', GARMIN_USERNAME)
                    page.keyboard.press("Enter")
                    page.wait_for_load_state("networkidle", timeout=20000)

                if page.locator('input[type="password"]').count() > 0:
                    page.fill('input[type="password"]', GARMIN_PASSWORD)
                    page.keyboard.press("Enter")
                    page.wait_for_load_state("networkidle", timeout=20000)

                time.sleep(2)

            # 3. Attente formulaire
            page.wait_for_selector("textarea", timeout=20000)
            print("✅ Formulaire prêt", flush=True)

            # 4. Envoi des messages
            for i, message in enumerate(messages, 1):
    print(f"📤 Message {i}/{len(messages)}", flush=True)

    if i > 1:
        time.sleep(DELAY_BETWEEN_MESSAGES)

    # 🔑 OBLIGATOIRE : rouvrir le formulaire Reply / Send
    print("🔁 Ouverture formulaire Send/Reply...", flush=True)

    open_button = page.locator(
        'button:has-text("Send"), button:has-text("Reply")'
    ).first

    open_button.wait_for(state="visible", timeout=15000)
    open_button.click()

    # Attendre que le textarea APPARAISSE réellement
    textarea = page.locator("textarea").first
    textarea.wait_for(state="visible", timeout=20000)

    # Remplissage
    textarea.fill("")
    time.sleep(0.5)
    textarea.fill(message)

    # Bouton Send interne au formulaire
    send_button = page.locator(
        'button:has-text("Send"), input[type="submit"]'
    ).last

    send_button.wait_for(state="visible", timeout=15000)
    send_button.click()

    # Attendre fermeture du formulaire
    page.wait_for_selector("textarea", state="detached", timeout=20000)

    print(f"✅ Message {i} envoyé", flush=True)

            print("🎉 Tous les messages envoyés", flush=True)
            browser.close()
            return True

        except Exception as e:
            print(f"❌ Erreur Playwright: {e}", flush=True)
            import traceback
            traceback.print_exc()
            if browser:
                browser.close()
            return False


def send_via_post_garmin(url, messages):
    parsed = urlparse(url)
    guid = parse_qs(parsed.query).get("extId", [None])[0]
    if not guid:
        return False

    success = 0
    for i, msg in enumerate(messages, 1):
        r = requests.post(
            url,
            headers=INREACH_HEADERS,
            data={
                "ReplyMessage": msg,
                "Guid": guid,
                "ReplyAddress": GARMIN_USERNAME,
            },
            timeout=30,
        )
        if r.status_code == 200:
            success += 1
        time.sleep(DELAY_BETWEEN_MESSAGES)

    return success == len(messages)


def send_via_email(reply_email, messages):
    if not SENDGRID_API_KEY:
        return False

    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    body = "\n\n---\n\n".join(messages)
    mail = Mail(
        from_email=GARMIN_USERNAME,
        to_emails=reply_email,
        subject="GRIB Weather Data Response",
        plain_text_content=body,
    )

    sg = SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(mail)
    return response.status_code in (200, 201, 202)


def send_to_inreach(url, messages, reply_email=None):
    if "inreachlink.com" in url:
        return send_via_playwright_inreachlink(url, messages)
    elif "garmin.com" in url and "extId" in url:
        return send_via_post_garmin(url, messages)
    elif reply_email:
        return send_via_email(reply_email)
    return False
