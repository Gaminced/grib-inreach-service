# grib_handler.py V1.0
"""Module pour gérer les requêtes GRIB via Saildocs"""

import time
import base64
import zlib
import email
import requests
from config import (GARMIN_USERNAME, SENDGRID_API_KEY, SAILDOCS_EMAIL,
                    SAILDOCS_RESPONSE_EMAIL, MAX_MESSAGE_LENGTH)


def send_to_saildocs(grib_request):
    """
    Envoie une requête GRIB à Saildocs
    
    Args:
        grib_request: Requête GRIB (ex: "ecmwf:24n,34n,72w,60w|8,8|12,48|wind,press")
        
    Returns:
        bool: True si envoyé
    """
    try:
        print(f"🌊 Envoi GRIB à Saildocs: {grib_request}")
        
        if not SENDGRID_API_KEY:
            print("❌ SENDGRID_API_KEY manquante")
            return False
        
        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "personalizations": [{
                "to": [{"email": SAILDOCS_EMAIL}],
                "subject": "GRIB Request"
            }],
            "from": {"email": GARMIN_USERNAME},
            "content": [{
                "type": "text/plain",
                "value": f"send {grib_request}"
            }]
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 202:
            print(f"✅ Demande GRIB envoyée à Saildocs")
            return True
        else:
            print(f"❌ Erreur SendGrid: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur envoi Saildocs: {e}")
        return False


def wait_for_saildocs_response(mail, timeout=300):
    """
    Attend la réponse de Saildocs avec le fichier GRIB
    
    Args:
        mail: Connexion IMAP
        timeout: Temps max d'attente en secondes
        
    Returns:
        bytes: Données GRIB ou None
    """
    print(f"⏳ Attente réponse Saildocs (max {timeout}s)...")
    
    start_time = time.time()
    check_count = 0
    
    while time.time() - start_time < timeout:
        try:
            check_count += 1
            elapsed = int(time.time() - start_time)
            
            if check_count % 6 == 1:
                print(f"   ⏱️  {elapsed}s écoulées...")
            
            mail.select("inbox")
            status, messages = mail.search(None, f'(FROM "{SAILDOCS_RESPONSE_EMAIL}" UNSEEN)')
            
            if status == "OK" and messages[0]:
                email_ids = messages[0].split()
                print(f"   📧 {len(email_ids)} email(s) Saildocs trouvé(s)")
                
                for email_id in email_ids:
                    status, msg_data = mail.fetch(email_id, "(RFC822)")
                    
                    if status != "OK":
                        continue
                    
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            # Chercher pièce jointe GRIB
                            for part in msg.walk():
                                if part.get_content_disposition() == "attachment":
                                    filename = part.get_filename()
                                    
                                    if filename and ('.grb' in filename.lower() or '.grib' in filename.lower()):
                                        grib_data = part.get_payload(decode=True)
                                        print(f"   ✅ GRIB reçu: {len(grib_data)} octets")
                                        return grib_data
            
            time.sleep(10)
            
        except Exception as e:
            print(f"   ⚠️  Erreur attente: {e}")
            time.sleep(10)
    
    print(f"❌ Timeout Saildocs après {timeout}s")
    return None


def encode_grib_to_messages(grib_data):
    """
    Encode un fichier GRIB en messages de 120 caractères
    
    Args:
        grib_data: Données GRIB brutes
        
    Returns:
        list: Messages encodés
    """
    print(f"\n{'='*60}")
    print("ENCODAGE GRIB")
    print(f"{'='*60}")
    
    # 1. Compression
    compressed = zlib.compress(grib_data, level=9)
    ratio = (1 - len(compressed) / len(grib_data)) * 100
    print(f"1. Compression: {len(grib_data)} → {len(compressed)} octets ({ratio:.1f}%)")
    
    # 2. Base64
    encoded = base64.b64encode(compressed).decode('utf-8')
    print(f"2. Base64: {len(encoded)} caractères")
    
    # 3. Découpage en chunks
    chunks = [encoded[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(encoded), MAX_MESSAGE_LENGTH)]
    total = len(chunks)
    print(f"3. Découpage: {total} messages")
    
    # 4. Formatage messages
    messages = []
    for i, chunk in enumerate(chunks):
        msg = f"msg {i+1}/{total}:\n{chunk}\nend"
        messages.append(msg)
    
    print(f"{'='*60}\n")
    
    return messages
