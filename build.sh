#!/usr/bin/env bash
# exit on error
set -o errexit

pip install --upgrade pip

# Installer Flask SANS dépendances pour éviter greenlet
pip install --no-deps Flask==2.3.3
pip install --no-deps Werkzeug==2.3.7

# Installer les autres packages normalement
pip install requests==2.32.3
pip install anthropic==0.39.0
pip install python-dotenv==1.0.1
pip install sendgrid==6.11.0
pip install gunicorn==21.2.0

# Installer les dépendances manquantes de Flask
pip install Jinja2>=3.0
pip install itsdangerous>=2.0
pip install click>=8.0
pip install blinker>=1.6.2

# Playwright en dernier
pip install playwright==1.40.0
playwright install chromium
playwright install-deps chromium
