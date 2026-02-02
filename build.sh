#!/usr/bin/env bash
# build.sh - v3.2.2
# Build simplifié - Utilise Chromium pré-installé de Render
set -e

echo "========================================================================"
echo "🚀 BUILD GARMIN INREACH SERVICE v3.2.2"
echo "========================================================================"

# =============================================================================
# Installation Python uniquement
# =============================================================================
echo ""
echo "🐍 Installation dépendances Python..."
echo "------------------------------------------------------------------------"

pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Python packages installés:"
pip list | grep -E "(resend|anthropic|mistral|playwright)" || true

# =============================================================================
# Configuration Playwright - Utilise Chromium pré-installé de Render
# =============================================================================
echo ""
echo "🎭 Configuration Playwright..."
echo "------------------------------------------------------------------------"

echo "🎭 Installation Playwright Chromium..."
playwright install chromium

echo "✅ Playwright configuré pour utiliser Chromium système de Render"

# =============================================================================
# FIN
# =============================================================================
echo ""
echo "========================================================================"
echo "✅ BUILD TERMINÉ AVEC SUCCÈS!"
echo "========================================================================"
echo ""
echo "📦 Packages installés:"
echo "   ✅ resend (emails GRIB)"
echo "   ✅ anthropic (Claude AI)"
echo "   ✅ mistralai (Mistral AI)"
echo "   ✅ playwright (automation)"
echo ""
echo "🎭 Playwright:"
echo "   ✅ Utilisera Chromium système de Render"
echo ""
echo "🚀 Service prêt à démarrer!"
echo "========================================================================"
