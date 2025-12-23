# 🌊 GRIB InReach Service avec Multi-AI

Service automatisé pour navigateurs en mer : fichiers météo GRIB et assistants AI (Claude/Mistral) via satellite Garmin InReach.

**Version actuelle :** v3.2.0  
**Auteur :** Cédric  
**Date :** Décembre 2025

---

## 📋 Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Architecture](#architecture)
- [Fonctionnalités](#fonctionnalités)
- [Commandes disponibles](#commandes-disponibles)
- [Installation](#installation)
- [Configuration](#configuration)
- [Structure des fichiers](#structure-des-fichiers)
- [Flux de données](#flux-de-données)
- [API et coûts](#api-et-coûts)
- [Déploiement](#déploiement)
- [Dépannage](#dépannage)

---

## 🎯 Vue d'ensemble

Ce service permet aux navigateurs en mer d'accéder à :
- **Fichiers GRIB météo** via Saildocs
- **Assistants AI maritimes** spécialisés (Claude/Mistral)
- **Assistants AI génériques** pour questions diverses
- **Expert météo** Mistral pour analyses spécialisées

Le tout via **satellite Garmin InReach**, avec réponses compressées et optimisées.

### Cas d'usage

1. **Navigateur en mer** → Envoie "c 150: vent prévu demain?" depuis inReach
2. **Service détecte** → Requête Claude maritime
3. **Claude répond** → Assistant maritime spécialisé
4. **Réponse découpée** → Messages ≤160 chars pour satellite
5. **Navigateur reçoit** → Réponse concise et actio

nnable

---

## 🏗️ Architecture

### Architecture modulaire (v3.0+)

```
┌─────────────────────────────────────────────────┐
│          Garmin InReach (Satellite)            │
│         Email → inreach@garmin.com             │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│              Gmail (IMAP)                       │
│      Réception emails InReach                   │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│         email_monitor.py (v3.2.0)              │
│    • Détection patterns (GRIB/AI)              │
│    • Extraction URL réponse                     │
│    • Routage vers handlers                      │
└──┬──────────┬──────────┬──────────┬─────────────┘
   │          │          │          │
   ▼          ▼          ▼          ▼
┌─────┐  ┌────────┐  ┌────────┐  ┌──────┐
│GRIB │  │Claude  │  │Mistral │  │Météo │
│     │  │Handler │  │Handler │  │Expert│
└──┬──┘  └───┬────┘  └───┬────┘  └──┬───┘
   │         │            │           │
   │         └────────────┴───────────┘
   │                  │
   ▼                  ▼
┌─────────────┐  ┌──────────────────┐
│ Saildocs    │  │ Anthropic/Mistral│
│ (GRIB)      │  │ API              │
└──┬──────────┘  └────────┬─────────┘
   │                      │
   │                      ▼
   │              ┌───────────────┐
   │              │ Découpage     │
   │              │ 160 chars max │
   │              └───────┬───────┘
   │                      │
   └──────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│         inreach_sender.py (v3.2.1)             │
│    • Playwright (inreachlink.com)              │
│    • POST API (explore.garmin.com)             │
│    • SendGrid Email (fallback)                 │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│          Garmin InReach (Satellite)            │
│         Réponses → Navigateur                   │
└─────────────────────────────────────────────────┘
```

---

## ✨ Fonctionnalités

### 1. Fichiers GRIB météo

**Format :** `ecmwf:lat1,lat2,lon1,lon2|résolution|heures|paramètres`

**Exemple :**
```
ecmwf:0S,10S,90W,80W|1,1|0,24,48|WIND,PRESS
```

**Traitement :**
1. Requête envoyée à Saildocs (query@saildocs.com)
2. Réception fichier GRIB
3. Compression zlib + encodage base64
4. Découpage en messages 120 chars
5. Envoi vers inReach

### 2. Assistants AI maritimes (spécialisés)

**Optimisés pour :** Navigation, météo marine, sécurité, manœuvres

**Patterns courts :**
- `c 150: question` → Claude maritime
- `m 150: question` → Mistral maritime
- `w 150: question` → Weather expert (Mistral météo)

**Patterns longs (compatibilité) :**
- `claude 150: question` → Claude maritime
- `mistral 150: question` → Mistral maritime

**Caractéristiques :**
- Réponses **ultra-concises** (max 160 chars si possible)
- Vocabulaire maritime précis
- Conseils **actionnables**
- Système prompt spécialisé navigation

**Exemple :**
```
Envoi: c 50: vent 40kt que faire?
Réponse: Réduire voilure: prendre 2-3 ris grand-voile, 
genois → trinquette. Cap de fuite si nécessaire. 
Vérifier météo évolution.
```

### 3. Assistants AI génériques (standard)

**Pour :** Questions générales, calculs, traductions, culture, etc.

**Patterns :**
- `cg 150: question` → Claude générique
- `mg 150: question` → Mistral générique

**Caractéristiques :**
- Pas de spécialisation maritime
- Réponses complètes
- Tous sujets

**Exemple :**
```
Envoi: cg 100: translate "hello sailor" to spanish
Réponse: "Hola marinero"
```

### 4. Expert météo Mistral

**Spécialisé :** Interprétation GRIB, prévisions route, fenêtres météo

**Pattern :**
- `w 150: question`

**Exemple :**
```
Envoi: w 100: GRIB montre 25kt NO demain, bon pour cap 270?
Réponse: 25kt NO cap 270° = vent de travers, allure OK. 
Vérifier mer croisée. Fenêtre stable 24h.
```

---

## 📱 Commandes disponibles

### Résumé des patterns

| Pattern | Type | Spécialisation | Exemple |
|---------|------|----------------|---------|
| `c 150: ...` | Claude | Maritime | `c 50: météo demain?` |
| `cg 150: ...` | Claude | Générique | `cg 100: capital of France?` |
| `m 150: ...` | Mistral | Maritime | `m 50: distance Panama-Galápagos?` |
| `mg 150: ...` | Mistral | Générique | `mg 100: traduire bonjour en anglais` |
| `w 150: ...` | Mistral | Météo expert | `w 100: interpréter GRIB vent 30kt` |
| `claude 150: ...` | Claude | Maritime | `claude 50: réduire voilure?` |
| `mistral 150: ...` | Mistral | Maritime | `mistral 50: cap Easter Island?` |
| `ecmwf:...` | GRIB | Météo | `ecmwf:0S,92W+150` |

### Notation nombre

Le nombre après le pattern = **nombre de mots approximatif** pour la réponse totale.

**Exemples :**
- `c 50: ...` → ~50 mots → ~1 message
- `c 150: ...` → ~150 mots → ~2-3 messages
- `cg 200: ...` → ~200 mots → ~3-4 messages

**Recommandations :**
- Questions simples : 50-100 mots
- Questions complexes : 100-200 mots
- Max conseillé : 200 mots (coût satellite)

---

## 🚀 Installation

### Prérequis

- Python 3.12.8
- Compte Garmin avec inReach
- Compte Gmail (réception emails inReach)
- Clés API : Anthropic, Mistral, SendGrid
- Hébergement : Render.com (ou similaire)

### Installation locale

```bash
# Clone repo
git clone https://github.com/votre-repo/grib-inreach-service.git
cd grib-inreach-service

# Installer dépendances
pip install -r requirements.txt

# Installer Playwright
playwright install chromium

# Configurer variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés
```

### Déploiement Render.com

1. **Connecter GitHub repo**
2. **Configurer variables d'environnement** (voir section Configuration)
3. **Build command :** `bash build.sh`
4. **Start command :** `gunicorn main:app`

---

## ⚙️ Configuration

### Variables d'environnement requises

```bash
# Garmin InReach
GARMIN_USERNAME=votre-email@gmail.com
GARMIN_PASSWORD=votre-mot-de-passe

# API AI
ANTHROPIC_API_KEY=sk-ant-xxxxx
MISTRAL_API_KEY=xxxxx

# SendGrid (emails)
SENDGRID_API_KEY=SG.xxxxx

# Playwright (optionnel, auto-détecté)
PLAYWRIGHT_BROWSER_PATH=/usr/bin/chromium-browser
```

### Configuration avancée (config.py)

```python
# Délai entre messages (secondes)
DELAY_BETWEEN_MESSAGES = 5

# Timeout Playwright (ms)
PLAYWRIGHT_TIMEOUT = 30000

# Port Flask
PORT = 10000

# Vérification email (minutes)
CHECK_INTERVAL = 5
```

---

## 📁 Structure des fichiers

```
grib-inreach-service/
│
├── main.py                 # Flask app + orchestration
├── email_monitor.py        # Surveillance Gmail + détection
├── claude_handler.py       # API Claude (maritime/générique)
├── mistral_handler.py      # API Mistral (maritime/générique/météo)
├── grib_handler.py         # Traitement GRIB + Saildocs
├── inreach_sender.py       # Envoi messages (Playwright/POST/Email)
├── config.py               # Configuration centralisée
├── utils.py                # Fonctions utilitaires
│
├── requirements.txt        # Dépendances Python
├── runtime.txt             # Version Python (3.12.8)
├── build.sh                # Script build Playwright
│
└── README.md               # Cette documentation
```

### Détail des modules

#### main.py (Flask + orchestration)

**Rôle :** Point d'entrée, API Flask, scheduler

**Endpoints :**
- `/` → Statut service
- `/health` → Health check
- `/status` → Statut détaillé

**Fonctions principales :**
- `run_scheduled_tasks()` → Boucle vérification email (5 min)
- `app.run()` → Serveur Flask

#### email_monitor.py (v3.2.0)

**Rôle :** Surveillance Gmail, détection patterns, routage

**Fonctions principales :**
- `check_gmail()` → Connexion IMAP, lecture emails
- `detect_request_type(body)` → Détection patterns (GRIB/AI)
- `extract_reply_url(body)` → Extraction URL réponse inReach
- `process_claude_maritime_wrapper()` → Route vers Claude maritime
- `process_claude_generic_wrapper()` → Route vers Claude générique
- `process_mistral_maritime_wrapper()` → Route vers Mistral maritime
- `process_mistral_generic_wrapper()` → Route vers Mistral générique
- `process_weather_wrapper()` → Route vers météo expert
- `split_long_response()` → Découpage messages 160 chars

**Patterns détectés :**
```python
# Génériques (priorité)
r'\bcg\s+(\d+)\s*:\s*(.+)'    # Claude générique
r'\bmg\s+(\d+)\s*:\s*(.+)'    # Mistral générique

# Maritimes
r'\bc\s+(\d+)\s*:\s*(.+)'     # Claude maritime
r'\bm\s+(\d+)\s*:\s*(.+)'     # Mistral maritime
r'\bw\s+(\d+)\s*:\s*(.+)'     # Weather expert

# Compatibilité
r'\b(claude|gpt)\s+(\d+)\s*:\s*(.+)'   # Claude long
r'\bmistral\s+(\d+)\s*:\s*(.+)'        # Mistral long

# GRIB
r'(ecmwf|gfs|icon):[^\s\n]+'
```

#### claude_handler.py (v1.0)

**Rôle :** Interface API Claude (Anthropic)

**Fonctions principales :**
- `handle_claude_maritime_assistant(message)` → Claude maritime
  - System prompt spécialisé navigation
  - Max 512 tokens
  - Réponses ultra-concises
  
- `handle_claude_request(message, max_tokens)` → Claude générique
  - Pas de system prompt spécialisé
  - Tokens configurables
  - Tous sujets

- `split_long_response(text, max_length)` → Découpage intelligent

**Modèle :** `claude-sonnet-4-20250514`

**Coût :** $3/$15 per M tokens (input/output)

#### mistral_handler.py (v1.0)

**Rôle :** Interface API Mistral AI

**Fonctions principales :**
- `handle_mistral_maritime_assistant(message)` → Mistral maritime
  - System prompt navigation
  - Max 512 tokens
  - Réponses concises

- `handle_mistral_request(message, max_tokens)` → Mistral générique
  - Tokens configurables
  - Tous sujets

- `handle_mistral_weather_expert(message)` → Expert météo
  - System prompt météo marine spécialisé
  - Interprétation GRIB
  - Stratégie routage

- `split_long_response(text, max_length)` → Découpage

**Modèle :** `mistral-large-latest`

**Coût :** $2/$6 per M tokens (input/output) - **3x moins cher que Claude**

#### grib_handler.py

**Rôle :** Traitement fichiers GRIB météo

**Fonctions principales :**
- `process_grib_request(request, reply_url, mail)` → Workflow complet
  1. Envoi requête Saildocs
  2. Attente réponse (max 5 min)
  3. Extraction fichier GRIB
  4. Compression + encodage
  5. Découpage 120 chars
  6. Envoi vers inReach

- `send_to_saildocs(request)` → Envoi via SendGrid
- `wait_for_saildocs_response(mail, timeout)` → Polling IMAP
- `encode_grib_to_messages(grib_data)` → Compression zlib + base64

**Format requête Saildocs :**
```
send ecmwf:lat1,lat2,lon1,lon2|res_lat,res_lon|hours|params
```

#### inreach_sender.py (v3.2.1)

**Rôle :** Envoi messages vers inReach (multi-méthode)

**Fonctions principales :**
- `send_to_inreach(url, messages, reply_email)` → Routeur intelligent
  - Détecte type URL
  - Choisit méthode optimale
  
- `send_via_playwright_inreachlink(url, messages)` → Playwright
  - URLs inreachlink.com
  - Automatisation navigateur
  - Gestion login Garmin
  - Détection dynamique boutons Send Reply/Send Message
  
- `send_via_post_garmin(url, messages)` → POST API
  - URLs explore.garmin.com
  - Requêtes HTTP POST
  - Extraction GUID
  
- `send_via_email(reply_email, messages)` → SendGrid
  - Fallback si URLs non reconnues
  - Combine tous messages en 1 email

**Méthode préférée :** Playwright (plus fiable)

**Fallback automatique :** POST → Email si échec

#### config.py

**Rôle :** Configuration centralisée

**Variables :**
- Identifiants Garmin
- Clés API (Anthropic, Mistral, SendGrid)
- Headers HTTP inReach
- Timeouts Playwright
- Délais entre messages

#### utils.py

**Rôle :** Fonctions utilitaires partagées

**Fonctions :**
- Formatage dates
- Validation données
- Helpers divers

---

## 🔄 Flux de données

### Exemple : Requête Claude maritime

```
1. NAVIGATEUR (inReach satellite)
   └─> Envoie: "c 50: vent prévu demain?"
   
2. GARMIN
   └─> Email vers garminced@gmail.com
   
3. GMAIL (IMAP)
   └─> Email stocké (non lu)
   
4. email_monitor.py (toutes les 5 min)
   ├─> Connexion IMAP
   ├─> Lecture emails non lus
   ├─> Extraction corps: "c 50: vent prévu demain?"
   ├─> Extraction URL: https://inreachlink.com/ABC123
   └─> Détection pattern: r'\bc\s+(\d+)\s*:\s*(.+)'
       └─> Match: type='claude_maritime', question='vent prévu demain?'
       
5. process_claude_maritime_wrapper()
   └─> Appel handle_claude_maritime_assistant()
   
6. claude_handler.py
   ├─> POST https://api.anthropic.com/v1/messages
   ├─> Headers: x-api-key, anthropic-version
   ├─> Body: {
   │     model: "claude-sonnet-4-20250514",
   │     max_tokens: 150,  # 50 mots * 3
   │     system: "Tu es assistant maritime...",
   │     messages: [{role: "user", content: "vent prévu demain?"}]
   │   }
   └─> Réponse: "GRIB montre 15-20kt NE demain 10h-16h. 
                  Mer 1-1.5m. Conditions bonnes navigation."
                  
7. split_long_response()
   └─> Découpage: ["GRIB montre 15-20kt NE demain 10h-16h. 
                     Mer 1-1.5m. Conditions bonnes navigation."]
   └─> 1 message (< 160 chars)
   
8. send_to_inreach()
   └─> Détection: 'inreachlink.com' in URL
   └─> Appel send_via_playwright_inreachlink()
   
9. inreach_sender.py (Playwright)
   ├─> Launch Chromium
   ├─> Navigate https://inreachlink.com/ABC123
   ├─> Login Garmin si nécessaire
   ├─> Click "Send Reply"
   ├─> Fill textarea: "GRIB montre 15-20kt NE demain..."
   ├─> Click "Send"
   └─> Wait 3s confirmation
   
10. GARMIN
    └─> Transmission satellite vers inReach
    
11. NAVIGATEUR (inReach)
    └─> Reçoit: "GRIB montre 15-20kt NE demain 10h-16h. 
                  Mer 1-1.5m. Conditions bonnes navigation."
```

### Exemple : Requête GRIB

```
1. NAVIGATEUR
   └─> "ecmwf:0S,10S,90W,80W|1,1|0,24|WIND"
   
2-4. [Même flux Gmail → email_monitor]

5. process_grib_request()
   
6. send_to_saildocs()
   ├─> POST https://api.sendgrid.com/v3/mail/send
   └─> To: query@saildocs.com
   └─> Body: "send ecmwf:0S,10S,90W,80W|1,1|0,24|WIND"
   
7. wait_for_saildocs_response() 
   ├─> Polling IMAP toutes les 10s
   ├─> Recherche: FROM "query-reply@saildocs.com"
   └─> Timeout: 5 minutes
   
8. SAILDOCS
   └─> Email avec fichier .grb attaché (3-5 min)
   
9. extract GRIB attachment
   └─> Fichier binaire: 15 KB
   
10. encode_grib_to_messages()
    ├─> zlib.compress(grib_data, level=9)
    │   └─> 15 KB → 4 KB (compression 73%)
    ├─> base64.b64encode(compressed)
    │   └─> 4 KB → 5.3 KB (encodage +33%)
    └─> Découpage 120 chars
        └─> 45 messages
        
11. send_to_inreach()
    └─> 45 messages envoyés (délai 5s entre chaque)
    └─> Durée totale: ~4 minutes
    
12. NAVIGATEUR
    └─> Reçoit 45 messages
    └─> Décodage base64 + décompression zlib
    └─> Fichier GRIB reconstitué: 15 KB
```

---

## 💰 API et coûts

### Claude (Anthropic)

**Modèle :** `claude-sonnet-4-20250514`

**Tarifs :**
- Input : $3 / M tokens
- Output : $15 / M tokens

**Estimation requête 50 mots :**
- Input : ~100 tokens (system + question)
- Output : ~150 tokens (50 mots * 3)
- Coût : ~$0.0025 (0.25 centime)

**Avantages :**
- Qualité exceptionnelle
- Raisonnement approfondi
- Excellent en français

### Mistral

**Modèle :** `mistral-large-latest`

**Tarifs :**
- Input : $2 / M tokens
- Output : $6 / M tokens

**Estimation requête 50 mots :**
- Input : ~100 tokens
- Output : ~150 tokens
- Coût : ~$0.0011 (0.11 centime)

**Avantages :**
- **3x moins cher que Claude**
- Très bon en français
- Excellent rapport qualité/prix

### SendGrid (emails)

**Plan gratuit :** 100 emails/jour

**Utilisation :**
- Envoi requêtes Saildocs : ~1-5/jour
- Fallback inReach : rare

### Coûts satellite inReach

**Variables selon abonnement Garmin**

**Messages reçus :** Généralement illimités

**Messages envoyés :**
- Plan Safety : 10/mois inclus
- Plan Recreation : 40/mois inclus  
- Plan Expedition : Illimités

**Recommandations :**
- Utiliser patterns courts (économie caractères)
- Limiter nombre de mots (moins de messages)
- Claude/Mistral : ~$0.001-0.003 par requête
- GRIB : 0 coût API (Saildocs gratuit)

---

## 🚢 Déploiement

### Render.com (recommandé)

**Avantages :**
- Gratuit (plan Hobby)
- Support Playwright
- Auto-redémarrage
- Logs détaillés

**Configuration :**

1. **Connecter repo GitHub**

2. **Settings :**
   - Environment : Python 3
   - Build Command : `bash build.sh`
   - Start Command : `gunicorn main:app`

3. **Environment Variables :**
   ```
   GARMIN_USERNAME=xxx
   GARMIN_PASSWORD=xxx
   ANTHROPIC_API_KEY=xxx
   MISTRAL_API_KEY=xxx
   SENDGRID_API_KEY=xxx
   PORT=10000
   ```

4. **Deploy**

### Railway.app (alternative)

Même configuration que Render.

### Heroku (alternative)

Ajouter `Procfile` :
```
web: gunicorn main:app
```

---

## 🔧 Dépannage

### Service ne démarre pas

**Symptôme :** Erreur au démarrage

**Solutions :**
1. Vérifier variables d'environnement
2. Vérifier `requirements.txt` installé
3. Vérifier `build.sh` exécuté (Playwright)
4. Consulter logs Render

### Emails non détectés

**Symptôme :** Pas de réponse aux messages inReach

**Solutions :**
1. Vérifier Gmail IMAP activé
2. Vérifier GARMIN_USERNAME = email correct
3. Vérifier email arrive bien dans Gmail
4. Consulter logs : "📧 EMAIL TROUVÉ"
5. Vérifier pattern détecté : "✅ Requête détectée"

### Pattern non reconnu

**Symptôme :** "❌ Aucun pattern reconnu"

**Solutions :**
1. Vérifier format exact :
   - `c 150: question` ✅
   - `c150: question` ❌ (manque espace)
   - `c 150 question` ❌ (manque `:`)
   
2. Vérifier majuscules acceptées :
   - `C 150: question` ✅
   - `CLAUDE 150: question` ✅

3. Consulter logs détection pour voir ce qui a été testé

### Envoi échoue

**Symptôme :** "❌ Échec envoi messages"

**Solutions :**

**Playwright :**
1. Vérifier Chromium installé : `playwright install chromium`
2. Vérifier timeout suffisant (30s)
3. Consulter logs Playwright détaillés
4. Vérifier login Garmin OK

**POST API :**
1. Vérifier URL contient `extId` parameter
2. Vérifier headers HTTP corrects

**Email :**
1. Vérifier SENDGRID_API_KEY
2. Vérifier quota SendGrid (100/jour gratuit)

### Claude/Mistral erreurs

**Symptôme :** "❌ Erreur API Claude/Mistral"

**Solutions :**
1. Vérifier clés API valides
2. Vérifier quota API non dépassé
3. Vérifier connexion internet serveur
4. Consulter message erreur détaillé

### GRIB timeout

**Symptôme :** "⏱️ Timeout atteint (300s)"

**Solutions :**
1. Saildocs peut être lent (pic heures)
2. Augmenter timeout si nécessaire
3. Vérifier format requête GRIB correct
4. Vérifier SendGrid email bien envoyé

---

## 📊 Monitoring

### Endpoints disponibles

**Health check :**
```bash
curl https://votre-service.onrender.com/health
```

**Statut détaillé :**
```bash
curl https://votre-service.onrender.com/status
```

**Réponse exemple :**
```json
{
  "service": "GRIB InReach Service with Multi-AI v3.2",
  "status": "running",
  "last_check_time": "2025-12-22 16:45:30",
  "anthropic_configured": "✓ Oui",
  "mistral_configured": "✓ Oui",
  "features": {
    "grib": "Format: ecmwf:...",
    "claude_maritime": "c 150: question",
    "claude_generic": "cg 150: question",
    "mistral_maritime": "m 150: question",
    "mistral_generic": "mg 150: question",
    "weather": "w 150: question"
  }
}
```

### Logs importants

**Vérification email :**
```
🔄 VÉRIFICATION EMAIL - 2025-12-22 16:45:30
📬 3 email(s) non lu(s) trouvé(s)
```

**Détection réussie :**
```
✅ CLAUDE MARITIME détecté (c)
   Max tokens: 450
   Question: vent prévu demain?
```

**Envoi réussi :**
```
✅✅✅ SUCCÈS
```

---

## 🤝 Contribution

Améliorations bienvenues :
- Nouveaux patterns de détection
- Support autres providers AI
- Optimisations compression GRIB
- Tests unitaires

---

## 📝 Changelog

### v3.2.0 (2025-12-22)
- ✨ Ajout patterns courts : `c`, `m`, `w`, `cg`, `mg`
- ✨ Distinction maritimes vs génériques
- ✨ Expert météo Mistral dédié
- 📝 Documentation complète README

### v3.1.1 (2025-12-21)
- 🐛 Fix import `send_to_inreach` (était `send_messages_to_inreach`)
- ✅ Tests validation intégration

### v3.1.0 (2025-12-21)
- ✨ Intégration Claude + Mistral handlers
- ✨ Détection patterns flexibles
- ✨ Support requêtes avec/sans question

### v3.0.0 (2025-12-20)
- 🏗️ Migration architecture modulaire
- 📦 9 fichiers séparés (vs monolithique)
- ✨ Playwright + POST + Email multi-méthode
- 🔧 Config centralisée

### v2.2.0 (2025-12-15)
- ✨ Playwright automatisation navigateur
- 🐛 Fix URL Garmin formats multiples

### v1.0.0 (2025-12-01)
- 🎉 Version initiale GRIB seulement

---

## 📞 Support

**Questions :** Créer une issue GitHub

**Bugs :** Fournir logs complets + message envoyé

---

## 📜 Licence

Usage personnel - Cédric © 2025

---

**Bon vent ! ⛵**
