# claude_handler.py V1.0
"""Module pour gérer les requêtes Claude AI"""

import requests
from config import ANTHROPIC_API_KEY
from utils import split_into_messages


def query_claude(prompt, max_words=50):
    """
    Envoie une requête à l'API Claude d'Anthropic
    
    Args:
        prompt: Question à poser
        max_words: Nombre max de mots pour la réponse
    
    Returns:
        list: Messages découpés avec numérotation [C X/Y] et coût
    """
    if not ANTHROPIC_API_KEY:
        return ["Claude AI non configuré. Définir ANTHROPIC_API_KEY."]
    
    try:
        print(f"🤖 Claude: {prompt[:50]}...")
        
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        system_msg = f"You are a helpful assistant for sailors at sea. Provide clear, practical answers in approximately {max_words} words."
        
        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": max_words * 3,
            "system": system_msg,
            "messages": [{
                "role": "user",
                "content": prompt
            }],
            "temperature": 0.7
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            answer = result['content'][0]['text'].strip()
            
            # Calcul du coût
            usage = result.get('usage', {})
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            
            input_cost = (input_tokens / 1_000_000) * 3.0
            output_cost = (output_tokens / 1_000_000) * 15.0
            total_cost = input_cost + output_cost
            
            print(f"✅ Claude: {len(answer)} chars, ${total_cost:.6f}")
            print(f"   Tokens: {input_tokens} in + {output_tokens} out")
            
            # Découper avec 95 chars max (120 - overhead)
            messages = split_into_messages(answer, max_chars_per_message=95)
            
            # Ajouter numérotation [C X/Y] et coût
            total_msgs = len(messages)
            numbered_messages = []
            
            for i, msg in enumerate(messages, 1):
                if i == total_msgs:
                    numbered_msg = f"[C {i}/{total_msgs}] {msg} [${total_cost:.4f}]"
                else:
                    numbered_msg = f"[C {i}/{total_msgs}] {msg}"
                
                # Vérification limite 120 chars
                if len(numbered_msg) > 120:
                    excess = len(numbered_msg) - 117
                    msg = msg[:-excess]
                    if i == total_msgs:
                        numbered_msg = f"[C {i}/{total_msgs}] {msg}... [${total_cost:.4f}]"
                    else:
                        numbered_msg = f"[C {i}/{total_msgs}] {msg}..."
                
                numbered_messages.append(numbered_msg)
            
            print(f"📨 Claude: {total_msgs} message(s)")
            for i, msg in enumerate(numbered_messages, 1):
                print(f"   [{i}/{total_msgs}]: {len(msg)} chars")
            
            return numbered_messages
        else:
            error = f"Erreur Claude: {response.status_code}"
            print(f"❌ {error} - {response.text}")
            return [error]
            
    except Exception as e:
        error = f"Erreur: {str(e)}"
        print(f"❌ Claude: {error}")
        import traceback
        traceback.print_exc()
        return [error]
