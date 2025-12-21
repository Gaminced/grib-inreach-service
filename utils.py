# utils.py - v3.0.0
"""Fonctions utilitaires pour encodage/décodage GRIB"""

import base64
import zlib
from config import MAX_MESSAGE_LENGTH


def encode_and_split_grib(grib_data):
    """
    Compresse et découpe fichier GRIB en messages
    
    Args:
        grib_data: Données GRIB brutes (bytes)
        
    Returns:
        list: Liste de messages formatés
    """
    print(f"\n{'='*60}")
    print("ENCODAGE GRIB")
    print(f"{'='*60}")
    
    # 1. Compression
    compressed = zlib.compress(grib_data, level=9)
    ratio = (1 - len(compressed)/len(grib_data)) * 100
    print(f"1. Compression: {len(grib_data)} → {len(compressed)} octets ({ratio:.1f}%)")
    
    # 2. Base64
    encoded = base64.b64encode(compressed).decode('utf-8')
    print(f"2. Base64: {len(encoded)} caractères")
    
    # 3. Découpage
    chunks = [encoded[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(encoded), MAX_MESSAGE_LENGTH)]
    total = len(chunks)
    print(f"3. Découpage: {total} messages")
    
    # 4. Formatage
    messages = []
    for i, chunk in enumerate(chunks):
        msg = f"msg {i+1}/{total}:\n{chunk}\nend"
        messages.append(msg)
        print(f"   Message {i+1}/{total}: {len(chunk)} chars")
    
    print(f"{'='*60}\n")
    
    return messages


def extract_grib_request(body):
    """
    Extrait la requête GRIB pure du corps de l'email
    Format: gfs:8N,9N,80W,79W|1,1|0,3,6,12,18,24,36|WIND,GUST,PRMSL
    
    IMPORTANT: Retourne SEULEMENT la requête, sans signature ni URL
    
    Args:
        body: Corps complet de l'email
        
    Returns:
        str: Requête GRIB pure ou None
    """
    import re
    
    # Pattern pour détecter requête GRIB
    grib_pattern = r'(gfs|ecmwf|arpege|icon)[:\s]*([\d\w\s,\-\|\.NSEW]+)'
    match = re.search(grib_pattern, body, re.IGNORECASE)
    
    if match:
        # Extraire la requête complète
        grib_request = match.group(0).strip()
        
        # Nettoyer: enlever tout ce qui suit après la requête
        # (signature, URLs, etc.)
        lines = grib_request.split('\n')
        clean_request = lines[0].strip()
        
        print(f"   📝 Requête GRIB extraite: {clean_request}")
        return clean_request
    
    return None


def extract_inreach_url(body):
    """
    Extrait l'URL inReach du corps de l'email
    
    Args:
        body: Corps de l'email
        
    Returns:
        str: URL inReach ou None
    """
    import re
    
    url_patterns = [
        r'(https://inreachlink\.com/[^\s]+)',
        r'(https://[^\s]*explore\.garmin\.com/textmessage/txtmsg[^\s]+)',
        r'(https://[^\s]*eur\.explore\.garmin\.com/textmessage/txtmsg[^\s]+)'
    ]
    
    for pattern in url_patterns:
        match = re.search(pattern, body)
        if match:
            url = match.group(1)
            # Nettoyer l'URL (enlever trailing chars)
            url = url.rstrip('>')
            return url
    
    return None
