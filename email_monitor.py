# email_monitor.py - v3.1.0
"""
Surveillance Gmail pour requêtes GRIB et AI (Claude/Mistral)
Architecture modulaire avec détection patterns flexibles
"""

import imaplib
import email
import re
from datetime import datetime
from config import GARMIN_USERNAME, GARMIN_PASSWORD
from grib_handler import process_grib_request
from claude_handler import handle_claude_maritime_assistant, handle_claude_request
from mistral_handler import handle_mistral_maritime_assistant, handle_mistral_request


def check_gmail():
    """
    Vérifie Gmail pour nouvelles requêtes inReach
    Détecte et route: GRIB, Claude, Mistral
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
                        if request_info['type'] in ['claude', 'mistral']:
                            print(f"   Provider: {request_info['provider']}")
                            print(f"   Max words: {request_info['max_words']}")
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
            
            if req['type'] == 'claude':
                process_claude_request_wrapper(req)
            
            elif req['type'] == 'mistral':
                process_mistral_request_wrapper(req)
            
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
    Détecte le type de requête: GRIB, Claude, Mistral
    
    Returns:
        dict avec type et paramètres, ou None
    """
    print(f"\n{'='*70}")
    print("🔍 DÉTECTION TYPE DE REQUÊTE")
    print(f"{'='*70}")
    
    # PATTERN 1: Claude avec question "claude 150: question"
    claude_with_q = re.compile(
        r'(claude|gpt)\s+(\d+)\s*:\s*(.+)',
        re.IGNORECASE | re.DOTALL
    )
    match = claude_with_q.search(body)
    if match:
        max_words = int(match.group(2))
        question = match.group(3).strip()
        question = ' '.join(question.split())
        
        print("✅ CLAUDE AVEC QUESTION détecté")
        print(f"   Max words: {max_words}")
        print(f"   Question: {question[:100]}...")
        
        return {
            'type': 'claude',
            'provider': 'claude',
            'max_words': max_words,
            'question': question
        }
    
    # PATTERN 2: Claude sans question "claude 150"
    claude_without_q = re.compile(
        r'(claude|gpt)\s+(\d+)\s*$',
        re.IGNORECASE | re.MULTILINE
    )
    match = claude_without_q.search(body)
    if match:
        max_words = int(match.group(2))
        
        print("✅ CLAUDE SANS QUESTION détecté (message d'aide)")
        print(f"   Max words: {max_words}")
        
        return {
            'type': 'claude',
            'provider': 'claude',
            'max_words': max_words,
            'question': ""  # Vide = message d'aide
        }
    
    # PATTERN 3: Juste "claude" ou "gpt"
    claude_only = re.compile(r'^(claude|gpt)\s*$', re.IGNORECASE | re.MULTILINE)
    match = claude_only.search(body)
    if match:
        print("✅ CLAUDE SEUL détecté (message d'aide, 50 mots par défaut)")
        
        return {
            'type': 'claude',
            'provider': 'claude',
            'max_words': 50,
            'question': ""
        }
    
    # PATTERN 4: Mistral avec question "mistral 150: question"
    mistral_with_q = re.compile(
        r'mistral\s+(\d+)\s*:\s*(.+)',
        re.IGNORECASE | re.DOTALL
    )
    match = mistral_with_q.search(body)
    if match:
        max_words = int(match.group(1))
        question = match.group(2).strip()
        question = ' '.join(question.split())
        
        print("✅ MISTRAL AVEC QUESTION détecté")
        print(f"   Max words: {max_words}")
        print(f"   Question: {question[:100]}...")
        
        return {
            'type': 'mistral',
            'provider': 'mistral',
            'max_words': max_words,
            'question': question
        }
    
    # PATTERN 5: Mistral sans question "mistral 150"
    mistral_without_q = re.compile(
        r'mistral\s+(\d+)\s*$',
        re.IGNORECASE | re.MULTILINE
    )
    match = mistral_without_q.search(body)
    if match:
        max_words = int(match.group(1))
        
        print("✅ MISTRAL SANS QUESTION détecté (message d'aide)")
        print(f"   Max words: {max_words}")
        
        return {
            'type': 'mistral',
            'provider': 'mistral',
            'max_words': max_words,
            'question': ""
        }
    
    # PATTERN 6: Juste "mistral"
    mistral_only = re.compile(r'^mistral\s*$', re.IGNORECASE | re.MULTILINE)
    match = mistral_only.search(body)
    if match:
        print("✅ MISTRAL SEUL détecté (message d'aide, 50 mots par défaut)")
        
        return {
            'type': 'mistral',
            'provider': 'mistral',
            'max_words': 50,
            'question': ""
        }
    
    # PATTERN 7: GRIB "ecmwf:..." ou "gfs:..." ou "icon:..."
    grib_pattern = re.compile(r'(ecmwf|gfs|icon):[^\s\n]+', re.IGNORECASE)
    match = grib_pattern.search(body)
    
    if not match:
        # Essayer sur une seule ligne
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


