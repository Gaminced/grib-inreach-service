# mistral_handler.py - v1.0
"""Handler pour conversations avec Mistral AI via inReach"""

import os
from mistralai import Mistral
from typing import Optional


def handle_mistral_request(user_message: str, conversation_history: Optional[list] = None) -> str:
    """
    Traite une requête Mistral et retourne la réponse
    
    Args:
        user_message: Message de l'utilisateur
        conversation_history: Historique optionnel des messages précédents
        
    Returns:
        Réponse de Mistral (texte brut)
    """
    api_key = os.getenv('MISTRAL_API_KEY')
    
    if not api_key:
        return "❌ MISTRAL_API_KEY non configurée"
    
    try:
        client = Mistral(api_key=api_key)
        
        # Construire l'historique de conversation
        messages = []
        
        if conversation_history:
            messages.extend(conversation_history)
        
        # Ajouter le message actuel
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Appel API Mistral
        response = client.chat.complete(
            model="mistral-large-latest",  # Meilleur modèle Mistral
            messages=messages,
            max_tokens=1024  # Limité pour inReach
        )
        
        # Extraire le texte de la réponse
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content
        else:
            return "❌ Réponse vide de Mistral"
            
    except Exception as e:
        return f"❌ Erreur Mistral: {e}"


def handle_mistral_request_with_context(
    user_message: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 1024
) -> str:
    """
    Requête Mistral avec prompt système personnalisé
    
    Args:
        user_message: Message utilisateur
        system_prompt: Instructions système optionnelles
        max_tokens: Limite de tokens (défaut: 1024)
        
    Returns:
        Réponse de Mistral
    """
    api_key = os.getenv('MISTRAL_API_KEY')
    
    if not api_key:
        return "❌ MISTRAL_API_KEY non configurée"
    
    try:
        client = Mistral(api_key=api_key)
        
        messages = []
        
        # Ajouter prompt système si fourni
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Ajouter message utilisateur
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=messages,
            max_tokens=max_tokens
        )
        
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content
        else:
            return "❌ Réponse vide de Mistral"
            
    except Exception as e:
        return f"❌ Erreur Mistral: {e}"


def handle_mistral_maritime_assistant(user_message: str) -> str:
    """
    Assistant maritime spécialisé avec Mistral
    Optimisé pour questions nautiques, météo, navigation
    
    Args:
        user_message: Question de l'utilisateur
        
    Returns:
        Réponse de Mistral spécialisée maritime
    """
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

    return handle_mistral_request_with_context(
        user_message=user_message,
        system_prompt=system_prompt,
        max_tokens=512
    )


def handle_mistral_weather_expert(user_message: str) -> str:
    """
    Expert météo marine spécialisé avec Mistral
    
    Args:
        user_message: Question météo
        
    Returns:
        Analyse météo de Mistral
    """
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

    return handle_mistral_request_with_context(
        user_message=user_message,
        system_prompt=system_prompt,
        max_tokens=512
    )


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


def compare_models_response(user_message: str) -> dict:
    """
    Compare les réponses de Mistral et Claude sur la même question
    Utile pour choisir le meilleur modèle selon le contexte
    
    Args:
        user_message: Question à poser aux deux modèles
        
    Returns:
        Dict avec réponses des deux modèles
    """
    # Import Claude handler
    try:
        from claude_handler import handle_claude_maritime_assistant
        claude_response = handle_claude_maritime_assistant(user_message)
    except:
        claude_response = "❌ Claude handler non disponible"
    
    # Réponse Mistral
    mistral_response = handle_mistral_maritime_assistant(user_message)
    
    return {
        "question": user_message,
        "mistral": {
            "response": mistral_response,
            "length": len(mistral_response),
            "segments": len(split_long_response(mistral_response))
        },
        "claude": {
            "response": claude_response,
            "length": len(claude_response),
            "segments": len(split_long_response(claude_response))
        }
    }


# === EXEMPLES D'UTILISATION ===

if __name__ == "__main__":
    # Test 1: Question maritime simple
    print("Test 1: Question maritime")
    print("-" * 50)
    response = handle_mistral_maritime_assistant(
        "Comment réduire voilure si vent 40 nœuds?"
    )
    print(f"Réponse: {response}\n")
    
    # Test 2: Expert météo
    print("Test 2: Expert météo")
    print("-" * 50)
    response = handle_mistral_weather_expert(
        "GRIB montre 25kt NO demain. Bon pour cap 270°?"
    )
    print(f"Réponse: {response}\n")
    
    # Test 3: Découpage message long
    print("Test 3: Découpage message")
    print("-" * 50)
    long_response = "Pour naviguer en sécurité par forte mer, il est recommandé de réduire la voilure progressivement, de maintenir un cap stable, de sécuriser tout l'équipement de pont, et de mettre en place des tours de quart pour surveiller les conditions météorologiques."
    
    segments = split_long_response(long_response, max_length=160)
    for i, segment in enumerate(segments, 1):
        print(f"Message {i}/{len(segments)}: {segment}")
    
    # Test 4: Conversation avec historique
    print("\nTest 4: Conversation avec historique")
    print("-" * 50)
    history = [
        {"role": "user", "content": "Position 09°S 092°W, cap Marquises"},
        {"role": "assistant", "content": "Route Marquises OK. Distance ~2500nm. ETA?"}
    ]
    
    response = handle_mistral_request(
        user_message="Vitesse moyenne 6kt, combien de jours?",
        conversation_history=history
    )
    print(f"Réponse: {response}")
    
    # Test 5: Comparaison Mistral vs Claude
    print("\nTest 5: Comparaison modèles")
    print("-" * 50)
    comparison = compare_models_response(
        "Meilleure allure pour économiser carburant?"
    )
    print(f"Question: {comparison['question']}")
    print(f"\nMistral ({comparison['mistral']['length']} chars):")
    print(f"  {comparison['mistral']['response']}")
    print(f"\nClaude ({comparison['claude']['length']} chars):")
    print(f"  {comparison['claude']['response']}")
