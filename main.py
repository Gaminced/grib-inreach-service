# main.py - v3.0.0
"""Point d'entrée principal - Flask + Scheduler"""

import sys
import schedule
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify

from config import (PORT, VERSION, VERSION_DATE, SERVICE_NAME, 
                   CHECK_INTERVAL_MINUTES, validate_config, get_config_status)
from email_monitor import check_gmail

# ==========================================
# APPLICATION FLASK
# ==========================================

app = Flask(__name__)

# Variables globales de statut
last_check_time = None
last_status = "Démarrage..."

@app.route('/')
def index():
    """Page d'accueil"""
    return jsonify({
        "service": SERVICE_NAME,
        "version": VERSION,
        "version_date": VERSION_DATE,
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
    config_status = get_config_status()
    
    return jsonify({
        "service": SERVICE_NAME,
        "version": VERSION,
        "version_date": VERSION_DATE,
        "status": "running",
        "current_status": last_status,
        "last_check_time": str(last_check_time) if last_check_time else "Aucune vérification encore",
        "config": config_status,
        "features": {
            "grib": "Format: gfs:8N,9N,80W,79W|1,1|0,3,6|WIND,GUST,PRMSL",
            "dual_url_support": "inreachlink.com + explore.garmin.com"
        }
    })

# ==========================================
# SCHEDULER
# ==========================================

def run_scheduler():
    """Thread pour vérifications périodiques"""
    global last_check_time, last_status
    
    print("\n" + "="*60)
    print("⏰ PLANIFICATION")
    print("="*60)
    print(f"📅 Vérification toutes les {CHECK_INTERVAL_MINUTES} MINUTES")
    print("="*60 + "\n")
    
    # Planifier les vérifications
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(check_gmail)
    
    # Première vérification immédiate
    print("🚀 Première vérification immédiate...\n")
    try:
        check_gmail()
        last_check_time = datetime.now()
        last_status = "✅ Vérification terminée"
    except Exception as e:
        last_status = f"❌ Erreur: {str(e)}"
        print(f"❌ Erreur première vérification: {e}")
    
    # Boucle du scheduler
    while True:
        schedule.run_pending()
        import time
        time.sleep(60)

# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 DÉMARRAGE GRIB INREACH SERVICE")
    print("="*60)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔖 Version: {VERSION} ({VERSION_DATE})")
    print(f"🌐 Port: {PORT}")
    print("="*60 + "\n")
    
    # Validation de la configuration
    config_errors = validate_config()
    
    if config_errors:
        print("❌ ERREURS DE CONFIGURATION:")
        for error in config_errors:
            print(f"   - {error}")
        print("\n⚠️  Le service démarre quand même mais certaines fonctionnalités seront limitées\n")
    else:
        print("✅ Configuration validée\n")
    
    # Démarrer le thread scheduler
    print("🔧 Démarrage thread scheduler...")
    scheduler_thread = Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    print("\n🌐 Démarrage Flask sur port", PORT)
    print("="*60 + "\n")
    
    # Démarrer Flask
    app.run(host='0.0.0.0', port=PORT, debug=False)
