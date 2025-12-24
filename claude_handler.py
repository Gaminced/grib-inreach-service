# claude_handler.py - v1.1
"""
Handler pour API Claude (Anthropic)
Compatible avec architecture modulaire email_monitor v3.2.1

v1.1: 
- Nettoyage automatique LaTeX/formules mathématiques
- Découpage messages intelligent avec numérotation équilibrée
- Pas de messages < 20 chars
"""

import os
import re
import requests
from typing import Optional


def handle_claude_maritime_assistant(user_message: str) -> str:
    """
    Assistant maritime spécialisé avec Claude
    Optimisé pour questions nautiques, météo, navigation
    
    Args:
        user_message: Question de l'utilisateur
        
    Returns:
        Réponse de Claude (texte brut, nettoyé)
    """
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        return "❌ ANTHROPIC_API_KEY non configurée"
    
    try:
        print(f"\n{'='*70}")
        print("🤖 CLAUDE MARITIME ASSISTANT")
        print(f"{'='*70}")
        print(f"Question: {user_message[:100]}...")
        
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        system_prompt = """Tu es un assistant maritime expert spécialisé pour les navigateurs en mer.

Contexte:
- L'utilisateur est en mer sur un voilier
- Communications par satellite inReach (coûteuses, limitées)
- Besoin de réponses CONCISES et PRÉCISES

Domaines d'expertise:
- Météo marine et interprétation GRIB
- Navigation hauturière
- Sécurité en mer
- Manœuvres et gestion du bateau
- Mécanique marine de base
- Protocoles d'urgence

IMPÉRATIF:
- Réponses COURTES (max 160 caractères si possible)
- Information essentielle UNIQUEMENT
- Pas de bavardage
- Vocabulaire maritime précis
- Conseils pratiques et actionnables
- TEXTE BRUT uniquement (pas de LaTeX, pas de formules mathématiques)

Si question hors contexte maritime: répondre brièvement que tu es spécialisé en navigation."""
        
        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 512,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "temperature": 0.7
        }
        
        print("📤 Envoi requête API Claude...")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            answer = result['content'][0]['text'].strip()
            
            # NETTOYAGE LaTeX
            answer = clean_latex(answer)
            
            # Infos usage
            usage = result.get('usage', {})
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            
            # Calcul coût (Claude Sonnet 4.5: $3/$15 per M tokens)
            input_cost = (input_tokens / 1_000_000) * 3.0
            output_cost = (output_tokens / 1_000_000) * 15.0
            total_cost = input_cost + output_cost
            
            print(f"✅ Réponse Claude reçue: {len(answer)} chars")
            print(f"📊 Tokens: {input_tokens} in + {output_tokens} out")
            print(f"💰 Coût: ${total_cost:.6f}")
            print(f"{'='*70}\n")
            
            return answer
            
        else:
            error_msg = f"❌ Erreur API Claude: {response.status_code}"
            print(error_msg)
            print(f"Réponse: {response.text[:200]}")
            return f"Erreur Claude: {response.status_code}"
            
    except Exception as e:
        error_msg = f"❌ Erreur Claude: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return f"Erreur: {str(e)[:100]}"


