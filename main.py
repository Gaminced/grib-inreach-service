# main.py
"""Service GRIB inReach avec Multi-AI - Architecture modulaire"""

import time
import schedule
from datetime import datetime, timezone
from threading import Thread, Event
from flask import Flask, jsonify

# Imports des modules
from config import PORT, check_credentials, ANTHROPIC_API_KEY, MISTRAL_API_KEY
from email_monitor import connect_gmail, check_for_requests
from claude_handler import query_claude
from mistral_handler import query_mistral
from grib_handler import send_to_saildocs, wait_for_saildocs_response, encode_grib_to_messages
from inreach_sender import send_to_inreach

# ==========================================
# FLASK APPLICATION
# ==========================================

app = Flask(__name__)

# Variables globales pour statut
last_check_time = None
last_status = "Démarrage..."
thread_started = Event()


@app.route('/')
def index():
    """Page d'accueil"""
    return jsonify({
        "service": "GRIB InReach Multi-AI",
        "status": "running",
        "last_check": str(last_check_time),
        "message": last_status,
        "features": ["GRIB files", "Claude AI", "Mistral AI"]
    })


@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "last_check": str(last_check_time)
    }), 200


@app.route('/status')
def status():
    """Statut détaillé"""
    return jsonify({
        "service": "GRIB InReach Multi-AI",
        "status": "running",
        "current_status": last_status,
        "last_check_time": str(last_check_time) if last_check_time else "Aucune vérification",
        "anthropic_configured": "✅" if ANTHROPIC_API_KEY else "❌",
        "mistral_configured": "✅" if MISTRAL_API_KEY else "❌",
        "verification_frequency": "Toutes les 5 minutes",
        "features": {
            "grib": "Format: ecmwf:24n,34n,72w,60w|8,8|12,48|wind,press",
            "claude": "Format: claude <max_words>: <question>",
            "mistral": "Format: mistral <max_words>: <question>"
        }
    })


# ==========================================
# TRAITEMENT WORKFLOW
# ==========================================

