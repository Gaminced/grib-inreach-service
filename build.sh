#!/usr/bin/env bash
set -e

echo "🔧 Installation des dépendances Python..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🎭 Installation Playwright Chromium..."
playwright install chromium

echo "📁 Copie browsers vers répertoire persistant..."
mkdir -p /opt/render/project/src/browsers
cp -r ~/.cache/ms-playwright/chromium-1091 /opt/render/project/src/browsers/

echo "✅ Build terminé avec succès!"
