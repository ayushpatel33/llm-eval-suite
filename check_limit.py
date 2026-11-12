import os
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL")
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
body = {"contents": [{"role": "user", "parts": [{"text": "Say hi"}]}]}

r = requests.post(
    url,
    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
    json=body,
    timeout=40,
)
print("model:", model)
print("status:", r.status_code)
print(r.text[:800])