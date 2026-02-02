# inreach_email_cleaner.py
"""Module de nettoyage des emails InReach pour extraction de la requête utilisateur"""

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
    
    Cherche pattern: GFS:lat1,lat2,lon1,lon2|param1,param2...
    
    Args:
        raw_body: Corps brut de l'email
        
    Returns:
        Requête GRIB nettoyée (ex: "GFS:8N,9N,80W,79W|1,1|0,3,6,12,18,24,36|WIND,GUST,PRMSL")
    """
    cleaned = clean_inreach_email(raw_body)
    
    # Pattern GRIB typique
    grib_pattern = r'(GFS|GFS3)[:\s]+[-\d,NSEW|A-Z\s]+'
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
    # Exemple d'email InReach réel
    test_email = """Gfs:8N,9N,80W,79W|1,1|0,3,6,12,18,24,36|WIND,GUST,PRMSL

View the location or send a reply to Cedric ALVAREZ:
https://inreachlink.com/m3F_7nUuuZd009w-YzWOPQ


Do not reply directly to this message.

This message was sent to you using the inReach two-way satellite communicator with GPS. To learn more, visit http://explore.garmin.com/inreach."""
    
    print("="*70)
    print("TEST NETTOYAGE EMAIL INREACH")
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
    
    print("\n" + "="*70)
    
    # Test avec question Claude/Mistral
    test_question = """Quelle est la différence entre un génois et un foc ?

View the location or send a reply to Cedric ALVAREZ:
https://inreachlink.com/abc123

Do not reply directly to this message.

This message was sent to you using the inReach two-way satellite communicator with GPS."""
    
    print("\n📧 Question maritime:")
    print(test_question)
    
    print("\n" + "="*70)
    
    cleaned_q = clean_inreach_email(test_question)
    print(f"✅ Question nettoyée:")
    print(cleaned_q)
