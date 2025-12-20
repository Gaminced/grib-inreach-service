#!/usr/bin/env bash
# build.sh - Version 2.4.2
# Date: 2025-12-20
# Changements: Copie Chromium vers projet persistant
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Installer Chromium
playwright install chromium

# Copier vers répertoire persistant
mkdir -p /opt/render/project/src/browsers
cp -r ~/.cache/ms-playwright/* /opt/render/project/src/browsers/ 2>/dev/null || \
cp -r /opt/render/.cache/ms-playwright/* /opt/render/project/src/browsers/ 2>/dev/null || \
echo "Installation Chromium standard"

echo "Build terminé - anthropic 0.34.0 installé"
