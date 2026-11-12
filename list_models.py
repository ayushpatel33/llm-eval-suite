import os
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GEMINI_API_KEY")
url = "https://generativelanguage.googleapis.com/v1beta/models"

r = requests.get(url, headers={"x-goog-api-key": key}, params={"pageSize": 100}, timeout=20)
print("status:", r.status_code)
if r.status_code != 200:
    print(r.text[:300])
else:
    for m in r.json().get("models", []):
        if "generateContent" in m.get("supportedGenerationMethods", []):
            print(m["name"].replace("models/", ""))