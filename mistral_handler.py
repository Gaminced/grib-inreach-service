# mistral_handler.py - v1.3
"""
Handler pour API Mistral AI
Compatible avec architecture modulaire email_monitor v3.2.2

v1.3:
- Découpage optimisé pour messages 100-120 chars (meilleur remplissage)
- Affichage coût + solde dans dernier message
- Fusion agressive messages courts
- Nettoyage automatique LaTeX/formules mathématiques
"""

import os
import re
import requests
from typing import Optional, Tuple


# Suivi du solde Mistral (initialisé à $5.00 par défaut)
MISTRAL_BALANCE = float(os.getenv('MISTRAL_BALANCE', '5.00'))


def handle_mistral_maritime_assistant(user_message: str) -> Tuple[str, float]:
    """
    Assistant maritime spécialisé avec Mistral
    Optimisé pour questions nautiques, météo, navigation
    
    Args:
        user_message: Question de l'utilisateur
        
    Returns:
        Tuple (réponse, coût) - Réponse de Mistral + coût de la requête
    """
    api_key = os.getenv('MISTRAL_API_KEY')
    
    if not api_key:
        return ("❌ MISTRAL_API_KEY non configurée", 0.0)
    
    try:
        print(f"\n{'='*70}")
        print("🧠 MISTRAL MARITIME ASSISTANT")
        print(f"{'='*70}")
        print(f"Question: {user_message[:100]}...")
        
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = """Tu es un assistant maritime expert pour navigateurs en mer.

Contexte:
- Utilisateur en mer sur voilier
- Communication satellite limitée et coûteuse
- Besoin réponses ULTRA-CONCISES

Expertise:
- Météorologie marine
- Navigation hauturière
- Sécurité maritime
- Mécanique marine
- Protocoles d'urgence
- Interprétation fichiers GRIB

RÈGLES STRICTES:
- MAX 120 caractères par réponse
- Info essentielle UNIQUEMENT
- Vocabulaire maritime précis
- Conseils pratiques directs
- Pas de fioriture
- TEXTE BRUT (pas de LaTeX, pas de formules mathématiques)

Questions hors maritime: décliner poliment."""
        
        data = {
            "model": "mistral-large-latest",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "max_tokens": 512,
            "temperature": 0.7
        }
        
        print("📤 Envoi requête API Mistral...")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            answer = result['choices'][0]['message']['content'].strip()
            
            # NETTOYAGE LaTeX
            answer = clean_latex(answer)
            
            # Infos usage
            usage = result.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            
            # Calcul coût (Mistral Large: $2/$6 per M tokens)
            input_cost = (input_tokens / 1_000_000) * 2.0
            output_cost = (output_tokens / 1_000_000) * 6.0
            total_cost = input_cost + output_cost
            
            print(f"✅ Réponse Mistral reçue: {len(answer)} chars")
            print(f"📊 Tokens: {input_tokens} in + {output_tokens} out")
            print(f"💰 Coût: ${total_cost:.6f}")
            print(f"{'='*70}\n")
            
            return (answer, total_cost)
            
        else:
            error_msg = f"❌ Erreur API Mistral: {response.status_code}"
            print(error_msg)
            print(f"Réponse: {response.text[:200]}")
            return (f"Erreur Mistral: {response.status_code}", 0.0)
            
    except Exception as e:
        error_msg = f"❌ Erreur Mistral: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return (f"Erreur: {str(e)[:100]}", 0.0)


