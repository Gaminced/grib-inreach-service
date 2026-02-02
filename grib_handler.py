# grib_handler.py - v3.3.0
"""
Module de traitement des requêtes GRIB avec Resend
v3.3.0: Migration SendGrid → Resend (100 emails/jour gratuit) et naming 
"""

import time
import imaplib
import email
import sys
from config import (GARMIN_USERNAME, GARMIN_PASSWORD, RESEND_API_KEY,
                    SAILDOCS_EMAIL, SAILDOCS_RESPONSE_EMAIL, IMAP_HOST, IMAP_PORT, SAILDOCS_TIMEOUT)
from utils import encode_and_split_grib
from inreach_sender import send_to_inreach
from inreach-cleaner-final import extract_grib_request

# Forcer stdout non-bufferisé
sys.stdout.flush()


def send_to_saildocs(grib_request):
    """
    Envoie requête GRIB à Saildocs par email via Resend
    
    RESEND vs SENDGRID:
    - 100 emails/jour GRATUIT (vs SendGrid payant)
    - API similaire, migration facile
    - Excellente délivrabilité
    
    Args:
        grib_request: Requête GRIB formatée (ex: "ecmwf:40N,50N,15W,5W|0.5,0.5|0,24..120|WIND,WAVES")
        
    Returns:
        bool: True si envoi réussi, False sinon
    """
    print(f"\n{'='*70}", flush=True)
    print(f"📤 ÉTAPE 1/3: ENVOI À SAILDOCS", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"Requête: {grib_request}", flush=True)
    
    if not RESEND_API_KEY:
        print("❌ RESEND_API_KEY requis pour Saildocs", flush=True)
        print("⚠️  Configurez RESEND_API_KEY dans variables d'environnement", flush=True)
        return False
    
    try:
        # Import Resend
        import resend
        
        # Configuration API Key
        resend.api_key = RESEND_API_KEY
        
        # Corps de l'email
        email_body = f"send {grib_request}"
        
        print(f"📧 Création email Resend...", flush=True)
        print(f"   De: onboarding@resend.dev", flush=True)  # Domaine gratuit Resend
        print(f"   Reply-To: {GARMIN_USERNAME}", flush=True)
        print(f"   À: {SAILDOCS_EMAIL}", flush=True)
        print(f"   Corps: {email_body}", flush=True)
        
        # Envoi email avec Resend
        params = {
            "from": "Garmin inReach <onboarding@resend.dev>",  # Domaine Resend gratuit
            "to": [SAILDOCS_EMAIL],
            "subject": "send",
            "text": email_body,
            "reply_to": GARMIN_USERNAME  # Réponse vers Gmail
        }
        
        print(f"📤 Envoi email...", flush=True)
        response = resend.Emails.send(params)
        
        print(f"📬 Resend Response ID: {response.get('id', 'N/A')}", flush=True)
        
        if response and response.get('id'):
            print(f"✅ Demande envoyée avec succès", flush=True)
            print(f"✅ Réponse attendue de: {SAILDOCS_RESPONSE_EMAIL}", flush=True)
            print(f"📊 Email ID: {response['id']}", flush=True)
            return True
        else:
            print(f"❌ Erreur: Pas d'ID de réponse", flush=True)
            print(f"Response: {response}", flush=True)
            return False
        
    except ImportError:
        print(f"❌ Erreur: Module 'resend' non installé", flush=True)
        print(f"💡 Solution: pip install resend", flush=True)
        return False
        
    except Exception as e:
        print(f"❌ Erreur Resend: {e}", flush=True)
        import traceback
        traceback.print_exc()
        
        # Suggestions de debug
        print(f"\n🔍 DEBUG:", flush=True)
        print(f"   - Vérifiez RESEND_API_KEY (format: re_xxxxx)", flush=True)
        print(f"   - API Key valide sur https://resend.com/api-keys", flush=True)
        print(f"   - Quota: 100 emails/jour (gratuit)", flush=True)
        
        return False


