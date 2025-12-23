# email_monitor.py - v3.2.0
"""
Surveillance Gmail pour requêtes GRIB et AI (Claude/Mistral)
Architecture modulaire avec patterns courts maritimes/génériques

PATTERNS MARITIMES (assistant spécialisé navigation):
- c 150: question       → Claude maritime
- m 150: question       → Mistral maritime
- w 150: question       → Weather expert (Mistral météo)
- claude 150: question  → Claude maritime (compatibilité)
- mistral 150: question → Mistral maritime (compatibilité)

PATTERNS GÉNÉRIQUES (assistant standard):
- cg 150: question      → Claude générique
- mg 150: question      → Mistral générique

GRIB:
- ecmwf:...             → Fichiers GRIB météo
"""

import imaplib
import email
import re
from datetime import datetime
from config import GARMIN_USERNAME, GARMIN_PASSWORD
from grib_handler import process_grib_request
from claude_handler import handle_claude_maritime_assistant, handle_claude_request
from mistral_handler import handle_mistral_maritime_assistant, handle_mistral_request, handle_mistral_weather_expert
from inreach_sender import send_to_inreach


def check_gmail():
    """
    Vérifie Gmail pour nouvelles requêtes inReach
    Détecte et route: GRIB, Claude (maritime/générique), Mistral (maritime/générique/météo)
    """
    print("\n" + "="*70)
    print(f"🔄 VÉRIFICATION EMAIL - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    try:
        # Connexion IMAP
        print(f"📧 Connexion IMAP: {GARMIN_USERNAME}")
        mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        mail.login(GARMIN_USERNAME, GARMIN_PASSWORD)
        mail.select('inbox')
        print("✅ Connexion IMAP réussie\n")
        
        # Rechercher emails non lus de inReach
        print("🔍 Recherche emails inReach non lus...")
        status, messages = mail.search(None, '(UNSEEN FROM "inreach")')
        
        if status != 'OK':
            print("⚠️  Erreur recherche emails")
            mail.logout()
            return
        
        email_ids = messages[0].split()
        print(f"📬 {len(email_ids)} email(s) non lu(s) trouvé(s)\n")
        
        if not email_ids:
            print("✓ Aucun nouveau message")
            mail.logout()
            return
        
        # Traiter chaque email
        requests_found = []
        
        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            
            if status != 'OK':
                continue
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Vérifier que c'est bien un email inReach
                    from_addr = msg.get('From', '').lower()
                    if 'inreach' not in from_addr and 'garmin' not in from_addr:
                        print(f"⏭ Email ignoré (pas inReach): {from_addr}")
                        continue
                    
                    # Extraire le corps du message
                    body = extract_email_body(msg)
                    
                    if not body:
                        print("⚠️  Corps du message vide")
                        continue
                    
                    # Extraire URL de réponse
                    reply_url = extract_reply_url(body)
                    
                    if not reply_url:
                        print("❌ Pas d'URL de réponse trouvée")
                        continue
                    
                    print(f"\n{'='*70}")
                    print(f"📧 EMAIL TROUVÉ")
                    print(f"{'='*70}")
                    print(f"From: {msg.get('From', 'Unknown')}")
                    print(f"Subject: {msg.get('Subject', 'No subject')}")
                    print(f"Body length: {len(body)} chars")
                    print(f"Body preview: {body[:200]}...")
                    print(f"Reply URL: {reply_url}")
                    print(f"{'='*70}\n")
                    
                    # DÉTECTION TYPE DE REQUÊTE
                    request_info = detect_request_type(body)
                    
                    if request_info:
                        request_info['reply_url'] = reply_url
                        requests_found.append(request_info)
                        
                        print(f"✅ Requête détectée: {request_info['type'].upper()}")
                        if 'mode' in request_info:
                            print(f"   Mode: {request_info['mode']}")
                        if 'question' in request_info:
                            print(f"   Question: {request_info['question'][:100]}...")
                    else:
                        print("❓ Aucune requête reconnue dans cet email")
        
        # TRAITER LES REQUÊTES
        if not requests_found:
            print("\n✓ Aucune requête à traiter")
            mail.logout()
            return
        
        print(f"\n{'='*70}")
        print(f"🎯 TRAITEMENT DE {len(requests_found)} REQUÊTE(S)")
        print(f"{'='*70}\n")
        
        for idx, req in enumerate(requests_found, 1):
            print(f"\n{'='*70}")
            print(f"📋 Requête {idx}/{len(requests_found)}")
            print(f"{'='*70}")
            
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
                process_grib_request(req['request'], req['reply_url'], mail)
            
            print(f"{'='*70}\n")
        
        mail.logout()
        print("\n✅ Vérification terminée\n")
        
    except Exception as e:
        print(f"❌ Erreur check_gmail: {e}")
        import traceback
        traceback.print_exc()


def extract_email_body(msg):
    """Extrait le corps du message email"""
    body = ""
    body_parts = []
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type in ["text/plain", "text/html"]:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        decoded = payload.decode('utf-8', errors='ignore')
                        body_parts.append(decoded)
                except Exception as e:
                    print(f"   ⚠️ Erreur décodage partie: {e}")
        body = "\n\n".join(body_parts)
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode('utf-8', errors='ignore')
            else:
                body = str(msg.get_payload())
        except:
            body = str(msg.get_payload())
    
    return body


def extract_reply_url(body):
    """Extrait l'URL de réponse inReach du corps du message"""
    # Format 1: https://inreachlink.com/GUID
    inreach_pattern = re.compile(r'https://inreachlink\.com/[A-Za-z0-9_-]+', re.IGNORECASE)
    match = inreach_pattern.search(body)
    
    if match:
        return match.group(0).strip()
    
    # Format 2: https://...garmin.com/textmessage/...
    garmin_pattern = re.compile(r'https://[^\s]+garmin\.com/[^\s]+', re.IGNORECASE)
    match = garmin_pattern.search(body)
    
    if match:
        return match.group(0).strip().rstrip('.,;)\'"<>')
    
    return None


def detect_request_type(body):
    """
    Détecte le type de requête avec patterns courts
    
    MARITIMES:
    - c 150: question       → Claude maritime
    - m 150: question       → Mistral maritime
    - w 150: question       → Weather expert
    - claude 150: question  → Claude maritime
    - mistral 150: question → Mistral maritime
    
    GÉNÉRIQUES:
    - cg 150: question      → Claude générique
    - mg 150: question      → Mistral générique
    
    GRIB:
    - ecmwf:...
    
    Returns:
        dict avec type et paramètres, ou None
    """
    print(f"\n{'='*70}")
    print("🔍 DÉTECTION TYPE DE REQUÊTE")
    print(f"{'='*70}")
    
    # ========================================
    # PATTERNS GÉNÉRIQUES (priorité haute)
    # ========================================
    
    # PATTERN 1: Claude générique "cg 150: question"
    cg_pattern = re.compile(
        r'\bcg\s+(\d+)\s*:\s*(.+)',
        re.IGNORECASE | re.DOTALL
    )
    match = cg_pattern.search(body)
    if match:
        max_tokens = int(match.group(1)) * 3
        question = match.group(2).strip()
        question = ' '.join(question.split())
        
        print("✅ CLAUDE GÉNÉRIQUE détecté (cg)")
        print(f"   Max tokens: {max_tokens}")
        print(f"   Question: {question[:100]}...")
        
        return {
            'type': 'claude_generic',
            'mode': 'generic',
            'max_tokens': max_tokens,
            'question': question
        }
    
    # PATTERN 2: Mistral générique "mg 150: question"
    mg_pattern = re.compile(
        r'\bmg\s+(\d+)\s*:\s*(.+)',
        re.IGNORECASE | re.DOTALL
    )
    match = mg_pattern.search(body)
    if match:
        max_tokens = int(match.group(1)) * 3
        question = match.group(2).strip()
        question = ' '.join(question.split())
        
        print("✅ MISTRAL GÉNÉRIQUE détecté (mg)")
        print(f"   Max tokens: {max_tokens}")
        print(f"   Question: {question[:100]}...")
        
        return {
            'type': 'mistral_generic',
            'mode': 'generic',
            'max_tokens': max_tokens,
            'question': question
        }
    
    # ========================================
    # PATTERNS MARITIMES
    # ========================================
    
    # PATTERN 3: Claude maritime court "c 150: question"
    c_pattern = re.compile(
        r'\bc\s+(\d+)\s*:\s*(.+)',
        re.IGNORECASE | re.DOTALL
    )
    match = c_pattern.search(body)
    if match:
        max_tokens = int(match.group(1)) * 3
        question = match.group(2).strip()
        question = ' '.join(question.split())
        
        print("✅ CLAUDE MARITIME détecté (c)")
        print(f"   Max tokens: {max_tokens}")
        print(f"   Question: {question[:100]}...")
        
        return {
            'type': 'claude_maritime',
            'mode': 'maritime',
            'max_tokens': max_tokens,
            'question': question
        }
    
    # PATTERN 4: Mistral maritime court "m 150: question"
    m_pattern = re.compile(
        r'\bm\s+(\d+)\s*:\s*(.+)',
        re.IGNORECASE | re.DOTALL
    )
    match = m_pattern.search(body)
    if match:
        max_tokens = int(match.group(1)) * 3
        question = match.group(2).strip()
        question = ' '.join(question.split())
        
        print("✅ MISTRAL MARITIME détecté (m)")
        print(f"   Max tokens: {max_tokens}")
        print(f"   Question: {question[:100]}...")
        
        return {
            'type': 'mistral_maritime',
            'mode': 'maritime',
            'max_tokens': max_tokens,
            'question': question
        }
    
    # PATTERN 5: Weather expert "w 150: question"
    w_pattern = re.compile(
        r'\bw\s+(\d+)\s*:\s*(.+)',
        re.IGNORECASE | re.DOTALL
    )
    match = w_pattern.search(body)
    if match:
        max_tokens = int(match.group(1)) * 3
        question = match.group(2).strip()
        question = ' '.join(question.split())
        
        print("✅ WEATHER EXPERT détecté (w)")
        print(f"   Max tokens: {max_tokens}")
        print(f"   Question: {question[:100]}...")
        
        return {
            'type': 'weather',
            'mode': 'weather',
            'max_tokens': max_tokens,
            'question': question
        }
    
    # PATTERN 6: Claude maritime long "claude 150: question" (compatibilité)
    claude_long = re.compile(
        r'\b(claude|gpt)\s+(\d+)\s*:\s*(.+)',
        re.IGNORECASE | re.DOTALL
    )
    match = claude_long.search(body)
    if match:
        max_tokens = int(match.group(2)) * 3
        question = match.group(3).strip()
        question = ' '.join(question.split())
        
        print("✅ CLAUDE MARITIME détecté (claude)")
        print(f"   Max tokens: {max_tokens}")
        print(f"   Question: {question[:100]}...")
        
        return {
            'type': 'claude_maritime',
            'mode': 'maritime',
            'max_tokens': max_tokens,
            'question': question
        }
    
    # PATTERN 7: Mistral maritime long "mistral 150: question" (compatibilité)
    mistral_long = re.compile(
        r'\bmistral\s+(\d+)\s*:\s*(.+)',
        re.IGNORECASE | re.DOTALL
    )
    match = mistral_long.search(body)
    if match:
        max_tokens = int(match.group(1)) * 3
        question = match.group(2).strip()
        question = ' '.join(question.split())
        
        print("✅ MISTRAL MARITIME détecté (mistral)")
        print(f"   Max tokens: {max_tokens}")
        print(f"   Question: {question[:100]}...")
        
        return {
            'type': 'mistral_maritime',
            'mode': 'maritime',
            'max_tokens': max_tokens,
            'question': question
        }
    
    # ========================================
    # PATTERNS SANS QUESTION (messages d'aide)
    # ========================================
    
    # Sans question = message d'aide
    for pattern, ai_type in [
        (r'\bc\s+(\d+)\s*$', 'claude_maritime'),
        (r'\bm\s+(\d+)\s*$', 'mistral_maritime'),
        (r'\bcg\s+(\d+)\s*$', 'claude_generic'),
        (r'\bmg\s+(\d+)\s*$', 'mistral_generic'),
        (r'\bw\s+(\d+)\s*$', 'weather'),
    ]:
        match = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
        if match:
            print(f"✅ {ai_type.upper()} SANS QUESTION (message d'aide)")
            return {
                'type': ai_type,
                'mode': 'help',
                'question': ""
            }
    
    # ========================================
    # PATTERN GRIB
    # ========================================
    
    grib_pattern = re.compile(r'(ecmwf|gfs|icon):[^\s\n]+', re.IGNORECASE)
    match = grib_pattern.search(body)
    
    if not match:
        body_single = body.replace('\n', ' ').replace('\r', ' ')
        match = grib_pattern.search(body_single)
    
    if match:
        grib_request = match.group(0)
        print("✅ GRIB détecté")
        print(f"   Request: {grib_request}")
        
        return {
            'type': 'grib',
            'request': grib_request
        }
    
    print("❌ Aucun pattern reconnu")
    print(f"{'='*70}")
    return None


def process_claude_maritime_wrapper(req):
    """Traite requête Claude MARITIME"""
    print(f"\n{'='*70}")
    print("⚓ CLAUDE MARITIME")
    print(f"{'='*70}")
    
    if req['question']:
        print(f"Question: {req['question'][:100]}...")
        
        try:
            response = handle_claude_maritime_assistant(req['question'])
            messages = split_long_response(response, max_length=160)
            
            print(f"✅ {len(messages)} message(s)")
            print(f"\n📤 Envoi...")
            if send_to_inreach(req['reply_url'], messages):
                print(f"✅✅✅ SUCCÈS")
            else:
                print(f"❌ ÉCHEC")
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
    else:
        send_help_message(req['reply_url'], "Claude maritime: c 150: question")


def process_claude_generic_wrapper(req):
    """Traite requête Claude GÉNÉRIQUE"""
    print(f"\n{'='*70}")
    print("🤖 CLAUDE GÉNÉRIQUE")
    print(f"{'='*70}")
    
    if req['question']:
        print(f"Question: {req['question'][:100]}...")
        
        try:
            response = handle_claude_request(req['question'], req['max_tokens'])
            messages = split_long_response(response, max_length=160)
            
            print(f"✅ {len(messages)} message(s)")
            print(f"\n📤 Envoi...")
            if send_to_inreach(req['reply_url'], messages):
                print(f"✅✅✅ SUCCÈS")
            else:
                print(f"❌ ÉCHEC")
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
    else:
        send_help_message(req['reply_url'], "Claude générique: cg 150: question")


def process_mistral_maritime_wrapper(req):
    """Traite requête Mistral MARITIME"""
    print(f"\n{'='*70}")
    print("⚓ MISTRAL MARITIME")
    print(f"{'='*70}")
    
    if req['question']:
        print(f"Question: {req['question'][:100]}...")
        
        try:
            response = handle_mistral_maritime_assistant(req['question'])
            messages = split_long_response(response, max_length=160)
            
            print(f"✅ {len(messages)} message(s)")
            print(f"\n📤 Envoi...")
            if send_to_inreach(req['reply_url'], messages):
                print(f"✅✅✅ SUCCÈS")
            else:
                print(f"❌ ÉCHEC")
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
    else:
        send_help_message(req['reply_url'], "Mistral maritime: m 150: question")


def process_mistral_generic_wrapper(req):
    """Traite requête Mistral GÉNÉRIQUE"""
    print(f"\n{'='*70}")
    print("🧠 MISTRAL GÉNÉRIQUE")
    print(f"{'='*70}")
    
    if req['question']:
        print(f"Question: {req['question'][:100]}...")
        
        try:
            response = handle_mistral_request(req['question'], req['max_tokens'])
            messages = split_long_response(response, max_length=160)
            
            print(f"✅ {len(messages)} message(s)")
            print(f"\n📤 Envoi...")
            if send_to_inreach(req['reply_url'], messages):
                print(f"✅✅✅ SUCCÈS")
            else:
                print(f"❌ ÉCHEC")
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
    else:
        send_help_message(req['reply_url'], "Mistral générique: mg 150: question")


def process_weather_wrapper(req):
    """Traite requête WEATHER EXPERT"""
    print(f"\n{'='*70}")
    print("🌊 WEATHER EXPERT")
    print(f"{'='*70}")
    
    if req['question']:
        print(f"Question: {req['question'][:100]}...")
        
        try:
            response = handle_mistral_weather_expert(req['question'])
            messages = split_long_response(response, max_length=160)
            
            print(f"✅ {len(messages)} message(s)")
            print(f"\n📤 Envoi...")
            if send_to_inreach(req['reply_url'], messages):
                print(f"✅✅✅ SUCCÈS")
            else:
                print(f"❌ ÉCHEC")
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
    else:
        send_help_message(req['reply_url'], "Weather expert: w 150: question")


def send_help_message(url, example):
    """Envoie message d'aide"""
    help_msg = f"Format: {example}"
    send_to_inreach(url, [help_msg])


def split_long_response(response, max_length=160):
    """Découpe réponse en messages"""
    if len(response) <= max_length:
        return [response]
    
    messages = []
    words = response.split()
    current_msg = ""
    
    for word in words:
        test_msg = current_msg + " " + word if current_msg else word
        
        if len(test_msg) <= max_length:
            current_msg = test_msg
        else:
            if current_msg:
                messages.append(current_msg)
            current_msg = word
    
    if current_msg:
        messages.append(current_msg)
    
    return messages
