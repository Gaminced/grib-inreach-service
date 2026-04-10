# email_monitor.py - v3.2.4
"""
Surveillance Gmail pour requêtes GRIB et AI (Claude/Mistral)
v3.2.4: 
- Support GRIB étendu : ECMWF, GFS, ICON, RTOFS
- Patterns tolérants (cg150 ou cg 150)
- Découpage 120 chars avec coût/solde
"""

import imaplib
import email
import re
import sys
from datetime import datetime
from config import GARMIN_USERNAME, GARMIN_PASSWORD
from grib_handler import process_grib_request
from claude_handler import handle_claude_maritime_assistant, handle_claude_request, split_long_response as claude_split
from mistral_handler import handle_mistral_maritime_assistant, handle_mistral_request, handle_mistral_weather_expert, split_long_response as mistral_split
from inreach_sender import send_to_inreach

def check_gmail():
    """Vérifie Gmail pour nouvelles requêtes inReach"""
    print("\n" + "="*70)
    print(f"🔄 VÉRIFICATION EMAIL - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    mail = None
    requests_found = []
    
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        mail.login(GARMIN_USERNAME, GARMIN_PASSWORD)
        mail.select('inbox')
        
        status, messages = mail.search(None, '(UNSEEN FROM "inreach")')
        
        if status != 'OK':
            if mail: mail.logout()
            return
        
        email_ids = messages[0].split()
        if not email_ids:
            print("✓ Aucun nouveau message")
            mail.logout()
            return
        
        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            if status != 'OK': continue
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    body = extract_email_body(msg)
                    reply_url = extract_reply_url(body)
                    
                    if not reply_url: continue
                    
                    request_info = detect_request_type(body)
                    if request_info:
                        request_info['reply_url'] = reply_url
                        requests_found.append(request_info)
        
        if mail: mail.logout()
        
        # Traitement des requêtes
        for req in requests_found:
            if req['type'] == 'claude_maritime':
                process_claude_maritime_wrapper(req)
            elif req['type'] == 'claude_generic':
                process_claude_generic_wrapper(req)
            elif req['type'] == 'mistral_maritime':
                process_mistral_maritime_wrapper(req)
            elif req['type'] == 'mistral_generic':
                process_mistral_generic_wrapper(req)
            elif req['type'] == 'weather':
                process_weather_wrapper(req)
            elif req['type'] == 'grib':
                process_grib_request(req['request'], req['reply_url'])
                
    except Exception as e:
        print(f"❌ Erreur check_gmail: {e}")
    finally:
        if mail:
            try: mail.logout()
            except: pass

def extract_email_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() in ["text/plain", "text/html"]:
                payload = part.get_payload(decode=True)
                if payload: body += payload.decode('utf-8', errors='ignore')
    else:
        payload = msg.get_payload(decode=True)
        body = payload.decode('utf-8', errors='ignore') if payload else ""
    return body

def extract_reply_url(body):
    inreach_pattern = re.compile(r'https://inreachlink\.com/[A-Za-z0-9_-]+', re.IGNORECASE)
    match = inreach_pattern.search(body)
    if match: return match.group(0).strip()
    
    garmin_pattern = re.compile(r'https://[^\s]+garmin\.com/[^\s]+', re.IGNORECASE)
    match = garmin_pattern.search(body)
    return match.group(0).strip().rstrip('.,;)\'"<>') if match else None

def detect_request_type(body):
    # Patterns AI
    patterns = {
        'claude_generic': r'\bcg\s*(\d+)\s*:\s*(.+)',
        'mistral_generic': r'\bmg\s*(\d+)\s*:\s*(.+)',
        'claude_maritime': r'\bc\s*(\d+)\s*:\s*(.+)',
        'mistral_maritime': r'\bm\s*(\d+)\s*:\s*(.+)',
        'weather': r'\bw\s*(\d+)\s*:\s*(.+)'
    }
    
    for key, pat in patterns.items():
        match = re.search(pat, body, re.IGNORECASE | re.DOTALL)
        if match:
            return {'type': key, 'max_tokens': int(match.group(1))*3, 'question': match.group(2).strip()}

    # Pattern GRIB étendu (GFS, ECMWF, ICON, RTOFS)
    grib_pattern = re.compile(r'(ecmwf|gfs|icon|rtofs):[^\s\n]+', re.IGNORECASE)
    match = grib_pattern.search(body)
    if match:
        return {'type': 'grib', 'request': match.group(0)}
    return None

def process_claude_maritime_wrapper(req):
    resp, cost = handle_claude_maritime_assistant(req['question'])
    send_to_inreach(req['reply_url'], claude_split(resp, cost, 120))

def process_claude_generic_wrapper(req):
    resp, cost = handle_claude_request(req['question'], req['max_tokens'])
    send_to_inreach(req['reply_url'], claude_split(resp, cost, 120))

def process_mistral_maritime_wrapper(req):
    resp, cost = handle_mistral_maritime_assistant(req['question'])
    send_to_inreach(req['reply_url'], mistral_split(resp, cost, 120))

def process_mistral_generic_wrapper(req):
    resp, cost = handle_mistral_request(req['question'], req['max_tokens'])
    send_to_inreach(req['reply_url'], mistral_split(resp, cost, 120))

def process_weather_wrapper(req):
    resp, cost = handle_mistral_weather_expert(req['question'])
    send_to_inreach(req['reply_url'], mistral_split(resp, cost, 120))