def wait_for_saildocs_response(timeout=SAILDOCS_TIMEOUT):
    """
    Attend réponse de Saildocs avec fichier GRIB
    Cherche emails de query-reply@saildocs.com
    
    Args:
        timeout: Temps max d'attente en secondes (défaut: 300s = 5min)
        
    Returns:
        bytes: Données GRIB si trouvé, None sinon
    """
    print(f"\n{'='*70}", flush=True)
    print(f"⏳ ÉTAPE 2/3: ATTENTE RÉPONSE SAILDOCS", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"Email attendu: {SAILDOCS_RESPONSE_EMAIL}", flush=True)
    print(f"Timeout: {timeout}s ({timeout//60} min)", flush=True)
    print(f"{'='*70}\n", flush=True)
    
    start_time = time.time()
    check_count = 0
    
    while time.time() - start_time < timeout:
        check_count += 1
        elapsed = int(time.time() - start_time)
        
        print(f"🔍 Vérification #{check_count} - {elapsed}s", flush=True)
        
        try:
            print(f"   📧 Connexion IMAP...", flush=True)
            mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            mail.login(GARMIN_USERNAME, GARMIN_PASSWORD)
            mail.select('inbox')
            print(f"   ✅ IMAP OK", flush=True)
            
            # Recherche emails de Saildocs (query-reply@saildocs.com)
            print(f"   🔎 Recherche: {SAILDOCS_RESPONSE_EMAIL}...", flush=True)
            status, messages = mail.search(None, f'(UNSEEN FROM "{SAILDOCS_RESPONSE_EMAIL}")')
            
            if status == 'OK':
                if messages[0]:
                    email_ids = messages[0].split()
                    print(f"   ✅ {len(email_ids)} email(s) trouvé(s)!", flush=True)
                    
                    for email_id in email_ids:
                        print(f"\n   📩 Email ID: {email_id.decode()}", flush=True)
                        
                        status, msg_data = mail.fetch(email_id, '(RFC822)')
                        raw_email = msg_data[0][1]
                        msg = email.message_from_bytes(raw_email)
                        
                        subject = msg.get('Subject', 'No subject')
                        print(f"      Sujet: {subject}", flush=True)
                        print(f"      📎 Recherche pièces jointes...", flush=True)
                        
                        # Parcourir les parties du message
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            filename = part.get_filename()
                            
                            if filename:
                                print(f"         📄 {filename} ({content_type})", flush=True)
                            
                            # Fichier GRIB = application/octet-stream
                            if content_type == 'application/octet-stream':
                                grib_data = part.get_payload(decode=True)
                                
                                if grib_data and len(grib_data) > 0:
                                    print(f"\n{'='*70}", flush=True)
                                    print(f"✅ GRIB REÇU!", flush=True)
                                    print(f"{'='*70}", flush=True)
                                    print(f"Taille: {len(grib_data)} octets", flush=True)
                                    print(f"Attente: {elapsed}s", flush=True)
                                    print(f"{'='*70}\n", flush=True)
                                    
                                    # Marquer comme lu
                                    mail.store(email_id, '+FLAGS', '\\Seen')
                                    mail.logout()
                                    return grib_data
                else:
                    print(f"   📭 Aucun email pour l'instant", flush=True)
            
            mail.logout()
            print(f"   🔌 Déconnexion\n", flush=True)
            
        except Exception as e:
            print(f"   ❌ Erreur IMAP: {e}", flush=True)
        
        # Attente avant prochaine vérification
        if elapsed < timeout - 10:
            print(f"   ⏸️  Attente 10s...\n", flush=True)
            time.sleep(10)
        else:
            break
    
    print(f"\n❌ TIMEOUT après {timeout}s", flush=True)
    print(f"💡 Saildocs peut prendre 2-10 minutes pour répondre", flush=True)
    return None


