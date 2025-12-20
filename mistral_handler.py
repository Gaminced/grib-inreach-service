# mistral_handler.py V1.0
"""Module pour gérer les requêtes Mistral AI"""

import requests
from config import MISTRAL_API_KEY
from utils import split_into_messages


def query_mistral(prompt, max_words=50):
    """
    Envoie une requête à l'API Mistral AI
    
    Args:
        prompt: Question à poser
        max_words: Nombre max de mots pour la réponse
    
    Returns:
        list: Messages découpés avec numérotation [M X/Y] et coût
    """
    if not MISTRAL_API_KEY:
        return ["Mistral AI non configuré. Définir MISTRAL_API_KEY."]
    
    try:
        print(f"🤖 Mistral: {prompt[:50]}...")
        
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        
        system_msg = f"You are a helpful assistant for sailors at sea. Provide clear, practical answers in approximately {max_words} words."
        
        data = {
            "model": "mistral-large-latest",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": max_words * 3
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            answer = result['choices'][0]['message']['content'].strip()
            
            # Calcul du coût
            usage = result.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            
            input_cost = (input_tokens / 1_000_000) * 2.0
            output_cost = (output_tokens / 1_000_000) * 6.0
            total_cost = input_cost + output_cost
            
            print(f"✅ Mistral: {len(answer)} chars, ${total_cost:.6f}")
            print(f"   Tokens: {input_tokens} in + {output_tokens} out")
            
            # Découper avec 95 chars max (120 - overhead)
            messages = split_into_messages(answer, max_chars_per_message=95)
            
            # Ajouter numérotation [M X/Y] et coût
            total_msgs = len(messages)
            numbered_messages = []
            
            for i, msg in enumerate(messages, 1):
                if i == total_msgs:
                    numbered_msg = f"[M {i}/{total_msgs}] {msg} [${total_cost:.4f}]"
                else:
                    numbered_msg = f"[M {i}/{total_msgs}] {msg}"
                
                # Vérification limite 120 chars
                if len(numbered_msg) > 120:
                    excess = len(numbered_msg) - 117
                    msg = msg[:-excess]
                    if i == total_msgs:
                        numbered_msg = f"[M {i}/{total_msgs}] {msg}... [${total_cost:.4f}]"
                    else:
                        numbered_msg = f"[M {i}/{total_msgs}] {msg}..."
                    print(f"   ⚠️  Msg {i} tronqué de {excess} chars")
                
                numbered_messages.append(numbered_msg)
            
            print(f"📨 Mistral: {total_msgs} message(s)")
            for i, msg in enumerate(numbered_messages, 1):
                print(f"   [{i}/{total_msgs}]: {len(msg)} chars")
            
            return numbered_messages
        else:
            error = f"Erreur Mistral: {response.status_code}"
            print(f"❌ {error} - {response.text}")
            return [error]
            
    except Exception as e:
        error = f"Erreur: {str(e)}"
        print(f"❌ Mistral: {error}")
        import traceback
        traceback.print_exc()
        return [error]
