# app/utils/translation.py
import openai
from config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_API_BASE
import base64

openai.api_key = OPENAI_API_KEY
openai.api_base = OPENAI_API_BASE

def translate_recipe(original_text, image_base64=None):
    messages = [
        {"role": "system", "content": "You are a helpful assistant that responds in Markdown. Help me translate Japanese recipes to Chinese."},
        {"role": "user", "content": original_text}
    ]
    
    if image_base64:
        image_message = {
            "type": "image_url",
            "image_url": f"data:image/png;base64,{image_base64}"
        }
        messages.append({"role": "user", "content": [original_text, image_message]})
    
    response = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.0,
    )
    
    return response.choices[0].message.content