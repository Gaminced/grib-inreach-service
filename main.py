#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service de traitement automatique des fichiers GRIB pour Garmin InReach
Surveille les emails, télécharge les fichiers GRIB, les traite avec Saildocs, 
et renvoie les données météo vers le Garmin InReach.
"""

import os
import sys
import time
import imaplib
import email
import smtplib
import requests
import schedule
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify

# ==========================================
# CONFIGURATION
# ==========================================

# Variables d'environnement (définies dans Render)
GARMIN_USERNAME = os.environ.get('GARMIN_USERNAME')
GARMIN_PASSWORD = os.environ.get('GARMIN_PASSWORD')

# Configuration Email (Garmin InReach)
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Adresse email de Saildocs pour récupérer les GRIB
SAILDOCS_EMAIL = "query@saildocs.com"

# Configuration du port pour Render
PORT = int(os.environ.get('PORT', 10000))

# ==========================================
# APPLICATION FLASK (pour le Health Check)
# ==========================================

app = Flask(__name__)

# Variable globale pour le statut
last_check_time = None
last_status = "Démarrage..."

@app.route('/')
def index():
    """Page d'accueil"""
    return jsonify({
        "service": "GRIB InReach Service",
        "status": "running",
        "last_check": str(last_check_time),
        "message": last_status
    })

@app.route('/health')
def health():
    """Endpoint de santé pour le monitoring"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "last_check": str(last_check_time)
    }), 200

@app.route('/status')
def status():
    """Statut détaillé du service"""
    return jsonify({
        "service": "GRIB InReach Service",
        "status": last_status,
        "last_check_time": str(last_check_time),
        "garmin_username": GARMIN_USERNAME if GARMIN_USERNAME else "Non configuré",
        "running": True
    })

# ==========================================
# FONCTIONS DE TRAITEMENT GRIB
# ==========================================

def check_credentials():
    """Vérifie que les identifiants Garmin sont configurés"""
    global last_status
    if not GARMIN_USERNAME or not GARMIN_PASSWORD:
        last_status = "❌ ERREUR: Variables GARMIN_USERNAME et GARMIN_PASSWORD non définies"
        print(last_status)
        return False
    print(f"✅ Identifiants Garmin configurés pour: {GARMIN_USERNAME}")
    return True

def connect_to_email():
    """Connexion à la boîte email Garmin InReach"""
    global last_status
    try:
        print(f"📧 Connexion à la boîte email: {GARMIN_USERNAME}")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(GARMIN_USERNAME, GARMIN_PASSWORD)
        print("✅ Connexion email réussie")
        return mail
    except Exception as e:
        last_status = f"❌ Erreur de connexion email: {str(e)}"
        print(last_status)
        return None

def check_for_grib_requests(mail):
    """Vérifie s'il y a des demandes de fichiers GRIB dans les emails"""
    global last_status, last_check_time
    
    try:
        mail.select('inbox')
        
        # Recherche des emails non lus avec le sujet GRIB
        status, messages = mail.search(None, 'UNSEEN', 'SUBJECT', '"GRIB"')
        
        if status != 'OK':
            last_status = "❌ Erreur lors de la recherche d'emails"
            return []
        
        email_ids = messages[0].split()
        print(f"📬 {len(email_ids)} nouveau(x) email(s) GRIB trouvé(s)")
        
        grib_requests = []
        
        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            
            if status != 'OK':
                continue
            
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            subject = email_message['subject']
            from_email = email_message['from']
            
            # Extraire les coordonnées et paramètres du corps de l'email
            body = get_email_body(email_message)
            
            grib_requests.append({
                'from': from_email,
                'subject': subject,
                'body': body,
                'email_id': email_id
            })
        
        last_check_time = datetime.now()
        last_status = f"✅ Vérification terminée - {len(grib_requests)} demande(s) trouvée(s)"
        
        return grib_requests
        
    except Exception as e:
        last_status = f"❌ Erreur lors de la vérification des emails: {str(e)}"
        print(last_status)
        return []

def get_email_body(email_message):
    """Extrait le corps de l'email"""
    body = ""
    
    if email_message.is_multipart():
        for part in email_message.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                break
    else:
        body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
    
    return body

