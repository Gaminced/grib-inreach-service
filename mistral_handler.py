# mistral_handler.py - v1.2
"""
Handler pour API Mistral AI
Compatible avec architecture modulaire email_monitor v3.2.2

v1.2:
- Découpage optimisé 120 caractères (inReach optimal)
- Numérotation correcte [1/N], [2/N]... [N/N]
- Messages équilibrés (pas de message < 30 chars)
- Nettoyage automatique LaTeX/formules mathématiques
"""

import os
import re
import requests
from typing import Optional


def handle_mistral_maritime_assistant(user_message: str) -> str:
    """
    Assistant maritime spécialisé avec Mistral
    Optimisé pour questions nautiques, météo, navigation
    
    Args:
        user_message: Question de l'utilisateur
        
    Returns:
        Réponse de Mistral (texte brut, nettoyé)
    """
    api_key = os.getenv('MISTRAL_API_KEY')
    
    if not api_key:
        return "❌ MISTRAL_API_KEY non configurée"
    
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
            
            return answer
            
        else:
            error_msg = f"❌ Erreur API Mistral: {response.status_code}"
            print(error_msg)
            print(f"Réponse: {response.text[:200]}")
            return f"Erreur Mistral: {response.status_code}"
            
    except Exception as e:
        error_msg = f"❌ Erreur Mistral: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return f"Erreur: {str(e)[:100]}"


def handle_mistral_request(user_message: str, max_tokens: int = 1024) -> str:
    """
    Requête Mistral générique (non spécialisée maritime)
    
    Args:
        user_message: Message utilisateur
        max_tokens: Limite de tokens (défaut: 1024)
        
    Returns:
        Réponse de Mistral (texte brut, nettoyé)
    """
    api_key = os.getenv('MISTRAL_API_KEY')
    
    if not api_key:
        return "❌ MISTRAL_API_KEY non configurée"
    
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
            
            return answer
            
        else:
            error_msg = f"❌ Erreur API: {response.status_code}"
            print(error_msg)
            return f"Erreur Mistral: {response.status_code}"
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return f"Erreur: {str(e)[:100]}"


def handle_mistral_weather_expert(user_message: str) -> str:
    """
    Expert météo marine spécialisé avec Mistral
    
    Args:
        user_message: Question météo
        
    Returns:
        Analyse météo de Mistral (texte brut, nettoyé)
    """
    api_key = os.getenv('MISTRAL_API_KEY')
    
    if not api_key:
        return "❌ MISTRAL_API_KEY non configurée"
    
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
            
            return answer
            
        else:
            error_msg = f"❌ Erreur API: {response.status_code}"
            print(error_msg)
            return f"Erreur Mistral Weather: {response.status_code}"
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return f"Erreur: {str(e)[:100]}"


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


