# claude_handler.py - v1.5.0
"""
Handler pour API Claude (Anthropic) avec nettoyage email InReach
Compatible avec architecture modulaire email_monitor v3.2.3

v1.5.0: 
- NETTOYAGE EMAIL INREACH avant envoi à Claude
- ALGORITHME ROBUSTE découpage équilibré
- Messages 110 chars minimum (sauf exceptions)
- Distribution équitable du texte
- Fusion agressive < 80 chars
- Coût + solde dans dernier message
"""

import os
import re
import requests
from typing import Optional, Tuple
from inreach_email_cleaner import clean_inreach_email


# Suivi du solde Claude (initialisé à $5.00 par défaut)
CLAUDE_BALANCE = float(os.getenv('CLAUDE_BALANCE', '5.00'))


def handle_claude_maritime_assistant(raw_email_body: str) -> Tuple[str, float]:
    """
    Assistant maritime spécialisé avec Claude + NETTOYAGE EMAIL
    Optimisé pour questions nautiques, météo, navigation
    
    Args:
        raw_email_body: Corps brut de l'email InReach (avec métadonnées)
        
    Returns:
        Tuple (réponse, coût) - Réponse de Claude + coût de la requête
    """
    # ✨ NETTOYAGE EMAIL INREACH
    user_message = clean_inreach_email(raw_email_body)
    
    if not user_message:
        return ("❌ Email vide après nettoyage", 0.0)
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        return ("❌ ANTHROPIC_API_KEY non configurée", 0.0)
    
    try:
        print(f"\n{'='*70}")
        print("🤖 CLAUDE MARITIME ASSISTANT v1.5.0")
        print(f"{'='*70}")
        print(f"📧 Email nettoyé ({len(user_message)} chars)")
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
- Réponses COURTES (max 120 caractères si possible)
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
            
            return (answer, total_cost)
            
        else:
            error_msg = f"❌ Erreur API Claude: {response.status_code}"
            print(error_msg)
            print(f"Réponse: {response.text[:200]}")
            return (f"Erreur Claude: {response.status_code}", 0.0)
            
    except Exception as e:
        error_msg = f"❌ Erreur Claude: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return (f"Erreur: {str(e)[:100]}", 0.0)


