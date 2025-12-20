#!/usr/bin/env bash
# build.sh - Version 2.3.1
# Date: 2025-12-19
# Changements: Installation Chromium dans répertoire persistant
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Installer Chromium dans le répertoire par défaut
playwright install chromium

# Créer le répertoire persistant et copier chromium
mkdir -p /opt/render/project/src/.browsers
cp -r /opt/render/.cache/ms-playwright/* /opt/render/project/src/.browsers/ 2>/dev/null || true

echo "Build terminé"
ls -la /opt/render/project/src/.browsers 2>/dev/null || echo "Browsers dir not accessible"