def split_long_response(response: str, max_length: int = 120) -> list:
    """
    Découpe une réponse longue en messages inReach (120 chars optimal)
    Avec numérotation correcte [1/N], [2/N]... [N/N]
    
    OPTIMISATION INREACH:
    - 120 chars = taille optimale réception inReach
    - Réserver 8 chars pour "[99/99] "
    - Messages équilibrés (pas < 30 chars)
    
    Args:
        response: Texte à découper
        max_length: Longueur max par message (défaut: 120)
        
    Returns:
        Liste de messages découpés et numérotés [1/N], [2/N]...
    """
    # Si assez court, retourner tel quel
    if len(response) <= max_length:
        return [response]
    
    print(f"\n{'='*70}")
    print(f"✂️  DÉCOUPAGE MESSAGES (max {max_length} chars)")
    print(f"{'='*70}")
    print(f"Texte original: {len(response)} chars\n")
    
    # Réserver 8 chars pour numérotation "[99/99] "
    usable_length = max_length - 8
    
    # Découpage par phrases pour meilleure lisibilité
    sentences = re.split(r'([.!?]\s+)', response)
    
    messages = []
    current_msg = ""
    
    for i in range(0, len(sentences), 2):
        sentence = sentences[i]
        if i + 1 < len(sentences):
            sentence += sentences[i + 1]  # Ajouter ponctuation
        
        # Test si on peut ajouter cette phrase
        test_msg = current_msg + sentence if current_msg else sentence
        
        if len(test_msg) <= usable_length:
            current_msg = test_msg
        else:
            # Message actuel est plein
            if current_msg:
                messages.append(current_msg.strip())
            
            # Si phrase trop longue, découper par mots
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
    
    # Ajouter dernier message
    if current_msg.strip():
        messages.append(current_msg.strip())
    
    # FUSION messages trop courts (< 30 chars)
    cleaned_messages = []
    for i, msg in enumerate(messages):
        if len(msg) < 30 and cleaned_messages:
            # Fusionner avec précédent si ça tient
            last = cleaned_messages[-1]
            combined = last + " " + msg
            if len(combined) <= usable_length:
                cleaned_messages[-1] = combined
                print(f"🔗 Fusion msg court ({len(msg)} chars) avec précédent")
            else:
                cleaned_messages.append(msg)
        else:
            cleaned_messages.append(msg)
    
    messages = cleaned_messages
    
    # AJOUTER NUMÉROTATION [1/N], [2/N]... [N/N]
    total = len(messages)
    numbered_messages = []
    
    print(f"📊 Total: {total} message(s)\n")
    
    for i, msg in enumerate(messages, 1):
        prefix = f"[{i}/{total}] "
        numbered = prefix + msg
        
        # Vérifier longueur finale
        if len(numbered) > max_length:
            # Tronquer le message pour respecter limite
            available = max_length - len(prefix) - 3  # -3 pour "..."
            msg = msg[:available] + "..."
            numbered = prefix + msg
            print(f"⚠️  Msg {i}/{total} tronqué: {len(numbered)} chars")
        
        numbered_messages.append(numbered)
        print(f"✅ [{i}/{total}] {len(numbered)} chars: {numbered[:50]}...")
    
    # Sécurité: si > 15 messages, limiter
    if len(numbered_messages) > 15:
        print(f"\n⚠️  Réponse trop longue ({len(numbered_messages)} msgs), limitation à 15")
        numbered_messages = numbered_messages[:15]
        # Mettre à jour numérotation
        numbered_messages = []
        for i, msg in enumerate(messages[:15], 1):
            prefix = f"[{i}/15] "
            numbered = prefix + msg
            if len(numbered) > max_length:
                available = max_length - len(prefix) - 3
                msg = msg[:available] + "..."
                numbered = prefix + msg
            numbered_messages.append(numbered)
    
    print(f"\n{'='*70}")
    print(f"✅ DÉCOUPAGE TERMINÉ: {len(numbered_messages)} messages")
    print(f"{'='*70}\n")
    
    return numbered_messages


# Test du module
if __name__ == "__main__":
    print("="*70)
    print("TEST MISTRAL HANDLER v1.2")
    print("="*70)
    
    # Test 1: Nettoyage LaTeX
    print("\n📝 Test 1: Nettoyage LaTeX")
    print("-"*70)
    latex_text = r"La corrosion de l'acier (Fe) est une réaction électrochimique : \[ 4\text{Fe} + 3\text{O}_2 + 6\text{H}_2\text{O} \rightarrow 4\text{Fe(OH)}_3 \]"
    cleaned = clean_latex(latex_text)
    print(f"Original: {latex_text}")
    print(f"Nettoyé: {cleaned}\n")
    
    # Test 2: Découpage 120 chars avec numérotation correcte
    print("\n📝 Test 2: Découpage 120 chars")
    print("-"*70)
    long_text = """Pour prévenir la corrosion de l'inox marin, rincez régulièrement à l'eau douce pour éliminer le sel. Appliquez une couche de cire protectrice ou d'huile sur les pièces exposées. Évitez le contact avec des métaux différents qui causent une corrosion galvanique. Inspectez et nettoyez les zones difficiles d'accès mensuellement. Utilisez des produits anti-corrosion marins spécialisés pour protection longue durée."""
    
    messages = split_long_response(long_text, max_length=120)
    print(f"\nTexte original: {len(long_text)} chars")
    print(f"Découpé en: {len(messages)} messages")
    print(f"\nMessages finaux:")
    for msg in messages:
        print(f"  {msg}")
    
    print("\n" + "="*70)
    print("TESTS TERMINÉS")
    print("="*70)
