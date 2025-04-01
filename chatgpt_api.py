import json
from openai import OpenAI

def load_api_key():
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    return config["api_key"]

def ask_chatgpt(prompt, role_prompt=""):
    client = OpenAI(api_key=load_api_key())
    messages = []
    if role_prompt:
        messages.append({"role": "system", "content": role_prompt})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.7
    )
    return response.choices[0].message.content