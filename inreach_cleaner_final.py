# inreach_cleaner_final.py - v3.5.8
"""FIX: Support points décimaux (0.5, 0.25) dans requêtes GRIB"""

import re


def clean_inreach_email(raw_body: str) -> str:
    """
    Nettoie un email InReach pour extraire UNIQUEMENT la requête utilisateur
    
    Supprime:
    - Liens InReach (https://inreachlink.com/...)
    - Texte "View the location or send a reply to..."
    - Texte "Do not reply directly to this message"
    - Texte "This message was sent to you using..."
    - URL explore.garmin.com
    - Lignes vides
    
    Args:
        raw_body: Corps brut de l'email InReach
        
    Returns:
        Requête utilisateur nettoyée (sans métadonnées)
    """
    if not raw_body:
        return ""
    
    # Séparer en lignes
    lines = raw_body.strip().split('\n')
    
    # Patterns à supprimer (ordre important)
    patterns_to_remove = [
        # URLs InReach
        r'https?://inreachlink\.com/\S+',
        r'http://explore\.garmin\.com/\S+',
        
        # Textes standards InReach
        r'View the location or send a reply to.*',
        r'Do not reply directly to this message.*',
        r'This message was sent to you using.*',
        
        # Lignes vides ou espaces
        r'^\s*$',
    ]
    
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        
        # Ignorer ligne vide
        if not line:
            continue
        
        # Vérifier si ligne correspond à un pattern à supprimer
        should_remove = False
        for pattern in patterns_to_remove:
            if re.search(pattern, line, re.IGNORECASE):
                should_remove = True
                break
        
        if not should_remove:
            cleaned_lines.append(line)
    
    # Rejoindre et nettoyer
    cleaned = ' '.join(cleaned_lines).strip()
    
    # Nettoyer espaces multiples
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    return cleaned


def extract_grib_request(raw_body: str) -> str:
    """
    Extrait une requête GRIB d'un email InReach
    
    v3.5.8: FIX - Support points décimaux (0.5, 0.25)
    
    Cherche pattern: GFS:lat1,lat2,lon1,lon2|param1,param2...
    
    Args:
        raw_body: Corps brut de l'email
        
    Returns:
        Requête GRIB nettoyée (ex: "GFS:8N,9N,80W,79W|0.5,0.5|0,3,6|WIND,GUST")
    """
    cleaned = clean_inreach_email(raw_body)
    
    # Pattern GRIB - v3.5.8: Ajout du point '.' pour supporter 0.5, 0.25, etc.
    grib_pattern = r'(GFS|GFS3)[:\s]+[-\d.,NSEW|A-Z\s]+'
    match = re.search(grib_pattern, cleaned, re.IGNORECASE)
    
    if match:
        grib_request = match.group(0)
        # Nettoyer espaces autour des caractères spéciaux
        grib_request = re.sub(r'\s*([,|:])\s*', r'\1', grib_request)
        return grib_request.strip()
    
    # Si pas de pattern GRIB trouvé, retourner texte nettoyé
    return cleaned


# Test du module
if __name__ == "__main__":
    # Test avec points décimaux
    test_email = """gfs:0N,1S,89W,91W|0.25,0.5|0,6,12,18,24|WIND,GUST

View the location or send a reply to Cedric ALVAREZ:
https://inreachlink.com/m3F_7nUuuZd009w-YzWOPQ

Do not reply directly to this message.

This message was sent to you using the inReach two-way satellite communicator with GPS."""
    
    print("="*70)
    print("TEST NETTOYAGE EMAIL INREACH v3.5.8")
    print("="*70)
    print(f"\n📧 Email original ({len(test_email)} chars):")
    print(test_email)
    
    print("\n" + "="*70)
    
    cleaned = clean_inreach_email(test_email)
    print(f"✅ Email nettoyé ({len(cleaned)} chars):")
    print(cleaned)
    
    print("\n" + "="*70)
    
    grib = extract_grib_request(test_email)
    print(f"🌊 Requête GRIB extraite ({len(grib)} chars):")
    print(grib)
    print(f"🔍 Contient '.' : {'OUI ✅' if '.' in grib else 'NON ❌'}")
    
    print("\n" + "="*70)
