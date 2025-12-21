# grib_handler.py - v3.0.1
"""Module de traitement des requêtes GRIB - LOGS ULTRA DÉTAILLÉS"""

import time
import imaplib
import email
import sys
from config import (GARMIN_USERNAME, GARMIN_PASSWORD, SENDGRID_API_KEY,
                    SAILDOCS_EMAIL, IMAP_HOST, IMAP_PORT, SAILDOCS_TIMEOUT)
from utils import encode_and_split_grib
from inreach_sender import send_to_inreach

# Forcer stdout non-bufferisé
sys.stdout.flush()


def send_to_saildocs(grib_request):
    """
    Envoie requête GRIB à Saildocs par email
    IMPORTANT: Envoie SEULEMENT la requête pure, sans signature ni URL
    """
    print(f"\n{'='*70}", flush=True)
    print(f"📤 ÉTAPE 1/3: ENVOI À SAILDOCS", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"Requête: {grib_request}", flush=True)
    
    if not SENDGRID_API_KEY:
        print("❌ SendGrid requis pour Saildocs", flush=True)
        return False
    
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        
        # CRITIQUE: Envoyer SEULEMENT "send <requête>"
        email_body = f"send {grib_request}"
        
        print(f"📧 Création email SendGrid...", flush=True)
        print(f"   De: {GARMIN_USERNAME}", flush=True)
        print(f"   À: {SAILDOCS_EMAIL}", flush=True)
        print(f"   Sujet: send", flush=True)
        print(f"   Corps: {email_body}", flush=True)
        
        message = Mail(
            from_email=GARMIN_USERNAME,
            to_emails=SAILDOCS_EMAIL,
            subject='send',
            plain_text_content=email_body
        )
        
        print(f"📤 Envoi email SendGrid...", flush=True)
        response = sg.send(message)
        
        print(f"📬 Réponse SendGrid: Status {response.status_code}", flush=True)
        
        if response.status_code in [200, 201, 202]:
            print(f"✅ Demande GRIB envoyée à Saildocs avec succès", flush=True)
            return True
        else:
            print(f"❌ Erreur SendGrid: Status {response.status_code}", flush=True)
            return False
        
    except Exception as e:
        print(f"❌ Erreur envoi Saildocs: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False


def wait_for_saildocs_response(timeout=SAILDOCS_TIMEOUT):
    """
    Attend réponse de Saildocs avec fichier GRIB
    LOGS ULTRA DÉTAILLÉS
    """
    print(f"\n{'='*70}", flush=True)
    print(f"⏳ ÉTAPE 2/3: ATTENTE RÉPONSE SAILDOCS", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"Timeout maximum: {timeout}s ({timeout//60} minutes)", flush=True)
    print(f"Vérification toutes les 10 secondes", flush=True)
    print(f"{'='*70}\n", flush=True)
    
    start_time = time.time()
    check_count = 0
    
    while time.time() - start_time < timeout:
        check_count += 1
        elapsed = int(time.time() - start_time)
        
        print(f"🔍 Vérification #{check_count} - {elapsed}s écoulées", flush=True)
        
        try:
            print(f"   📧 Connexion IMAP...", flush=True)
            mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            mail.login(GARMIN_USERNAME, GARMIN_PASSWORD)
            mail.select('inbox')
            print(f"   ✅ Connexion IMAP OK", flush=True)
            
            # Chercher emails non lus de Saildocs
            print(f"   🔎 Recherche emails de query@saildocs.com...", flush=True)
            status, messages = mail.search(None, '(UNSEEN FROM "query@saildocs.com")')
            
            if status == 'OK':
                print(f"   📬 Recherche OK", flush=True)
                
                if messages[0]:
                    email_ids = messages[0].split()
                    print(f"   ✅ {len(email_ids)} email(s) de Saildocs trouvé(s)!", flush=True)
                    
                    for email_id in email_ids:
                        print(f"\n   📩 Analyse email ID: {email_id.decode()}", flush=True)
                        
                        status, msg_data = mail.fetch(email_id, '(RFC822)')
                        raw_email = msg_data[0][1]
                        msg = email.message_from_bytes(raw_email)
                        
                        # Afficher sujet
                        subject = msg.get('Subject', 'No subject')
                        print(f"      Sujet: {subject}", flush=True)
                        
                        print(f"      📎 Recherche pièces jointes...", flush=True)
                        
                        attachment_count = 0
                        
                        # Chercher pièce jointe GRIB
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            filename = part.get_filename()
                            
                            if filename:
                                attachment_count += 1
                                print(f"         Fichier #{attachment_count}: {filename} ({content_type})", flush=True)
                            
                            # GRIB = application/octet-stream
                            if content_type == 'application/octet-stream':
                                grib_data = part.get_payload(decode=True)
                                
                                if grib_data and len(grib_data) > 0:
                                    print(f"\n{'='*70}", flush=True)
                                    print(f"✅ GRIB REÇU!", flush=True)
                                    print(f"{'='*70}", flush=True)
                                    print(f"Taille: {len(grib_data)} octets", flush=True)
                                    print(f"Temps d'attente: {elapsed}s", flush=True)
                                    print(f"{'='*70}\n", flush=True)
                                    
                                    # Marquer comme lu
                                    mail.store(email_id, '+FLAGS', '\\Seen')
                                    mail.logout()
                                    
                                    return grib_data
                                else:
                                    print(f"         ⚠️  Pièce jointe vide", flush=True)
                        
                        if attachment_count == 0:
                            print(f"      ⚠️  Aucune pièce jointe trouvée", flush=True)
                else:
                    print(f"   📭 Aucun email de Saildocs pour l'instant", flush=True)
            else:
                print(f"   ⚠️  Erreur recherche: {status}", flush=True)
            
            mail.logout()
            print(f"   🔌 Déconnexion IMAP\n", flush=True)
            
        except Exception as e:
            print(f"   ❌ Erreur vérification: {e}", flush=True)
            import traceback
            traceback.print_exc()
        
        # Attendre 10s avant prochaine vérification
        if elapsed < timeout - 10:
            print(f"   ⏸️  Attente 10s avant prochaine vérification...\n", flush=True)
            time.sleep(10)
        else:
            break
    
    print(f"\n{'='*70}", flush=True)
    print(f"❌ TIMEOUT - Aucune réponse de Saildocs après {timeout}s", flush=True)
    print(f"{'='*70}\n", flush=True)
    return None


def process_grib_request(grib_request, inreach_url, reply_email=None):
    """
    Traite une requête GRIB complète de bout en bout
    LOGS ULTRA DÉTAILLÉS
    """
    print(f"\n{'='*70}", flush=True)
    print(f"🌊 TRAITEMENT GRIB COMPLET", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"Requête: {grib_request}", flush=True)
    print(f"URL inReach: {inreach_url}", flush=True)
    if reply_email:
        print(f"Email secours: {reply_email}", flush=True)
    print(f"{'='*70}\n", flush=True)
    
    try:
        # Étape 1: Envoyer à Saildocs
        if not send_to_saildocs(grib_request):
            print("❌ ÉCHEC ÉTAPE 1: Envoi Saildocs", flush=True)
            return False
        
        # Étape 2: Attendre réponse
        grib_data = wait_for_saildocs_response()
        
        if not grib_data:
            print("❌ ÉCHEC ÉTAPE 2: Aucune réponse Saildocs", flush=True)
            return False
        
        # Étape 3: Encoder et envoyer
        print(f"\n{'='*70}", flush=True)
        print(f"🔧 ÉTAPE 3/3: ENCODAGE ET ENVOI", flush=True)
        print(f"{'='*70}\n", flush=True)
        
        messages = encode_and_split_grib(grib_data)
        
        # Envoyer vers inReach
        success = send_to_inreach(inreach_url, messages, reply_email)
        
        if success:
            print(f"\n{'='*70}", flush=True)
            print(f"✅✅✅ SUCCÈS COMPLET ✅✅✅", flush=True)
            print(f"{'='*70}", flush=True)
            print(f"GRIB envoyé: {len(messages)} messages", flush=True)
            print(f"{'='*70}\n", flush=True)
            return True
        else:
            print(f"\n❌ ÉCHEC ÉTAPE 3: Envoi inReach\n", flush=True)
            return False
            
    except Exception as e:
        print(f"❌ ERREUR CRITIQUE: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False
