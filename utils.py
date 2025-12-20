# utils.py
"""Fonctions utilitaires partagées"""

import re

def split_into_messages(text, max_chars_per_message=95):
    """
    Découpe un texte en plusieurs messages de taille limitée
    Découpe intelligemment par phrases
    
    Args:
        text: Texte à découper
        max_chars_per_message: Taille max par message
        
    Returns:
        list: Liste de messages découpés
    """
    messages = []
    
    # Découper par phrases
    sentences = re.split(r'([.!?]\s+)', text)
    current_message = ""
    
    for i in range(0, len(sentences), 2):
        sentence = sentences[i]
        if i + 1 < len(sentences):
            sentence += sentences[i + 1]
        
        if len(current_message) + len(sentence) > max_chars_per_message:
            if current_message:
                messages.append(current_message.strip())
                current_message = sentence
            else:
                # Phrase trop longue, couper par mots
                words = sentence.split()
                temp_msg = ""
                for word in words:
                    if len(temp_msg) + len(word) + 1 <= max_chars_per_message:
                        temp_msg += word + " "
                    else:
                        if temp_msg:
                            messages.append(temp_msg.strip())
                        temp_msg = word + " "
                current_message = temp_msg
        else:
            current_message += sentence
    
    # Toujours ajouter le dernier message
    if current_message and current_message.strip():
        messages.append(current_message.strip())
    
    # Limiter à 10 messages maximum
    if len(messages) > 10:
        print(f"⚠️  Réponse trop longue ({len(messages)} messages), truncation à 10", flush=True)
        chars_per_msg = len(text) // 10 + 10
        messages = []
        for i in range(10):
            start = i * chars_per_msg
            end = min((i + 1) * chars_per_msg, len(text))
            if start < len(text):
                msg = text[start:end].strip()
                if i == 9 and end < len(text):
                    msg += "..."
                messages.append(msg)
    
    # Vérification finale
    if not messages:
        print("⚠️  ATTENTION: split_into_messages a généré 0 messages!", flush=True)
        messages = [text[:max_chars_per_message]]
    
    print(f"   🔍 Découpage: {len(text)} chars → {len(messages)} message(s)", flush=True)
    for i, msg in enumerate(messages, 1):
        print(f"      Msg {i}: {len(msg)} chars", flush=True)
    
    return messages


def parse_ai_request(body):
    """
    Parse une requête AI du format: <provider> <max_words>: <question>
    Supporte: claude, mistral, gpt (alias pour claude)
    
    Args:
        body: Corps de l'email
        
    Returns:
        tuple: (provider, max_words, question) ou (None, None, None)
    """
    # Pattern: claude/mistral/gpt 150: How do tides work?
    ai_pattern = re.compile(r'(claude|mistral|gpt)\s+(\d+)\s*:\s*(.+)', re.IGNORECASE | re.DOTALL)
    match = ai_pattern.search(body)
    
    if match:
        provider = match.group(1).lower()
        # Alias: gpt → claude
        if provider == 'gpt':
            provider = 'claude'
        max_words = int(match.group(2))
        question = match.group(3).strip()
        question = ' '.join(question.split())
        
        return provider, max_words, question
    
    return None, None, None
