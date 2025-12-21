#!/usr/bin/env bash
set -e

echo "🔧 Installation des dépendances..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🎭 Installation Playwright Chromium..."
playwright install chromium
playwright install-deps chromium

echo "📁 Copie browsers vers répertoire persistant..."
mkdir -p /opt/render/project/src/browsers
cp -r ~/.cache/ms-playwright/chromium-1091 /opt/render/project/src/browsers/

echo "✅ Build terminé avec succès!"
