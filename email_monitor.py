# email_monitor.py - v1.1
"""Surveillance des emails Gmail pour détecter requêtes GRIB et chat"""

import imaplib
import email
from email.header import decode_header
import re
import time
from datetime import datetime
from config import GARMIN_USERNAME, GARMIN_PASSWORD
from grib_handler import process_grib_request
from claude_handler import process_claude_chat
from mistral_handler import process_mistral_chat


def check_gmail():
    """
    Vérifie Gmail pour nouvelles requêtes inReach
    Traite GRIB et conversations AI
    """
    print("\n")
    print("="*70)
    print(f"🔄 TRAITEMENT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    print()
    
    try:
        # Connexion IMAP
        print(f"✅ Identifiants Garmin: {GARMIN_USERNAME}")
        print(f"📧 Connexion IMAP: {GARMIN_USERNAME}")
        
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(GARMIN_USERNAME, GARMIN_PASSWORD)
        mail.select('inbox')
        
        print("✅ Connexion IMAP réussie")
        print()
        
        # Rechercher emails non lus de inReach
        print("🔍 Recherche emails inReach non lus...")
        status, messages = mail.search(None, '(UNSEEN FROM "inreach")')
        
        if status != 'OK':
            print("⚠️  Erreur recherche emails")
            mail.logout()
            return
        
        email_ids = messages[0].split()
        total_emails = len(email_ids)
        
        print(f"📬 {total_emails} email(s) inReach non lu(s) trouvé(s)")
        print()
        
        if total_emails == 0:
            print("✅ Aucun nouveau message inReach")
            mail.logout()
            return
        
        # Traiter chaque email
        requests_processed = 0
        
        for i, email_id in enumerate(email_ids, 1):
            print(f"\n{'='*70}")
            print(f"📧 EMAIL {i}/{total_emails}")
            print(f"{'='*70}\n")
            
            try:
                # Récupérer email
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                
                if status != 'OK':
                    print(f"   ⚠️  Erreur récupération email {i}")
                    continue
                
                # Parser email
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Extraire infos
                subject = ""
                if msg['Subject']:
                    decoded = decode_header(msg['Subject'])[0]
                    subject = decoded[0].decode() if isinstance(decoded[0], bytes) else decoded[0]
                
                from_addr = msg.get('From', '')
                
                print(f"   De: {from_addr}")
                print(f"   Sujet: {subject}")
                print()
                
                # Extraire corps du message
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode()
                                break
                            except:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode()
                    except:
                        body = msg.get_payload()
                
                print(f"   Corps: {body[:200]}...")
                print()
                
                # Extraire URL inReach
                inreach_url = None
                url_patterns = [
                    r'(https://[^\s]*inreach[^\s]*)',
                    r'(https://[^\s]*garmin\.com[^\s]*)'
                ]
                
                for pattern in url_patterns:
                    matches = re.findall(pattern, body)
                    if matches:
                        inreach_url = matches[0]
                        break
                
                if not inreach_url:
                    print("   ⚠️  Aucune URL inReach trouvée, skip")
                    continue
                
                print(f"   🔗 URL inReach: {inreach_url}")
                print()
                
                # Détecter type de requête
                request_type = None
                request_content = None
                
                # 1. Chercher requête GRIB
                grib_pattern = r'(gfs|ecmwf|arpege|icon)[:\s]*([\d\w\s,\-\|\.N|S|E|W]+)'
                grib_match = re.search(grib_pattern, body, re.IGNORECASE)
                
                if grib_match:
                    request_type = 'grib'
                    request_content = grib_match.group(0).strip()
                    print(f"   🌊 REQUÊTE GRIB DÉTECTÉE")
                    print(f"   📝 Contenu: {request_content}")
                
                # 2. Chercher conversation AI
                elif any(keyword in body.lower() for keyword in ['claude', 'ai', 'help', 'weather', 'route']):
                    request_type = 'chat'
                    request_content = body.strip()
                    print(f"   💬 REQUÊTE CHAT DÉTECTÉE")
                    print(f"   📝 Contenu: {request_content[:100]}...")
                
                else:
                    print("   ⚠️  Type de requête non reconnu")
                    continue
                
                print()
                print(f"   ✅ Requête {request_type.upper()} prête au traitement")
                print()
                
                # TRAITER LA REQUÊTE
                if request_type == 'grib':
                    print(f"\n{'='*70}")
                    print(f"🌊 TRAITEMENT REQUÊTE GRIB")
                    print(f"{'='*70}\n")
                    
                    success = process_grib_request(request_content, inreach_url)
                    
                    if success:
                        print(f"\n✅✅✅ GRIB TRAITÉ AVEC SUCCÈS ✅✅✅\n")
                        requests_processed += 1
                    else:
                        print(f"\n❌ ÉCHEC TRAITEMENT GRIB\n")
                
                elif request_type == 'chat':
                    print(f"\n{'='*70}")
                    print(f"💬 TRAITEMENT REQUÊTE CHAT")
                    print(f"{'='*70}\n")
                    
                    # Tenter Claude d'abord, puis Mistral en fallback
                    success = process_claude_chat(request_content, inreach_url)
                    
                    if not success:
                        print("   ⚠️  Claude échec, tentative Mistral...")
                        success = process_mistral_chat(request_content, inreach_url)
                    
                    if success:
                        print(f"\n✅✅✅ CHAT TRAITÉ AVEC SUCCÈS ✅✅✅\n")
                        requests_processed += 1
                    else:
                        print(f"\n❌ ÉCHEC TRAITEMENT CHAT\n")
                
                # Marquer comme lu
                mail.store(email_id, '+FLAGS', '\\Seen')
                print(f"   ✉️  Email marqué comme lu\n")
                
            except Exception as e:
                print(f"   ❌ Erreur traitement email {i}: {e}\n")
                continue
        
        # Déconnexion
        mail.logout()
        print("\n" + "="*70)
        print(f"✅ VÉRIFICATION TERMINÉE - {requests_processed} requête(s) traitée(s)")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"❌ Erreur check_gmail: {e}\n")
