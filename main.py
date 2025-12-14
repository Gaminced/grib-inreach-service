#!/usr/bin/env python3

-- coding: utf-8 --

""" Version corrigée de main.pi Objectif : garantir l'envoi des messages vers Garmin inReach EN UTILISANT STRICTEMENT la même méthode que main.working.without.cloud.request.py

👉 AUCUN appel à l'API fixe Garmin 👉 POST direct sur l'URL de réponse inReach (reply_url) 👉 Cookies + headers identiques

Cette version est volontairement minimaliste et robuste. """

import os import time import requests from urllib.parse import urlparse, parse_qs

==========================================

CONFIGURATION

==========================================

GARMIN_USERNAME = os.environ.get('GARMIN_USERNAME')

MAX_MESSAGE_LENGTH = 120 DELAY_BETWEEN_MESSAGES = 5

relational_HEADERS = { 'authority': 'eur.explore.garmin.com', 'accept': '/', 'accept-language': 'en-US,en;q=0.9', 'content-type': 'application/x-www-form-urlencoded; charset=UTF-8', 'origin': 'https://eur.explore.garmin.com', 'sec-fetch-mode': 'cors', 'sec-fetch-site': 'same-origin', 'user-agent': 'Mozilla/5.0', 'x-requested-with': 'XMLHttpRequest', }

INREACH_COOKIES = { 'BrowsingMode': 'Desktop', }

==========================================

OUTILS

==========================================

def extract_guid_from_url(url): """ Extraction GUID compatible ANCIEN + NOUVEAU format """ parsed = urlparse(url)

# Nouveau format : https://inreachlink.com/GUID
if 'inreachlink.com' in url:
    guid = parsed.path.split('/')[-1]
    if guid:
        return guid

# Ancien format Garmin
guid_list = parse_qs(parsed.query).get('extId')
if guid_list:
    return guid_list[0]

raise ValueError('GUID introuvable dans l\'URL inReach')

==========================================

MÉTHODE GARMIN QUI FONCTIONNE

==========================================

def send_messages_to_inreach(reply_url, messages): """ ⚠️ MÉTHODE VALIDÉE - POST DIRECT sur reply_url - EXACTEMENT comme main.working.without.cloud.request.py """

print(f"📤 Envoi de {len(messages)} messages vers inReach")

try:
    guid = extract_guid_from_url(reply_url)
    print(f"✅ GUID extrait: {guid}")
except Exception as e:
    print(f"❌ Erreur GUID: {e}")
    return False

success = 0

for i, message in enumerate(messages, 1):
    try:
        data = {
            'ReplyMessage': message,
            'Guid': guid,
            'ReplyAddress': GARMIN_USERNAME,
        }

        response = requests.post(
            reply_url,              # ⚠️ CRITIQUE
            headers=relational_HEADERS,
            cookies=INREACH_COOKIES,
            data=data,
            timeout=30
        )

        if response.status_code == 200:
            print(f"✅ Message {i}/{len(messages)} envoyé")
            success += 1
        else:
            print(f"⚠ Message {i} échec ({response.status_code})")
            print(response.text[:200])

        if i < len(messages):
            time.sleep(DELAY_BETWEEN_MESSAGES)

    except Exception as e:
        print(f"❌ Exception message {i}: {e}")

print(f"📊 Résultat: {success}/{len(messages)} messages envoyés")
return success == len(messages)

==========================================

TEST MANUEL (OPTIONNEL)

==========================================

if name == 'main': # Exemple de test rapide test_url = 'https://inreachlink.com/REPLACE_GUID' test_messages = ['Test message 1', 'Test message 2']

send_messages_to_inreach(test_url, test_messages)
