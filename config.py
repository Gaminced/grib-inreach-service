# config.py
"""
Configuration centralisée pour le service Garmin inReach AI
v3.2.0: Migration SendGrid → Resend
"""

import os

# =============================================================================
# GMAIL / IMAP
# =============================================================================
GARMIN_USERNAME = os.getenv('GARMIN_USERNAME', 'garminced@gmail.com')
GARMIN_PASSWORD = os.getenv('GARMIN_PASSWORD')

IMAP_HOST = 'imap.gmail.com'
IMAP_PORT = 993

# =============================================================================
# RESEND (Remplacement SendGrid)
# =============================================================================
# NOUVEAU: Resend API Key (100 emails/jour gratuit)
# Format: re_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# Obtenir sur: https://resend.com/api-keys
RESEND_API_KEY = os.getenv('RESEND_API_KEY')

# ANCIEN: SendGrid (ne plus utiliser)
# SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')  # DEPRECATED

# =============================================================================
# SAILDOCS GRIB
# =============================================================================
SAILDOCS_EMAIL = 'query@saildocs.com'
SAILDOCS_RESPONSE_EMAIL = 'query-reply@saildocs.com'
SAILDOCS_TIMEOUT = 300  # 5 minutes

# =============================================================================
# ANTHROPIC (Claude)
# =============================================================================
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Solde Claude (optionnel, pour tracking)
CLAUDE_BALANCE = float(os.getenv('CLAUDE_BALANCE', '5.00'))

# =============================================================================
# MISTRAL AI
# =============================================================================
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')

# Solde Mistral (optionnel, pour tracking)
MISTRAL_BALANCE = float(os.getenv('MISTRAL_BALANCE', '5.00'))

# =============================================================================
# VALIDATION CONFIGURATION
# =============================================================================

def validate_config():
    """Valide que toutes les variables essentielles sont configurées"""
    
    errors = []
    warnings = []
    
    # OBLIGATOIRES
    if not GARMIN_USERNAME:
        errors.append("❌ GARMIN_USERNAME manquant")
    
    if not GARMIN_PASSWORD:
        errors.append("❌ GARMIN_PASSWORD manquant")
    
    # RECOMMANDÉES pour GRIB
    if not RESEND_API_KEY:
        warnings.append("⚠️  RESEND_API_KEY manquant (requis pour GRIB)")
    
    # RECOMMANDÉES pour AI
    if not ANTHROPIC_API_KEY:
        warnings.append("⚠️  ANTHROPIC_API_KEY manquant (Claude désactivé)")
    
    if not MISTRAL_API_KEY:
        warnings.append("⚠️  MISTRAL_API_KEY manquant (Mistral désactivé)")
    
    # Affichage
    print("\n" + "="*70)
    print("🔍 VALIDATION CONFIGURATION")
    print("="*70)
    
    if errors:
        print("\n❌ ERREURS CRITIQUES:")
        for error in errors:
            print(f"   {error}")
    
    if warnings:
        print("\n⚠️  AVERTISSEMENTS:")
        for warning in warnings:
            print(f"   {warning}")
    
    if not errors and not warnings:
        print("\n✅ Configuration complète et valide")
    
    print("="*70 + "\n")
    
    return len(errors) == 0


# Test automatique au démarrage
if __name__ == "__main__":
    print("="*70)
    print("TEST CONFIG.PY v3.2.0")
    print("="*70)
    
    validate_config()
    
    print("\n📋 Configuration actuelle:")
    print(f"   GARMIN_USERNAME: {GARMIN_USERNAME}")
    print(f"   GARMIN_PASSWORD: {'✅ configuré' if GARMIN_PASSWORD else '❌ manquant'}")
    print(f"   RESEND_API_KEY: {'✅ configuré' if RESEND_API_KEY else '❌ manquant'}")
    print(f"   ANTHROPIC_API_KEY: {'✅ configuré' if ANTHROPIC_API_KEY else '❌ manquant'}")
    print(f"   MISTRAL_API_KEY: {'✅ configuré' if MISTRAL_API_KEY else '❌ manquant'}")
    
    print("\n" + "="*70)