def process_claude_request_wrapper(req):
    """Traite une requête Claude et envoie les messages"""
    from inreach_sender import send_messages_to_inreach
    
    print(f"\n{'='*70}")
    print("🤖 TRAITEMENT CLAUDE")
    print(f"{'='*70}")
    
    if req['question'] and req['question'].strip():
        # Requête avec question
        print(f"Question: {req['question'][:100]}...")
        print(f"Max words: {req['max_words']}\n")
        
        # Appeler le handler (fonction à choisir selon ton implementation)
        try:
            response = handle_claude_maritime_assistant(req['question'])
            
            # Découper la réponse en messages inReach (max 160 chars)
            messages = split_long_response(response, max_length=160)
            
            print(f"✅ Réponse Claude: {len(messages)} message(s)")
            for i, msg in enumerate(messages, 1):
                print(f"   [{i}/{len(messages)}] {len(msg)} chars: '{msg[:50]}...'")
            
            # Envoyer
            print(f"\n📤 Envoi de {len(messages)} message(s)...")
            if send_messages_to_inreach(req['reply_url'], messages):
                print(f"✅✅✅ CLAUDE: {len(messages)} messages envoyés avec succès")
            else:
                print(f"❌ Échec envoi messages Claude")
        
        except Exception as e:
            print(f"❌ Erreur traitement Claude: {e}")
            import traceback
            traceback.print_exc()
    
    else:
        # Requête sans question = message d'aide
        print("📖 Envoi message d'aide Claude\n")
        
        help_msg = """Claude AI prêt!
Formats:
- claude 150: votre question
- claude 100: weather forecast
Envoyez question après ':'"""
        
        messages = [help_msg]
        
        print(f"📤 Envoi message d'aide...")
        if send_messages_to_inreach(req['reply_url'], messages):
            print(f"✅ Message d'aide Claude envoyé")
        else:
            print(f"❌ Échec envoi aide Claude")


def process_mistral_request_wrapper(req):
    """Traite une requête Mistral et envoie les messages"""
    from inreach_sender import send_messages_to_inreach
    
    print(f"\n{'='*70}")
    print("🧠 TRAITEMENT MISTRAL")
    print(f"{'='*70}")
    
    if req['question'] and req['question'].strip():
        # Requête avec question
        print(f"Question: {req['question'][:100]}...")
        print(f"Max words: {req['max_words']}\n")
        
        try:
            response = handle_mistral_maritime_assistant(req['question'])
            
            # Découper la réponse
            messages = split_long_response(response, max_length=160)
            
            print(f"✅ Réponse Mistral: {len(messages)} message(s)")
            for i, msg in enumerate(messages, 1):
                print(f"   [{i}/{len(messages)}] {len(msg)} chars: '{msg[:50]}...'")
            
            # Envoyer
            print(f"\n📤 Envoi de {len(messages)} message(s)...")
            if send_messages_to_inreach(req['reply_url'], messages):
                print(f"✅✅✅ MISTRAL: {len(messages)} messages envoyés avec succès")
            else:
                print(f"❌ Échec envoi messages Mistral")
        
        except Exception as e:
            print(f"❌ Erreur traitement Mistral: {e}")
            import traceback
            traceback.print_exc()
    
    else:
        # Requête sans question = message d'aide
        print("📖 Envoi message d'aide Mistral\n")
        
        help_msg = """Mistral AI prêt!
Formats:
- mistral 150: votre question
- mistral 100: météo demain
Envoyez question après ':'"""
        
        messages = [help_msg]
        
        print(f"📤 Envoi message d'aide...")
        if send_messages_to_inreach(req['reply_url'], messages):
            print(f"✅ Message d'aide Mistral envoyé")
        else:
            print(f"❌ Échec envoi aide Mistral")


def split_long_response(response, max_length=160):
    """
    Découpe une réponse longue en messages inReach
    
    Args:
        response: Texte à découper
        max_length: Taille max par message (défaut 160)
        
    Returns:
        Liste de messages
    """
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


# Point d'entrée pour tests
if __name__ == "__main__":
    print("Test email_monitor.py v3.1.0")
    print("="*70)
    
    # Test détection
    test_bodies = [
        "claude 150: que faire si vent 40kt?",
        "Claude 150",
        "mistral 100: distance Panama Marquises",
        "mistral 50",
        "ecmwf:0S,92W+150",
    ]
    
    for body in test_bodies:
        print(f"\nTest: '{body}'")
        result = detect_request_type(body)
        if result:
            print(f"✅ Détecté: {result}")
        else:
            print("❌ Non détecté")