def handle_claude_request(raw_email_body: str, max_tokens: int = 1024) -> Tuple[str, float]:
    """
    Requête Claude générique (non spécialisée maritime) + NETTOYAGE EMAIL
    
    Args:
        raw_email_body: Corps brut de l'email InReach
        max_tokens: Limite de tokens (défaut: 1024)
        
    Returns:
        Tuple (réponse, coût) - Réponse de Claude + coût de la requête
    """
    # ✨ NETTOYAGE EMAIL INREACH
    user_message = clean_inreach_email(raw_email_body)
    
    if not user_message:
        return ("❌ Email vide après nettoyage", 0.0)
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        return ("❌ ANTHROPIC_API_KEY non configurée", 0.0)
    
    try:
        print(f"\n{'='*70}")
        print("🤖 CLAUDE REQUEST v1.5.0")
        print(f"{'='*70}")
        print(f"📧 Email nettoyé ({len(user_message)} chars)")
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
            
            return (answer, total_cost)
            
        else:
            error_msg = f"❌ Erreur API: {response.status_code}"
            print(error_msg)
            return (f"Erreur Claude: {response.status_code}", 0.0)
            
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
    ALGORITHME ROBUSTE v1.4
    Découpe équilibrée avec messages 110 chars minimum
    
    STRATÉGIE:
    1. Calcul nombre optimal de messages (total_chars / 110)
    2. Distribution équitable par mots
    3. Fusion agressive < 80 chars
    4. Coût dans dernier message
    
    Args:
        response: Texte à découper
        cost: Coût de la requête
        max_length: Longueur max (120)
        
    Returns:
        Liste messages équilibrés avec coût
    """
    global CLAUDE_BALANCE
    
    print(f"\n{'='*70}")
    print(f"✂️  DÉCOUPAGE ROBUSTE v1.4")
    print(f"{'='*70}")
    print(f"Texte original: {len(response)} chars\n")
    
    # Réserver espace pour numérotation + coût
    prefix_space = 8  # "[99/99] "
    cost_space = 35   # " | Coût: $X.XXXX | Solde: $Y.YY"
    usable_length = max_length - prefix_space
    
    # Si très court, retourner avec coût
    if len(response) <= max_length - cost_space:
        CLAUDE_BALANCE -= cost
        suffix = f" | Coût: ${cost:.4f} | Solde: ${CLAUDE_BALANCE:.2f}"
        if len(response + suffix) <= max_length:
            return [response + suffix]
    
    # CALCUL NOMBRE OPTIMAL DE MESSAGES
    # Objectif: 110 chars par message (bon compromis)
    target_per_msg = 110
    estimated_msgs = max(1, int(len(response) / target_per_msg) + 1)
    
    print(f"📊 Estimation: {estimated_msgs} messages (~{target_per_msg} chars/msg)")
    
    # DÉCOUPAGE PAR MOTS (plus robuste que par phrases)
    words = response.split()
    total_words = len(words)
    
    if total_words == 0:
        return [response]
    
    # Distribution équitable des mots
    words_per_msg = max(1, total_words // estimated_msgs)
    
    messages = []
    current_msg = ""
    word_count = 0
    
    for i, word in enumerate(words):
        test_msg = current_msg + " " + word if current_msg else word
        
        # Stratégie: remplir jusqu'à target_per_msg (110 chars)
        if len(test_msg) <= usable_length:
            current_msg = test_msg
            word_count += 1
            
            # Couper si on atteint target OU quota mots
            if (len(current_msg) >= target_per_msg or word_count >= words_per_msg) and i < total_words - 1:
                # Vérifier qu'on a assez rempli (> 80 chars)
                if len(current_msg) >= 80:
                    messages.append(current_msg.strip())
                    current_msg = ""
                    word_count = 0
        else:
            # Message plein
            if current_msg:
                messages.append(current_msg.strip())
            current_msg = word
            word_count = 1
    
    # Ajouter dernier message
    if current_msg.strip():
        messages.append(current_msg.strip())
    
    # FUSION AGRESSIVE messages < 80 chars
    print(f"\n🔗 Fusion messages courts...")
    optimized = []
    i = 0
    
    while i < len(messages):
        msg = messages[i]
        
        # Fusionner avec suivants si < 80 chars
        while len(msg) < 80 and i + 1 < len(messages):
            combined = msg + " " + messages[i + 1]
            if len(combined) <= usable_length:
                msg = combined
                i += 1
                print(f"   Fusion: {len(msg)} chars")
            else:
                break
        
        optimized.append(msg)
        i += 1
    
    messages = optimized
    
    # VALIDATION: aucun message < 70 chars (sauf si dernier avec coût)
    print(f"\n✅ Validation longueurs...")
    final_messages = []
    
    for i, msg in enumerate(messages):
        if len(msg) < 70 and i < len(messages) - 1:
            # Trop court: fusionner avec suivant
            if i + 1 < len(messages):
                messages[i + 1] = msg + " " + messages[i + 1]
                print(f"   ⚠️  Msg {i+1} trop court ({len(msg)} chars), fusionné")
                continue
        final_messages.append(msg)
    
    messages = final_messages
    
    # NUMÉROTATION + COÛT
    total = len(messages)
    numbered_messages = []
    
    print(f"\n📊 Messages finaux: {total}")
    
    for i, msg in enumerate(messages, 1):
        prefix = f"[{i}/{total}] "
        
        # Dernier message: ajouter coût
        if i == total:
            CLAUDE_BALANCE -= cost
            suffix = f" | Coût: ${cost:.4f} | Solde: ${CLAUDE_BALANCE:.2f}"
            
            numbered = prefix + msg + suffix
            
            if len(numbered) <= max_length:
                numbered_messages.append(numbered)
                print(f"   ✅ [{i}/{total}] {len(numbered)} chars (avec coût)")
            else:
                # Tronquer pour faire tenir le coût
                available = max_length - len(prefix) - len(suffix) - 3
                if available > 30:
                    msg = msg[:available] + "..."
                    numbered = prefix + msg + suffix
                    numbered_messages.append(numbered)
                    print(f"   ⚠️  [{i}/{total}] tronqué: {len(numbered)} chars")
                else:
                    # Séparer le coût
                    numbered_messages.append(prefix + msg)
                    numbered_messages.append(f"[{total+1}/{total+1}] Coût: ${cost:.4f} | Solde: ${CLAUDE_BALANCE:.2f}")
                    print(f"   ⚠️  Coût séparé")
        else:
            numbered = prefix + msg
            
            if len(numbered) > max_length:
                available = max_length - len(prefix) - 3
                msg = msg[:available] + "..."
                numbered = prefix + msg
                print(f"   ⚠️  [{i}/{total}] tronqué: {len(numbered)} chars")
            
            numbered_messages.append(numbered)
            print(f"   ✅ [{i}/{total}] {len(numbered)} chars")
    
    print(f"\n{'='*70}")
    print(f"✅ DÉCOUPAGE TERMINÉ: {len(numbered_messages)} messages")
    print(f"💰 Coût: ${cost:.4f} | Solde: ${CLAUDE_BALANCE:.2f}")
    print(f"{'='*70}\n")
    
    return numbered_messages