def process_grib_request(raw_email_body, inreach_url, mail=None):
    """
    Traite requête GRIB complète avec NETTOYAGE EMAIL INREACH
    
    Pipeline:
    1. Nettoie email inReach (retire métadonnées)
    2. Envoie requête à Saildocs via Resend
    3. Attend réponse GRIB de Saildocs
    4. Encode GRIB en base64
    5. Découpe en messages 160 chars
    6. Envoie à inReach via Playwright
    
    Args:
        raw_email_body: Corps brut de l'email InReach (avec métadonnées)
        inreach_url: URL de réponse InReach
        mail: Connexion IMAP optionnelle (non utilisée en v3.2.0)
        
    Returns:
        bool: True si succès complet, False sinon
    """
    print(f"\n{'='*70}", flush=True)
    print(f"🌊 TRAITEMENT GRIB v3.2.0 (Resend)", flush=True)
    print(f"{'='*70}", flush=True)
    
    # ÉTAPE 0: Nettoyage email InReach
    print(f"🧹 Nettoyage email InReach...", flush=True)
    grib_request = extract_grib_request(raw_email_body)
    
    if not grib_request:
        print(f"❌ Impossible d'extraire la requête GRIB", flush=True)
        print(f"💡 Format attendu: ecmwf:lat1,lat2,lon1,lon2|...", flush=True)
        return False
    
    print(f"✅ Requête extraite: {grib_request}", flush=True)
    print(f"📍 URL inReach: {inreach_url}", flush=True)
    print(f"{'='*70}\n", flush=True)
    
    try:
        # ÉTAPE 1: Envoi à Saildocs via Resend
        if not send_to_saildocs(grib_request):
            print(f"❌ Échec envoi Saildocs", flush=True)
            return False
        
        # ÉTAPE 2: Attente réponse Saildocs
        grib_data = wait_for_saildocs_response()
        if not grib_data:
            print(f"❌ Pas de réponse Saildocs", flush=True)
            return False
        
        # ÉTAPE 3: Encodage et envoi inReach
        print(f"\n{'='*70}", flush=True)
        print(f"🔧 ÉTAPE 3/3: ENCODAGE ET ENVOI", flush=True)
        print(f"{'='*70}\n", flush=True)
        
        messages = encode_and_split_grib(grib_data)
        print(f"📤 Envoi {len(messages)} messages à inReach...", flush=True)
        
        success = send_to_inreach(inreach_url, messages)
        
        if success:
            print(f"\n{'='*70}", flush=True)
            print(f"✅✅✅ SUCCÈS COMPLET ✅✅✅", flush=True)
            print(f"{'='*70}", flush=True)
            print(f"Messages envoyés: {len(messages)}", flush=True)
            print(f"Taille GRIB: {len(grib_data)} octets", flush=True)
            print(f"{'='*70}\n", flush=True)
            return True
        else:
            print(f"\n❌ Échec envoi inReach", flush=True)
            return False
            
    except Exception as e:
        print(f"\n{'='*70}", flush=True)
        print(f"❌ ERREUR CRITIQUE", flush=True)
        print(f"{'='*70}", flush=True)
        print(f"Exception: {e}", flush=True)
        import traceback
        traceback.print_exc()
        print(f"{'='*70}\n", flush=True)
        return False


# ================================================================================
# TEST DU MODULE (debug local)
# ================================================================================

if __name__ == "__main__":
    print("="*70)
    print("TEST GRIB HANDLER v3.2.0 - RESEND")
    print("="*70)
    
    # Test 1: Vérifier configuration
    print("\n📋 Test 1: Configuration")
    print("-"*70)
    
    from config import RESEND_API_KEY, SAILDOCS_EMAIL
    
    if RESEND_API_KEY:
        print(f"✅ RESEND_API_KEY: {RESEND_API_KEY[:10]}...")
    else:
        print(f"❌ RESEND_API_KEY manquant")
    
    print(f"✅ SAILDOCS_EMAIL: {SAILDOCS_EMAIL}")
    
    # Test 2: Simulation envoi
    print("\n📋 Test 2: Test envoi Saildocs")
    print("-"*70)
    print("⚠️  Test désactivé pour ne pas consommer quota")
    print("💡 Décommentez le code ci-dessous pour tester:")
    print()
    print("# test_request = 'ecmwf:40N,50N,15W,5W|0.5,0.5|0,24..48|WIND'")
    print("# send_to_saildocs(test_request)")
    
    print("\n" + "="*70)
    print("TESTS TERMINÉS")
    print("="*70)
