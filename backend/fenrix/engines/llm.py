"""Optional local LLM (Ollama). Fenrix never sends code to a hosted API; if no
local model is running every caller falls back to deterministic output."""
from __future__ import annotations

import logging
import re

import httpx

from fenrix.config import get_settings

log = logging.getLogger("fenrix.llm")


def status() -> dict:
    s = get_settings()
    if not s.llm_enabled:
        return {"available": False, "model": None, "reason": "Disabled (FENRIX_LLM_ENABLED=false)"}
    try:
        r = httpx.get(f"{s.ollama_url}/api/tags", timeout=1.5)
        r.raise_for_status()
        models = [m.get("name", "") for m in r.json().get("models", [])]
        if any(m == s.ollama_model or m.split(":")[0] == s.ollama_model.split(":")[0] for m in models):
            return {"available": True, "model": s.ollama_model, "reason": "Ollama running locally"}
        return {"available": False, "model": None,
                "reason": f"Ollama is running but {s.ollama_model} is not pulled (ollama pull {s.ollama_model})"}
    except Exception:
        return {"available": False, "model": None, "reason": "Ollama not running — using built-in recipes"}


def generate_code(prompt: str, timeout: float = 60.0) -> str | None:
    s = get_settings()
    if not status()["available"]:
        return None
    system = ("You are a senior engineer helping replace a risky open-source dependency. "
              "Reply with ONE fenced code block only, no prose. Keep it under 40 lines, production quality, "
              "no placeholder TODOs, and do not import the library being replaced.")
    try:
        r = httpx.post(f"{s.ollama_url}/api/generate", timeout=timeout, json={
            "model": s.ollama_model, "system": system, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.2},
        })
        r.raise_for_status()
        text = r.json().get("response", "")
        m = re.search(r"```[\w+-]*\n(.*?)```", text, re.S)
        return (m.group(1) if m else text).strip() or None
    except Exception as exc:  # pragma: no cover - network dependent
        log.warning("LLM generation failed: %s", exc)
        return None
