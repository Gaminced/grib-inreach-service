#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Installer Chromium avec le bon path
PLAYWRIGHT_BROWSERS_PATH=$PWD/.browsers playwright install chromium
