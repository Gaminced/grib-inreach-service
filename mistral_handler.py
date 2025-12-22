# mistral_handler.py - v1.0
"""
Handler pour API Mistral AI
Compatible avec architecture modulaire email_monitor v3.1.0
"""

import os
import requests
from typing import Optional


def handle_mistral_maritime_assistant(user_message: str) -> str:
    """
    Assistant maritime spécialisé avec Mistral
    Optimisé pour questions nautiques, météo, navigation
    
    Args:
        user_message: Question de l'utilisateur
        
    Returns:
        Réponse de Mistral (texte brut)
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
- MAX 160 caractères par réponse
- Info essentielle UNIQUEMENT
- Vocabulaire maritime précis
- Conseils pratiques directs
- Pas de fioriture

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
            "max_tokens": 512,  # Limité pour réponses concises
            "temperature": 0.7
        }
        
        print("📤 Envoi requête API Mistral...")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            answer = result['choices'][0]['message']['content'].strip()
            
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
        Réponse de Mistral
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
        
        data = {
            "model": "mistral-large-latest",
            "messages": [
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
        Analyse météo de Mistral
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


def split_long_response(response: str, max_length: int = 160) -> list:
    """
    Découpe une réponse longue en messages inReach (max 160 chars)
    
    Args:
        response: Texte à découper
        max_length: Longueur max par message
        
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
    print("TEST MISTRAL HANDLER v1.0")
    print("="*70)
    
    # Test 1: Question maritime
    print("\n📝 Test 1: Question maritime")
    print("-"*70)
    response = handle_mistral_maritime_assistant(
        "Comment réduire voilure si vent 40 nœuds?"
    )
    print(f"Réponse: {response}\n")
    
    # Test 2: Expert météo
    print("\n📝 Test 2: Expert météo")
    print("-"*70)
    response = handle_mistral_weather_expert(
        "GRIB montre 25kt NO demain. Bon pour cap 270°?"
    )
    print(f"Réponse: {response}\n")
    
    # Test 3: Découpage message long
    print("\n📝 Test 3: Découpage message")
    print("-"*70)
    long_response = "Pour naviguer en sécurité par forte mer, il est recommandé de réduire la voilure progressivement, de maintenir un cap stable, de sécuriser tout l'équipement de pont, et de mettre en place des tours de quart pour surveiller les conditions météorologiques."
    
    segments = split_long_response(long_response, max_length=160)
    print(f"Message original: {len(long_response)} chars")
    print(f"Découpé en: {len(segments)} segments")
    for i, segment in enumerate(segments, 1):
        print(f"  Segment {i}/{len(segments)} ({len(segment)} chars): {segment}")
    
    print("\n" + "="*70)
    print("TESTS TERMINÉS")
    print("="*70)
