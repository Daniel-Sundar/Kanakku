"""Talk to an AI model.  Owner: Daniel.

LLM_MODE = cloud | local | replay | rules   (default: cloud, falling back down the chain)
  cloud  : Google Gemini (GEMINI_API_KEY in .env, model GEMINI_MODEL, default gemini-flash-latest)
  local  : Ollama on this laptop (OLLAMA_MODEL, default qwen2.5-coder:7b)
  replay : answers saved from earlier real runs in replay_cache/
  rules  : no AI; planner falls back to its rule parser
Every successful AI reply is saved to replay_cache/, so the demo works with Wi-Fi off.
"""
import hashlib
import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "replay_cache"


def _load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()


def _cache_file(key: str) -> Path:
    return CACHE / (hashlib.sha256(key.strip().lower().encode()).hexdigest()[:16] + ".json")


def _cloud(prompt: str) -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("no GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                      headers={"x-goog-api-key": key},
                      json={"contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}},
                      timeout=25)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _local(prompt: str) -> str:
    r = requests.post(os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/generate",
                      json={"model": os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b"), "prompt": prompt,
                            "stream": False, "format": "json", "options": {"temperature": 0}},
                      timeout=60)
    r.raise_for_status()
    return r.json()["response"]


def _replay(prompt: str, key: str) -> str:
    f = _cache_file(key)
    if not f.exists():
        raise RuntimeError("not in replay cache")
    return json.loads(f.read_text())["response"]


def generate(prompt: str, cache_key: str):
    """Return (text, mode_used), or (None, why_every_mode_failed)."""
    order = {"cloud": ["cloud", "local", "replay"], "local": ["local", "cloud", "replay"],
             "replay": ["replay"], "rules": []}[os.getenv("LLM_MODE", "cloud")]
    errors = []
    for mode in order:
        try:
            text = _replay(prompt, cache_key) if mode == "replay" else (_cloud if mode == "cloud" else _local)(prompt)
            if mode != "replay":
                CACHE.mkdir(exist_ok=True)
                _cache_file(cache_key).write_text(json.dumps({"question": cache_key, "mode": mode, "response": text}))
            return text, mode
        except Exception as e:  # noqa: BLE001  (any failure means: try the next mode)
            errors.append(f"{mode}: {str(e)[:80]}")
    return None, "; ".join(errors) or "AI switched off"
