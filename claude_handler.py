# claude_handler.py - v1.0
"""
Handler pour API Claude (Anthropic)
Compatible avec architecture modulaire email_monitor v3.1.0
"""

import os
import requests
from typing import Optional


def handle_claude_maritime_assistant(user_message: str) -> str:
    """
    Assistant maritime spécialisé avec Claude
    Optimisé pour questions nautiques, météo, navigation
    
    Args:
        user_message: Question de l'utilisateur
        
    Returns:
        Réponse de Claude (texte brut)
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

Si question hors contexte maritime: répondre brièvement que tu es spécialisé en navigation."""
        
        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 512,  # Limité pour réponses concises
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
        Réponse de Claude
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
        
        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": max_tokens,
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


def split_long_response(response: str, max_length: int = 160) -> list:
    """
    Découpe une réponse longue en messages inReach (max 160 chars)
    
    Args:
        response: Texte à découper
        max_length: Longueur max par message (défaut: 160)
        
    Returns:
        Liste de messages découpés
    """
    if len(response) <= max_length:
        return [response]
    
    messages = []
    words = response.split()
    current_msg = ""
    
    for word in words:
        test_msg = current_msg + " " + word if current_msg else word
        
        if len(test_msg) <= max_length:
            current_msg = test_msg
        else:
            if current_msg:
                messages.append(current_msg)
            current_msg = word
    
    if current_msg:
        messages.append(current_msg)
    
    return messages


# Test du module
if __name__ == "__main__":
    print("="*70)
    print("TEST CLAUDE HANDLER v1.0")
    print("="*70)
    
    # Test 1: Question maritime
    print("\n📝 Test 1: Question maritime")
    print("-"*70)
    response = handle_claude_maritime_assistant(
        "Que faire si le vent forcit à 35 nœuds?"
    )
    print(f"Réponse: {response}\n")
    
    # Test 2: Découpage long message
    print("\n📝 Test 2: Découpage message")
    print("-"*70)
    long_response = "Voici une très longue réponse qui dépasse largement la limite de 160 caractères imposée par les messages satellite inReach et qui doit donc être découpée en plusieurs segments pour pouvoir être transmise correctement sans perdre d'information importante."
    
    segments = split_long_response(long_response, max_length=160)
    print(f"Message original: {len(long_response)} chars")
    print(f"Découpé en: {len(segments)} segments")
    for i, segment in enumerate(segments, 1):
        print(f"  Segment {i}/{len(segments)} ({len(segment)} chars): {segment}")
    
    print("\n" + "="*70)
    print("TESTS TERMINÉS")
    print("="*70)
