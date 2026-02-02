#!/usr/bin/env bash
# build.sh - v3.2.0
# Script de build pour Render.com avec Playwright + Resend
set -e

echo "========================================================================"
echo "🚀 BUILD GARMIN INREACH SERVICE v3.2.0"
echo "========================================================================"

# =============================================================================
# ÉTAPE 1: Installation Python
# =============================================================================
echo ""
echo "🐍 ÉTAPE 1/3: Installation dépendances Python..."
echo "------------------------------------------------------------------------"
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Python packages installés"

# =============================================================================
# ÉTAPE 2: Installation Playwright Chromium
# =============================================================================
echo ""
echo "🎭 ÉTAPE 2/3: Installation Playwright Chromium..."
echo "------------------------------------------------------------------------"

# Installation avec dépendances système
PLAYWRIGHT_BROWSERS_PATH=/opt/render/.cache playwright install --with-deps chromium

echo "✅ Playwright Chromium installé"

# Vérification
echo ""
echo "🔍 Vérification installation Playwright..."
if [ -d "/opt/render/.cache/ms-playwright" ]; then
    echo "✅ Répertoire Playwright trouvé:"
    ls -lah /opt/render/.cache/ms-playwright/ | head -10
else
    echo "⚠️  Répertoire Playwright non trouvé, utilisation cache par défaut"
fi

# =============================================================================
# ÉTAPE 3: Configuration cache persistant (optionnel)
# =============================================================================
echo ""
echo "📁 ÉTAPE 3/3: Configuration cache..."
echo "------------------------------------------------------------------------"

# Créer répertoire de cache si nécessaire
mkdir -p /opt/render/project/src/.cache

# Variable d'environnement pour Playwright
export PLAYWRIGHT_BROWSERS_PATH=/opt/render/.cache

echo "✅ Cache configuré"

# =============================================================================
# FIN
# =============================================================================
echo ""
echo "========================================================================"
echo "✅ BUILD TERMINÉ AVEC SUCCÈS!"
echo "========================================================================"
echo ""
echo "📦 Packages installés:"
echo "   - resend (emails GRIB)"
echo "   - anthropic (Claude)"
echo "   - mistralai (Mistral)"
echo "   - playwright (automation inReach)"
echo ""
echo "🎭 Playwright:"
echo "   - Chromium installé avec dépendances système"
echo "   - Cache: /opt/render/.cache"
echo ""
echo "🚀 Service prêt à démarrer!"
echo "========================================================================"