def handle_claude_request(user_message: str, max_tokens: int = 1024) -> str:
    """
    Requête Claude générique (non spécialisée maritime)
    
    Args:
        user_message: Message utilisateur
        max_tokens: Limite de tokens (défaut: 1024)
        
    Returns:
        Réponse de Claude (texte brut, nettoyé)
    """
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        return "❌ ANTHROPIC_API_KEY non configurée"
    
    try:
        print(f"\n{'='*70}")
        print("🤖 CLAUDE REQUEST")
        print(f"{'='*70}")
        print(f"Message: {user_message[:100]}...")
        print(f"Max tokens: {max_tokens}")
        
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
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
            "model": "claude-sonnet-4-20250514",
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "temperature": 0.7
        }
        
        print("📤 Envoi requête API Claude...")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            answer = result['content'][0]['text'].strip()
            
            # NETTOYAGE LaTeX (sécurité au cas où)
            answer = clean_latex(answer)
            
            usage = result.get('usage', {})
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            
            input_cost = (input_tokens / 1_000_000) * 3.0
            output_cost = (output_tokens / 1_000_000) * 15.0
            total_cost = input_cost + output_cost
            
            print(f"✅ Réponse: {len(answer)} chars")
            print(f"📊 Tokens: {input_tokens}/{output_tokens}")
            print(f"💰 Coût: ${total_cost:.6f}")
            print(f"{'='*70}\n")
            
            return answer
            
        else:
            error_msg = f"❌ Erreur API: {response.status_code}"
            print(error_msg)
            return f"Erreur Claude: {response.status_code}"
            
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
    latex_commands = [
        r'\\cdot', r'\\times', r'\\pm', r'\\div',
        r'\\infty', r'\\approx', r'\\equiv', r'\\neq',
        r'\\le', r'\\ge', r'\\ll', r'\\gg',
        r'\\alpha', r'\\beta', r'\\gamma', r'\\delta',
        r'\\pi', r'\\theta', r'\\lambda', r'\\mu',
        r'\\sum', r'\\int', r'\\partial', r'\\nabla'
    ]
    
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
    
    # Supprimer commandes LaTeX restantes
    for cmd in latex_commands:
        text = text.replace(cmd, '')
    
    # Supprimer $...$ (inline math)
    text = re.sub(r'\$([^$]+)\$', r'\1', text)
    
    # Supprimer $$...$$ (display math)
    text = re.sub(r'\$\$([^$]+)\$\$', r'\1', text)
    
    # Nettoyer espaces multiples
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def split_long_response(response: str, max_length: int = 160) -> list:
    """
    Découpe une réponse longue en messages inReach (max 160 chars)
    Avec numérotation intelligente [1/N] et messages équilibrés
    
    Args:
        response: Texte à découper
        max_length: Longueur max par message (défaut: 160)
        
    Returns:
        Liste de messages découpés et numérotés
    """
    # Si assez court, retourner tel quel
    if len(response) <= max_length:
        return [response]
    
    # Estimer nombre de messages nécessaires
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
    
    # Vérifier pas de messages trop courts (< 20 chars)
    # Les fusionner avec le précédent si possible
    cleaned_messages = []
    for i, msg in enumerate(messages):
        if len(msg) < 20 and cleaned_messages:
            # Fusionner avec précédent si ça tient
            last = cleaned_messages[-1]
            combined = last + " " + msg
            if len(combined) <= usable_length:
                cleaned_messages[-1] = combined
            else:
                cleaned_messages.append(msg)
        else:
            cleaned_messages.append(msg)
    
    messages = cleaned_messages
    
    # Ajouter numérotation [1/N], [2/N], etc.
    total = len(messages)
    numbered_messages = []
    
    for i, msg in enumerate(messages, 1):
        prefix = f"[{i}/{total}] "
        numbered = prefix + msg
        
        # Vérifier longueur finale
        if len(numbered) > max_length:
            # Tronquer le message pour respecter limite
            available = max_length - len(prefix) - 3  # -3 pour "..."
            msg = msg[:available] + "..."
            numbered = prefix + msg
        
        numbered_messages.append(numbered)
    
    # Sécurité: si > 10 messages, limiter à 10
    if len(numbered_messages) > 10:
        print(f"⚠️  Réponse trop longue ({len(numbered_messages)} msgs), limitation à 10")
        numbered_messages = numbered_messages[:10]
        # Mettre à jour numérotation
        numbered_messages = []
        for i, msg in enumerate(messages[:10], 1):
            prefix = f"[{i}/10] "
            numbered = prefix + msg
            if len(numbered) > max_length:
                available = max_length - len(prefix) - 3
                msg = msg[:available] + "..."
                numbered = prefix + msg
            numbered_messages.append(numbered)
    
    return numbered_messages


# Test du module
if __name__ == "__main__":
    print("="*70)
    print("TEST CLAUDE HANDLER v1.1")
    print("="*70)
    
    # Test 1: Nettoyage LaTeX
    print("\n📝 Test 1: Nettoyage LaTeX")
    print("-"*70)
    latex_text = r"Le fer métallique (Fe) perd des électrons et se transforme en ions ferreux (Fe^{2+}) : \[ \text{Fe} \rightarrow \text{Fe}^{2+} + 2e^- \]"
    cleaned = clean_latex(latex_text)
    print(f"Original: {latex_text}")
    print(f"Nettoyé: {cleaned}\n")
    
    # Test 2: Découpage intelligent
    print("\n📝 Test 2: Découpage messages")
    print("-"*70)
    long_text = """Pour redresser une pièce en inox, chauffez localement la zone bombée avec un chalumeau jusqu'à rouge sombre (600-700°C), puis refroidissez rapidement à l'eau. La contraction lors du refroidissement aide à redresser. Vous pouvez aussi utiliser un marteau et une enclume pour marteler progressivement. Pour de grandes pièces, utilisez une presse hydraulique avec des matrices adaptées."""
    
    messages = split_long_response(long_text, max_length=160)
    print(f"Texte original: {len(long_text)} chars")
    print(f"Découpé en: {len(messages)} messages\n")
    for i, msg in enumerate(messages, 1):
        print(f"Message {i}: ({len(msg)} chars)")
        print(f"  '{msg}'")
        print()
    
    print("="*70)
    print("TESTS TERMINÉS")
    print("="*70)
