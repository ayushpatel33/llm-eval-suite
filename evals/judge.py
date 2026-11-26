import hashlib
import json
import os
import re
import time

import requests
from dotenv import load_dotenv
from deepeval.models import DeepEvalBaseLLM

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(ROOT, ".env"), override=True)

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

CACHE_PATH = os.path.join(ROOT, ".cache", "judge.json")
TRIES = 3
MIN_GAP = 6
_last_call = 0.0


def _load_cache():
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _wait_turn():
    global _last_call
    gap = time.time() - _last_call
    if gap < MIN_GAP:
        time.sleep(MIN_GAP - gap)
    _last_call = time.time()


def _call_gemini(prompt, as_json):
    key = hashlib.sha256(f"{MODEL}|{as_json}|{prompt}".encode("utf-8")).hexdigest()
    cache = _load_cache()
    if key in cache:
        return cache[key]

    if not API_KEY or not MODEL:
        raise RuntimeError("Missing GEMINI_API_KEY or GEMINI_MODEL. Check your .env file.")

    config = {"temperature": 0}
    if as_json:
        config["responseMimeType"] = "application/json"
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": config}
    headers = {"x-goog-api-key": API_KEY, "Content-Type": "application/json"}

    last_problem = ""
    for attempt in range(TRIES):
        wait = 3 * (attempt + 1)
        _wait_turn()
        try:
            r = requests.post(URL, headers=headers, json=body, timeout=60)
        except requests.exceptions.Timeout:
            last_problem = "timeout"
        else:
            if r.status_code in (429, 500, 503):
                last_problem = f"server busy ({r.status_code})"
                if r.status_code == 429:
                    if "perday" in r.text.lower().replace(" ", ""):
                        raise RuntimeError(
                            "Daily free quota used up. Wait for the reset "
                            "or change GEMINI_MODEL in .env."
                        )
                    wait = 20 * (attempt + 1)
            else:
                r.raise_for_status()
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                cache[key] = text
                _save_cache(cache)
                return text
        if attempt < TRIES - 1:
            time.sleep(wait)
    raise RuntimeError(f"Gemini server not available after {TRIES} tries: {last_problem}")


def _clean_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text


class GeminiJudge(DeepEvalBaseLLM):
    """Lets DeepEval use Gemini (through plain REST calls) as the judge."""

    def __init__(self):
        self.model_name = MODEL

    def load_model(self):
        return self.model_name

    def get_model_name(self):
        return f"Gemini judge ({self.model_name})"

    def generate(self, prompt: str, schema=None):
        if schema is None:
            return _call_gemini(prompt, as_json=False)
        full_prompt = (
            prompt
            + "\n\nReturn ONLY valid JSON that matches this JSON schema:\n"
            + json.dumps(schema.model_json_schema())
        )
        text = _call_gemini(full_prompt, as_json=True)
        return schema(**json.loads(_clean_json(text)))

    async def a_generate(self, prompt: str, schema=None):
        return self.generate(prompt, schema)