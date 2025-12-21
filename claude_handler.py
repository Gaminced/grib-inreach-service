# claude_handler.py - v1.0
"""Handler pour conversations avec Claude AI via inReach"""

import os
import anthropic
from typing import Optional


def handle_claude_request(user_message: str, conversation_history: Optional[list] = None) -> str:
    """
    Traite une requête Claude et retourne la réponse
    
    Args:
        user_message: Message de l'utilisateur
        conversation_history: Historique optionnel des messages précédents
        
    Returns:
        Réponse de Claude (texte brut)
    """
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        return "❌ ANTHROPIC_API_KEY non configurée"
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        # Construire l'historique de conversation
        messages = []
        
        if conversation_history:
            messages.extend(conversation_history)
        
        # Ajouter le message actuel
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Appel API Claude
        response = client.messages.create(
            model="claude-sonnet-4-20250514",  # Modèle le plus récent
            max_tokens=1024,  # Limité pour inReach (messages courts)
            messages=messages
        )
        
        # Extraire le texte de la réponse
        if response.content and len(response.content) > 0:
            return response.content[0].text
        else:
            return "❌ Réponse vide de Claude"
            
    except anthropic.APIError as e:
        return f"❌ Erreur API Claude: {e}"
    except Exception as e:
        return f"❌ Erreur inattendue: {e}"


def handle_claude_request_with_context(
    user_message: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 1024
) -> str:
    """
    Requête Claude avec prompt système personnalisé
    
    Args:
        user_message: Message utilisateur
        system_prompt: Instructions système optionnelles
        max_tokens: Limite de tokens (défaut: 1024)
        
    Returns:
        Réponse de Claude
    """
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        return "❌ ANTHROPIC_API_KEY non configurée"
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        # Paramètres de base
        params = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        }
        
        # Ajouter prompt système si fourni
        if system_prompt:
            params["system"] = system_prompt
        
        response = client.messages.create(**params)
        
        if response.content and len(response.content) > 0:
            return response.content[0].text
        else:
            return "❌ Réponse vide de Claude"
            
    except anthropic.APIError as e:
        return f"❌ Erreur API Claude: {e}"
    except Exception as e:
        return f"❌ Erreur inattendue: {e}"


def handle_claude_maritime_assistant(user_message: str) -> str:
    """
    Assistant maritime spécialisé avec Claude
    Optimisé pour questions nautiques, météo, navigation
    
    Args:
        user_message: Question de l'utilisateur
        
    Returns:
        Réponse de Claude spécialisée maritime
    """
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

    return handle_claude_request_with_context(
        user_message=user_message,
        system_prompt=system_prompt,
        max_tokens=512  # Limité pour réponses concises
    )


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
        # Vérifier si ajouter le mot dépasse la limite
        test_msg = current_msg + " " + word if current_msg else word
        
        if len(test_msg) <= max_length:
            current_msg = test_msg
        else:
            # Message plein, le sauvegarder et commencer nouveau
            if current_msg:
                messages.append(current_msg)
            current_msg = word
    
    # Ajouter le dernier message
    if current_msg:
        messages.append(current_msg)
    
    return messages


# === EXEMPLES D'UTILISATION ===

if __name__ == "__main__":
    # Test 1: Question simple
    print("Test 1: Question simple")
    print("-" * 50)
    response = handle_claude_maritime_assistant(
        "Que faire si le vent forcit à 35 nœuds?"
    )
    print(f"Réponse: {response}\n")
    
    # Test 2: Découpage long message
    print("Test 2: Découpage message")
    print("-" * 50)
    long_response = "Voici une très longue réponse qui dépasse largement la limite de 160 caractères imposée par les messages satellite inReach et qui doit donc être découpée en plusieurs segments pour pouvoir être transmise correctement sans perdre d'information."
    
    segments = split_long_response(long_response, max_length=160)
    for i, segment in enumerate(segments, 1):
        print(f"Message {i}/{len(segments)}: {segment}")
    
    # Test 3: Conversation avec contexte
    print("\nTest 3: Conversation avec historique")
    print("-" * 50)
    history = [
        {"role": "user", "content": "Je suis au large des Galapagos"},
        {"role": "assistant", "content": "Compris. Navigation Pacifique. Météo?"}
    ]
    
    response = handle_claude_request(
        user_message="Quel cap vers Easter Island?",
        conversation_history=history
    )
    print(f"Réponse: {response}")
