#!/usr/bin/env bash
set -o errexit

export PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/src/.browsers

pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium

echo "Chromium installed at: $PLAYWRIGHT_BROWSERS_PATH"
ls -la $PLAYWRIGHT_BROWSERS_PATH
