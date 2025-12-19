#!/usr/bin/env bash
# exit on error
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Installer uniquement le browser sans les dépendances système
PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0 playwright install chromium

# Les dépendances chromium seront installées automatiquement par Render