def request_grib_from_saildocs(grib_params):
    """Envoie une demande de fichier GRIB à Saildocs"""
    global last_status
    
    try:
        print(f"🌊 Envoi de la demande GRIB à Saildocs...")
        
        # Construction du message pour Saildocs
        msg = MIMEMultipart()
        msg['From'] = GARMIN_USERNAME
        msg['To'] = SAILDOCS_EMAIL
        msg['Subject'] = "GRIB Request"
        
        # Corps du message avec les paramètres GRIB
        body = f"send {grib_params}"
        msg.attach(MIMEText(body, 'plain'))
        
        # Envoi via SMTP
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(GARMIN_USERNAME, GARMIN_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print("✅ Demande GRIB envoyée à Saildocs")
        last_status = "✅ Demande GRIB envoyée à Saildocs"
        return True
        
    except Exception as e:
        last_status = f"❌ Erreur lors de l'envoi à Saildocs: {str(e)}"
        print(last_status)
        return False

def send_grib_to_garmin(grib_data, recipient_email):
    """Envoie les données GRIB traitées vers le Garmin InReach"""
    global last_status
    
    try:
        print(f"📤 Envoi des données GRIB vers: {recipient_email}")
        
        msg = MIMEMultipart()
        msg['From'] = GARMIN_USERNAME
        msg['To'] = recipient_email
        msg['Subject'] = "Météo GRIB"
        
        # Formatage des données météo en texte court pour InReach
        formatted_data = format_grib_for_inreach(grib_data)
        msg.attach(MIMEText(formatted_data, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(GARMIN_USERNAME, GARMIN_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print("✅ Données GRIB envoyées au Garmin InReach")
        last_status = "✅ Données GRIB envoyées au Garmin InReach"
        return True
        
    except Exception as e:
        last_status = f"❌ Erreur lors de l'envoi au Garmin: {str(e)}"
        print(last_status)
        return False

def format_grib_for_inreach(grib_data):
    """Formate les données GRIB en texte court pour InReach (limitation 160 caractères)"""
    # TODO: Adapter selon le format de données GRIB reçu
    # Pour l'instant, retourne un format simple
    return f"Météo: Vent 15kts NE, Mer 1.5m, Tendance stable. {datetime.now().strftime('%d/%m %H:%M')}"

def process_grib_workflow():
    """Processus complet de traitement des fichiers GRIB"""
    global last_status, last_check_time
    
    print("\n" + "="*50)
    print(f"🔄 Démarrage du traitement GRIB - {datetime.now()}")
    print("="*50)
    
    if not check_credentials():
        return
    
    mail = connect_to_email()
    if not mail:
        return
    
    try:
        grib_requests = check_for_grib_requests(mail)
        
        for request in grib_requests:
            print(f"\n📩 Traitement de la demande de: {request['from']}")
            
            # Demande du fichier GRIB à Saildocs
            if request_grib_from_saildocs(request['body']):
                # Attente de la réponse de Saildocs (à adapter selon le temps réel)
                time.sleep(60)
                
                # TODO: Récupérer la réponse de Saildocs
                # TODO: Décoder le fichier GRIB
                grib_data = "Données météo simulées"
                
                # Envoi des données au Garmin
                send_grib_to_garmin(grib_data, request['from'])
        
        if len(grib_requests) == 0:
            last_status = "✅ Aucune nouvelle demande GRIB"
            print(last_status)
        
    finally:
        mail.logout()
        print("📧 Déconnexion de la boîte email")

# ==========================================
# PLANIFICATION DES TÂCHES
# ==========================================

def run_scheduled_tasks():
    """Exécute les tâches planifiées"""
    print("⏰ Planification : Vérification toutes les 6 heures")
    
    # Planification toutes les 6 heures
    schedule.every(6).hours.do(process_grib_workflow)
    
    # Exécution immédiate au démarrage
    process_grib_workflow()
    
    # Boucle de vérification du planificateur
    while True:
        schedule.run_pending()
        time.sleep(60)  # Vérification toutes les minutes

# ==========================================
# DÉMARRAGE DU SERVICE
# ==========================================

def run_flask_server():
    """Démarre le serveur Flask dans un thread séparé"""
    print(f"🌐 Démarrage du serveur HTTP sur le port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

def main():
    """Point d'entrée principal"""
    global last_status
    
    print("\n" + "="*50)
    print("🚀 DÉMARRAGE DU SERVICE GRIB INREACH")
    print("="*50)
    print(f"📅 Date: {datetime.now()}")
    print(f"🔧 Port: {PORT}")
    print(f"👤 Utilisateur Garmin: {GARMIN_USERNAME}")
    print("="*50 + "\n")
    
    last_status = "🚀 Service démarré"
    
    # Démarrage du serveur Flask dans un thread
    flask_thread = Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    
    # Attente que Flask démarre
    time.sleep(2)
    print("✅ Serveur HTTP démarré avec succès\n")
    
    # Démarrage des tâches planifiées (bloquant)
    try:
        run_scheduled_tasks()
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du service demandé")
        last_status = "🛑 Service arrêté"
        sys.exit(0)

if __name__ == "__main__":
    main()
