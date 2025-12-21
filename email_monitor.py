# email_monitor.py - v3.0.0
"""Surveillance des emails Gmail pour détecter requêtes GRIB"""

import imaplib
import email
from email.header import decode_header
from datetime import datetime
from config import GARMIN_USERNAME, GARMIN_PASSWORD, IMAP_HOST, IMAP_PORT
from utils import extract_grib_request, extract_inreach_url
from grib_handler import process_grib_request


def check_gmail():
    """
    Vérifie Gmail pour nouvelles requêtes inReach
    Traite les requêtes GRIB
    """
    print("\n")
    print("="*70)
    print(f"🔄 VÉRIFICATION GMAIL - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    print()
    
    try:
        # Connexion IMAP
        print(f"📧 Connexion IMAP: {GARMIN_USERNAME}")
        
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
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
                
                print(f"   Corps (extrait):")
                print(f"   {body[:200]}...")
                print()
                
                # Extraire URL inReach
                inreach_url = extract_inreach_url(body)
                
                if not inreach_url:
                    print("   ⚠️  Aucune URL inReach trouvée, skip")
                    continue
                
                print(f"   🔗 URL inReach: {inreach_url}")
                print()
                
                # Extraire requête GRIB
                grib_request = extract_grib_request(body)
                
                if grib_request:
                    print(f"   🌊 REQUÊTE GRIB DÉTECTÉE")
                    print(f"   📝 Requête: {grib_request}")
                    print()
                    
                    # TRAITER LA REQUÊTE GRIB
                    success = process_grib_request(grib_request, inreach_url)
                    
                    if success:
                        print(f"\n✅✅✅ GRIB TRAITÉ AVEC SUCCÈS ✅✅✅\n")
                        requests_processed += 1
                    else:
                        print(f"\n❌ ÉCHEC TRAITEMENT GRIB\n")
                else:
                    print("   ⚠️  Pas de requête GRIB détectée")
                
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
        import traceback
        traceback.print_exc()