def handle_mistral_request(user_message: str, max_tokens: int = 1024) -> Tuple[str, float]:
    """
    Requête Mistral générique (non spécialisée maritime)
    
    Args:
        user_message: Message utilisateur
        max_tokens: Limite de tokens (défaut: 1024)
        
    Returns:
        Tuple (réponse, coût) - Réponse de Mistral + coût de la requête
    """
    api_key = os.getenv('MISTRAL_API_KEY')
    
    if not api_key:
        return ("❌ MISTRAL_API_KEY non configurée", 0.0)
    
    try:
        print(f"\n{'='*70}")
        print("🧠 MISTRAL REQUEST")
        print(f"{'='*70}")
        print(f"Message: {user_message[:100]}...")
        print(f"Max tokens: {max_tokens}")
        
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # System prompt pour TEXTE BRUT
        system_prompt = """Tu es un assistant intelligent et concis.

RÈGLES STRICTES DE FORMATAGE:
- TEXTE BRUT UNIQUEMENT
- PAS de LaTeX (\\text{}, \\rightarrow, etc.)
- PAS de notation mathématique complexe (^, _, subscript, superscript)
- Formules chimiques: écris "Fe2+" au lieu de "Fe^{2+}"
- Flèches: utilise "->" au lieu de "\\rightarrow"
- Équations: écris "H2O" au lieu de "H_2O"
- Exposants: écris "m2" au lieu de "m^2"

Reste précis et informatif, mais en texte simple lisible sur tout appareil."""
        
        data = {
            "model": "mistral-large-latest",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        print("📤 Envoi requête API Mistral...")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            answer = result['choices'][0]['message']['content'].strip()
            
            # NETTOYAGE LaTeX (sécurité)
            answer = clean_latex(answer)
            
            usage = result.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            
            input_cost = (input_tokens / 1_000_000) * 2.0
            output_cost = (output_tokens / 1_000_000) * 6.0
            total_cost = input_cost + output_cost
            
            print(f"✅ Réponse: {len(answer)} chars")
            print(f"📊 Tokens: {input_tokens}/{output_tokens}")
            print(f"💰 Coût: ${total_cost:.6f}")
            print(f"{'='*70}\n")
            
            return (answer, total_cost)
            
        else:
            error_msg = f"❌ Erreur API: {response.status_code}"
            print(error_msg)
            return (f"Erreur Mistral: {response.status_code}", 0.0)
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return (f"Erreur: {str(e)[:100]}", 0.0)


def handle_mistral_weather_expert(user_message: str) -> Tuple[str, float]:
    """
    Expert météo marine spécialisé avec Mistral
    
    Args:
        user_message: Question météo
        
    Returns:
        Tuple (réponse, coût) - Analyse météo de Mistral + coût de la requête
    """
    api_key = os.getenv('MISTRAL_API_KEY')
    
    if not api_key:
        return ("❌ MISTRAL_API_KEY non configurée", 0.0)
    
    try:
        print(f"\n{'='*70}")
        print("🌊 MISTRAL WEATHER EXPERT")
        print(f"{'='*70}")
        print(f"Question: {user_message[:100]}...")
        
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = """Expert météorologie marine pour navigation hauturière.

Spécialités:
- Interprétation GRIB (vent, vagues, pression)
- Prévisions route océanique
- Fenêtres météo favorables
- Systèmes dépressionnaires
- Stratégie routage

Format réponse:
- Synthèse conditions (2-3 lignes max)
- Recommandation cap/timing
- Alertes si danger
- CONCIS et ACTIONNABLE
- TEXTE BRUT (pas de LaTeX)

Unités: nœuds, mbar, degrés vrais."""
        
        data = {
            "model": "mistral-large-latest",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "max_tokens": 512,
            "temperature": 0.7
        }
        
        print("📤 Envoi requête API Mistral Weather...")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            answer = result['choices'][0]['message']['content'].strip()
            
            # NETTOYAGE LaTeX
            answer = clean_latex(answer)
            
            usage = result.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            
            input_cost = (input_tokens / 1_000_000) * 2.0
            output_cost = (output_tokens / 1_000_000) * 6.0
            total_cost = input_cost + output_cost
            
            print(f"✅ Réponse Weather: {len(answer)} chars")
            print(f"📊 Tokens: {input_tokens}/{output_tokens}")
            print(f"💰 Coût: ${total_cost:.6f}")
            print(f"{'='*70}\n")
            
            return (answer, total_cost)
            
        else:
            error_msg = f"❌ Erreur API: {response.status_code}"
            print(error_msg)
            return (f"Erreur Mistral Weather: {response.status_code}", 0.0)
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return (f"Erreur: {str(e)[:100]}", 0.0)


def clean_latex(text: str) -> str:
    """
    Nettoie le texte des notations LaTeX et formules mathématiques
    
    Args:
        text: Texte potentiellement avec LaTeX
        
    Returns:
        Texte nettoyé en texte brut
    """
    # Supprimer \text{...}
    text = re.sub(r'\\text\{([^}]+)\}', r'\1', text)
    
    # Remplacer flèches
    text = text.replace(r'\rightarrow', '->')
    text = text.replace(r'\leftarrow', '<-')
    text = text.replace(r'\leftrightarrow', '<->')
    
    # Supprimer exposants/indices LaTeX: X^{n} -> Xn, X_{n} -> Xn
    text = re.sub(r'\^\\?\{([^}]+)\}', r'\1', text)
    text = re.sub(r'_\\?\{([^}]+)\}', r'\1', text)
    
    # Exposants simples: X^n -> Xn
    text = re.sub(r'\^(\w)', r'\1', text)
    text = re.sub(r'_(\w)', r'\1', text)
    
    # Supprimer autres commandes LaTeX courantes
    replacements = {
        r'\\cdot': '*',
        r'\\times': 'x',
        r'\\pm': '+/-',
        r'\\div': '/',
        r'\\infty': 'infini',
        r'\\approx': '≈',
        r'\\equiv': '=',
        r'\\neq': '≠',
        r'\\le': '≤',
        r'\\ge': '≥',
        r'\\ll': '<<',
        r'\\gg': '>>',
    }
    
    for cmd, repl in replacements.items():
        text = text.replace(cmd, repl)
    
    # Supprimer $...$ (inline math)
    text = re.sub(r'\$([^$]+)\$', r'\1', text)
    
    # Supprimer $$...$$ (display math)
    text = re.sub(r'\$\$([^$]+)\$\$', r'\1', text)
    
    # Nettoyer espaces multiples
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def split_long_response(response: str, cost: float = 0.0, max_length: int = 120) -> list:
    """
    Découpe une réponse longue en messages inReach (120 chars optimal)
    Avec numérotation correcte [1/N], [2/N]... [N/N]
    NOUVEAU: Coût + solde dans dernier message
    
    OPTIMISATION v1.3:
    - Objectif: messages 100-120 chars (meilleur remplissage)
    - Fusion agressive messages courts
    - Dernier message: "Coût: $X.XXXX | Solde: $Y.YY"
    
    Args:
        response: Texte à découper
        cost: Coût de la requête (pour affichage final)
        max_length: Longueur max par message (défaut: 120)
        
    Returns:
        Liste de messages découpés et numérotés avec coût
    """
    global MISTRAL_BALANCE
    
    # Si assez court, retourner avec coût
    if len(response) <= max_length - 35:  # Réserver 35 chars pour coût
        MISTRAL_BALANCE -= cost
        balance_str = f" | Coût: ${cost:.4f} | Solde: ${MISTRAL_BALANCE:.2f}"
        if len(response + balance_str) <= max_length:
            return [response + balance_str]
        else:
            # Séparer en 2 messages
            return [response, f"Coût: ${cost:.4f} | Solde: ${MISTRAL_BALANCE:.2f}"]
    
    print(f"\n{'='*70}")
    print(f"✂️  DÉCOUPAGE OPTIMISÉ (objectif 100-120 chars)")
    print(f"{'='*70}")
    print(f"Texte original: {len(response)} chars\n")
    
    # Réserver 8 chars pour numérotation "[99/99] "
    usable_length = max_length - 8
    
    # Objectif: messages entre 100-120 chars (bon remplissage)
    target_length = 100
    
    # Découpage par phrases
    sentences = re.split(r'([.!?]\s+)', response)
    
    messages = []
    current_msg = ""
    
    for i in range(0, len(sentences), 2):
        sentence = sentences[i]
        if i + 1 < len(sentences):
            sentence += sentences[i + 1]
        
        test_msg = current_msg + sentence if current_msg else sentence
        
        # Stratégie: remplir jusqu'à target_length (100 chars)
        if len(test_msg) <= usable_length:
            current_msg = test_msg
            # Si on dépasse 100 chars ET il reste des phrases, on coupe
            if len(current_msg) >= target_length and i + 2 < len(sentences):
                messages.append(current_msg.strip())
                current_msg = ""
        else:
            if current_msg:
                messages.append(current_msg.strip())
            
            # Phrase trop longue -> découper par mots
            if len(sentence) > usable_length:
                words = sentence.split()
                temp_msg = ""
                for word in words:
                    test = temp_msg + " " + word if temp_msg else word
                    if len(test) <= usable_length:
                        temp_msg = test
                    else:
                        if temp_msg:
                            messages.append(temp_msg.strip())
                        temp_msg = word
                current_msg = temp_msg
            else:
                current_msg = sentence
    
    if current_msg.strip():
        messages.append(current_msg.strip())
    
    # FUSION AGRESSIVE messages courts (< 50 chars)
    optimized = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        
        # Essayer de fusionner avec suivants si trop court
        while len(msg) < 50 and i + 1 < len(messages):
            combined = msg + " " + messages[i + 1]
            if len(combined) <= usable_length:
                msg = combined
                i += 1
                print(f"🔗 Fusion: {len(msg)} chars")
            else:
                break
        
        optimized.append(msg)
        i += 1
    
    messages = optimized
    
    # AJOUTER NUMÉROTATION
    total = len(messages)
    numbered_messages = []
    
    print(f"📊 Total: {total} message(s)\n")
    
    for i, msg in enumerate(messages, 1):
        prefix = f"[{i}/{total}] "
        
        # Dernier message: ajouter coût + solde
        if i == total:
            MISTRAL_BALANCE -= cost
            suffix = f" | Coût: ${cost:.4f} | Solde: ${MISTRAL_BALANCE:.2f}"
            
            # Vérifier si ça tient
            numbered = prefix + msg + suffix
            if len(numbered) <= max_length:
                numbered_messages.append(numbered)
                print(f"✅ [{i}/{total}] {len(numbered)} chars (avec coût): {numbered[:60]}...")
            else:
                # Tronquer message pour faire tenir le coût
                available = max_length - len(prefix) - len(suffix) - 3
                if available > 20:
                    msg = msg[:available] + "..."
                    numbered = prefix + msg + suffix
                    numbered_messages.append(numbered)
                    print(f"⚠️  [{i}/{total}] tronqué pour coût: {len(numbered)} chars")
                else:
                    # Impossible de tout mettre, séparer
                    numbered_messages.append(prefix + msg)
                    numbered_messages.append(f"[{total+1}/{total+1}] Coût: ${cost:.4f} | Solde: ${MISTRAL_BALANCE:.2f}")
                    print(f"⚠️  Coût séparé en message additionnel")
        else:
            numbered = prefix + msg
            
            if len(numbered) > max_length:
                available = max_length - len(prefix) - 3
                msg = msg[:available] + "..."
                numbered = prefix + msg
                print(f"⚠️  Msg {i}/{total} tronqué: {len(numbered)} chars")
            
            numbered_messages.append(numbered)
            print(f"✅ [{i}/{total}] {len(numbered)} chars: {numbered[:60]}...")
    
    # Limite sécurité
    if len(numbered_messages) > 15:
        print(f"\n⚠️  Limitation à 15 messages")
        numbered_messages = numbered_messages[:15]
    
    print(f"\n{'='*70}")
    print(f"✅ DÉCOUPAGE TERMINÉ: {len(numbered_messages)} messages")
    print(f"💰 Coût requête: ${cost:.4f}")
    print(f"💳 Solde restant: ${MISTRAL_BALANCE:.2f}")
    print(f"{'='*70}\n")
    
    return numbered_messages


# Test du module
if __name__ == "__main__":
    print("="*70)
    print("TEST MISTRAL HANDLER v1.3")
    print("="*70)
    
    # Test découpage avec coût
    print("\n📝 Test: Découpage optimisé avec coût")
    print("-"*70)
    
    long_text = """Pour prévenir la corrosion de l'inox marin, rincez régulièrement à l'eau douce pour éliminer le sel. Appliquez une couche de cire protectrice ou d'huile sur les pièces exposées. Évitez le contact avec des métaux différents qui causent une corrosion galvanique. Inspectez et nettoyez les zones difficiles d'accès mensuellement."""
    
    messages = split_long_response(long_text, cost=0.0015, max_length=120)
    
    print(f"\nTexte: {len(long_text)} chars")
    print(f"Messages: {len(messages)}")
    print(f"\nRésultat:")
    for msg in messages:
        print(f"  [{len(msg)} chars] {msg}")
    
    print("\n" + "="*70)