def process_workflow():
    """Processus complet de traitement"""
    global last_status, last_check_time
    
    print("\n" + "="*70)
    print(f"🔄 TRAITEMENT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    if not check_credentials():
        return
    
    mail = connect_gmail()
    if not mail:
        return
    
    try:
        requests_list = check_for_requests(mail)
        
        if not requests_list:
            print("✅ Aucune nouvelle requête")
            last_status = "✅ Aucune demande"
            return
        
        print(f"\n🎯 {len(requests_list)} REQUÊTE(S) TROUVÉE(S)!")
        
        for idx, req in enumerate(requests_list, 1):
            print(f"\n{'='*70}")
            print(f"🔄 Requête {idx}/{len(requests_list)} - Type: {req['type']}")
            print(f"{'='*70}")
            
            # TRAITEMENT AI
            if req['type'] == 'ai':
                provider = req['provider']
                print(f"\n🤖 {provider.upper()}: {req['question'][:50]}...")
                print(f"   Max words: {req['max_words']}")
                
                # Appeler le bon provider
                if provider == 'claude':
                    messages = query_claude(req['question'], req['max_words'])
                elif provider == 'mistral':
                    messages = query_mistral(req['question'], req['max_words'])
                else:
                    messages = [f"Provider inconnu: {provider}"]
                
                print(f"\n📦 {len(messages)} MESSAGES À ENVOYER")
                
                # Envoyer
                if send_to_inreach(req['reply_url'], messages, req['reply_email']):
                    print(f"✅✅✅ SUCCÈS {provider.upper()}: {len(messages)} messages")
                    last_status = f"✅ {provider.upper()}: {len(messages)} msg"
                else:
                    print(f"❌ ÉCHEC {provider.upper()}")
                    last_status = f"❌ {provider.upper()} échec"
            
            # TRAITEMENT GRIB
            elif req['type'] == 'grib':
                print(f"\n🌊 GRIB: {req['request']}")
                
                # Envoyer à Saildocs
                if not send_to_saildocs(req['request']):
                    print("❌ Échec envoi Saildocs")
                    last_status = "❌ GRIB échec Saildocs"
                    continue
                
                # Attendre réponse
                grib_data = wait_for_saildocs_response(mail, timeout=300)
                
                if not grib_data:
                    print("❌ Timeout Saildocs")
                    last_status = "❌ GRIB timeout"
                    continue
                
                # Encoder
                messages = encode_grib_to_messages(grib_data)
                print(f"\n📦 {len(messages)} MESSAGES GRIB À ENVOYER")
                
                # Envoyer
                if send_to_inreach(req['reply_url'], messages, req['reply_email']):
                    print(f"✅✅✅ SUCCÈS GRIB: {len(messages)} messages")
                    last_status = f"✅ GRIB: {len(messages)} msg"
                else:
                    print(f"❌ ÉCHEC GRIB")
                    last_status = "❌ GRIB échec envoi"
        
        last_check_time = datetime.now()
        
    except Exception as e:
        print(f"❌ ERREUR WORKFLOW: {e}")
        import traceback
        traceback.print_exc()
        last_status = f"❌ Erreur: {str(e)[:50]}"
    
    finally:
        try:
            mail.logout()
        except:
            pass


# ==========================================
# SCHEDULER
# ==========================================

def run_scheduled_tasks():
    """Exécute les tâches planifiées"""
    print("\n🚨 THREAD SCHEDULER ACTIF")
    thread_started.set()
    
    print("\n" + "="*60)
    print("⏰ PLANIFICATION")
    print("="*60)
    print("📅 Vérification toutes les 5 MINUTES")
    print("🤖 Claude AI + Mistral AI activés")
    print("="*60 + "\n")
    
    # Vérification toutes les 5 minutes
    schedule.every(5).minutes.do(process_workflow)
    
    # Heartbeat toutes les 2 minutes
    def heartbeat():
        current_time = datetime.now().strftime('%H:%M:%S')
        print(f"💓 {current_time} - Service actif")
    
    schedule.every(2).minutes.do(heartbeat)
    
    # Première vérification immédiate
    print("🚀 Première vérification immédiate...\n")
    process_workflow()
    print("\n✅ Première vérification terminée")
    print(f"⏰ Prochaine vérification dans 5 minutes\n")
    
    # Boucle principale
    loop_count = 0
    while True:
        try:
            loop_count += 1
            if loop_count % 5 == 0:
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f"🔄 Loop #{loop_count} - {current_time}")
            
            schedule.run_pending()
            time.sleep(60)
            
        except Exception as e:
            print(f"❌ ERREUR boucle: {e}")
            time.sleep(60)


# ==========================================
# DÉMARRAGE
# ==========================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 DÉMARRAGE GRIB INREACH MULTI-AI")
    print("="*60)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🤖 Claude: {'✅' if ANTHROPIC_API_KEY else '❌'}")
    print(f"🤖 Mistral: {'✅' if MISTRAL_API_KEY else '❌'}")
    print(f"🌐 Port: {PORT}")
    print("="*60 + "\n")
    
    if not check_credentials():
        import sys
        sys.exit(1)
    
    # Démarrer thread scheduler
    print("🔧 Démarrage thread scheduler...")
    scheduler_thread = Thread(target=run_scheduled_tasks, daemon=True)
    scheduler_thread.start()
    
    if thread_started.wait(timeout=10):
        print("✅ Thread scheduler actif\n")
    else:
        print("⚠️  Thread ne répond pas\n")
    
    # Démarrer Flask
    print(f"🌐 Démarrage Flask sur port {PORT}...")
    print("="*60 + "\n")
    
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 Arrêt utilisateur")
    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE: {e}")
        import sys
        sys.exit(1)
