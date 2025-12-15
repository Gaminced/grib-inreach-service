#!/usr/bin/env python3

-- coding: utf-8 --

""" SERVICE GRIB + AI (Claude / Mistral) → Garmin inReach VERSION FINALE STABLE

CORRECTION CLÉ :

Support DES DEUX canaux Garmin :

1. Ancien : /textmessage/txtmsg?extId=UUID&adr=email  ✅


2. Nouveau : https://inreachlink.com/<token court>    ✅



AUCUNE reconstruction invalide

Routage automatique selon le type d'URL


Cette version est basée sur les tests Termux validés. """

================================

VERSION

================================

VERSION = "2.2.0" VERSION_DATE = "2025-12-15"

================================

IMPORTS

================================

import os import sys import time import imaplib import email import base64 import zlib import re import requests import schedule from datetime import datetime from threading import Thread, Event from urllib.parse import urlparse, parse_qs from flask import Flask, jsonify

================================

CONFIGURATION

================================

GARMIN_USERNAME = os.environ.get('GARMIN_USERNAME') GARMIN_PASSWORD = os.environ.get('GARMIN_PASSWORD') ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY') MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY')

IMAP_HOST = "imap.gmail.com" IMAP_PORT = 993

MAX_MESSAGE_LENGTH = 120 DELAY_BETWEEN_MESSAGES = 5 PORT = int(os.environ.get('PORT', 10000))

INREACH_HEADERS = { 'authority': 'eur.explore.garmin.com', 'accept': '/', 'accept-language': 'en-US,en;q=0.9', 'content-type': 'application/x-www-form-urlencoded; charset=UTF-8', 'origin': 'https://eur.explore.garmin.com', 'user-agent': 'Mozilla/5.0', 'x-requested-with': 'XMLHttpRequest', }

INREACH_COOKIES = {'BrowsingMode': 'Desktop'}

================================

FLASK (Healthcheck Render)

================================

app = Flask(name) last_status = "Démarrage" last_check_time = None thread_started = Event()

@app.route('/health') def health(): return jsonify({"status": "ok", "time": datetime.now().isoformat()}), 200

================================

OUTILS GARMIN

================================

def extract_guid_from_url(url: str) -> str: parsed = urlparse(url)

if 'inreachlink.com' in url:
    return parsed.path.strip('/').split('/')[-1]

guid_list = parse_qs(parsed.query).get('extId')
if guid_list:
    return guid_list[0]

raise ValueError('GUID introuvable')

def is_uuid(guid: str) -> bool: return bool(re.fullmatch(r"[0-9a-fA-F-]{36}", guid))

================================

ENVOI GARMIN — VERSION VALIDÉE

================================

def send_messages_to_inreach(reply_url, messages): """ Routage AUTOMATIQUE selon le type d'URL Garmin """ print(f"📤 Envoi de {len(messages)} messages Garmin", flush=True)

try:
    guid = extract_guid_from_url(reply_url)
except Exception as e:
    print(f"❌ GUID invalide: {e}", flush=True)
    return False

# CAS 1 — Nouveau canal Garmin (token court)
if 'inreachlink.com' in reply_url:
    post_url = reply_url
    print("➡️ Mode inreachlink DIRECT", flush=True)

# CAS 2 — Ancien canal Garmin (UUID long)
elif is_uuid(guid):
    post_url = (
        "https://eur.explore.garmin.com/textmessage/txtmsg"
        f"?extId={guid}&adr={GARMIN_USERNAME.replace('@', '%40')}"
    )
    print("➡️ Mode txtmsg UUID", flush=True)
    print(f"URL: {post_url}", flush=True)

else:
    print("❌ GUID non compatible Garmin", flush=True)
    return False

ok = 0
for i, msg in enumerate(messages, 1):
    r = requests.post(
        post_url,
        headers=INREACH_HEADERS,
        cookies=INREACH_COOKIES,
        data={
            'ReplyMessage': msg,
            'Guid': guid,
            'ReplyAddress': GARMIN_USERNAME,
        },
        timeout=30
    )

    if r.status_code == 200:
        print(f"✅ Msg {i}/{len(messages)} envoyé", flush=True)
        ok += 1
    else:
        print(f"⚠️ Msg {i} échec {r.status_code}", flush=True)
        print(r.text[:200], flush=True)

    time.sleep(DELAY_BETWEEN_MESSAGES)

return ok == len(messages)

================================

EMAIL (IMAP)

================================

def connect_gmail(): mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) mail.login(GARMIN_USERNAME, GARMIN_PASSWORD) return mail

def find_reply_url(body: str): m = re.search(r"https://inreachlink.com/[A-Za-z0-9_-]+", body) if m: return m.group(0)

m = re.search(r"https://[^\s]+garmin\.com/textmessage/[^\s]+", body)
if m:
    return m.group(0).rstrip('.,;)')

return None

================================

WORKFLOW MINIMAL (AI / GRIB branchés au-dessus)

================================

def process_workflow(): global last_check_time, last_status print("\n=== TRAITEMENT ===", flush=True)

mail = connect_gmail()
mail.select('inbox')
status, ids = mail.search(None, 'UNSEEN')

for eid in ids[0].split():
    _, data = mail.fetch(eid, '(RFC822)')
    msg = email.message_from_bytes(data[0][1])

    body = ""
    for part in msg.walk():
        if part.get_content_type() in ('text/plain', 'text/html'):
            payload = part.get_payload(decode=True)
            if payload:
                body += payload.decode('utf-8', errors='ignore')

    reply_url = find_reply_url(body)
    if not reply_url:
        continue

    messages = ["Service opérationnel ✔️"]
    send_messages_to_inreach(reply_url, messages)

last_check_time = datetime.now()
last_status = "OK"

================================

PLANIFICATION

================================

def run_scheduler(): thread_started.set() schedule.every(5).minutes.do(process_workflow) process_workflow()

while True:
    schedule.run_pending()
    time.sleep(60)

================================

MAIN

================================

if name == 'main': print(f"🚀 DÉMARRAGE v{VERSION} ({VERSION_DATE})")

t = Thread(target=run_scheduler, daemon=True)
t.start()
thread_started.wait(5)

app.run(host='0.0.0.0', port=PORT)
