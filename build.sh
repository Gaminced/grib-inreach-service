#!/usr/bin/env bash
# build.sh - Script d'installation pour Render
# Installe les dependances Playwright

set -o errexit

echo "📦 Installation des dependances Python..."
pip install -r requirements.txt

echo "🌐 Installation Chromium pour Playwright..."
playwright install chromium

echo "📚 Installation dependances systeme Chromium..."
playwright install-deps chromium

echo "✅ Build termine!"
