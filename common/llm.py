"""Thin OpenAI-compatible chat client with role-based model selection.

Configuration comes from `.env` (see that file) or real environment variables:

  OPENROUTER_API_KEY   if set → OpenRouter; otherwise the local llama.cpp server
  L10N_JUDGE_MODEL     model that reads documents and judges meaning
  L10N_MT_MODEL        model that translates in the experiments
  L10N_LLM_MODEL       fallback for both
  L10N_LLM_BASE_URL    override the endpoint (e.g. https://api.openai.com/v1 with OPENAI_API_KEY)

Responses are cached on disk (keyed by endpoint + model + messages), so re-runs are free.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
import time
from pathlib import Path

from openai import OpenAI

from . import env  # noqa: F401  (loads .env)

_OR_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
if _OR_KEY:
    BASE_URL = os.environ.get("L10N_LLM_BASE_URL", "https://openrouter.ai/api/v1")
    API_KEY = _OR_KEY
    _default = os.environ.get("L10N_LLM_MODEL", "anthropic/claude-sonnet-5.5")
else:
    BASE_URL = os.environ.get("L10N_LLM_BASE_URL", "http://127.0.0.1:8081/v1")
    API_KEY = os.environ.get("OPENAI_API_KEY", "not-needed-for-local")
    _default = os.environ.get("L10N_LLM_MODEL", "local-qwen3-4b")

REMOTE = not BASE_URL.startswith(("http://127.", "http://localhost"))
MODEL = _default
JUDGE_MODEL = os.environ.get("L10N_JUDGE_MODEL", _default) if REMOTE else _default
MT_MODEL = os.environ.get("L10N_MT_MODEL", _default) if REMOTE else _default
REASONING_EFFORT = os.environ.get("L10N_REASONING_EFFORT", "low")

_CACHE_PATH = Path(__file__).resolve().parent.parent / ".cache" / "llm_cache.sqlite"
_lock = threading.Lock()
_client: OpenAI | None = None
_db: sqlite3.Connection | None = None


def describe() -> str:
    return f"endpoint={BASE_URL}  judge={JUDGE_MODEL}  mt={MT_MODEL}"


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=600, max_retries=4)
    return _client


def _get_db() -> sqlite3.Connection:
    global _db
    if _db is None:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _db = sqlite3.connect(_CACHE_PATH, check_same_thread=False)
        _db.execute("CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v TEXT)")
    return _db


def chat(
    messages: list[dict] | str,
    *,
    system: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    use_cache: bool = True,
) -> str:
    model = model or MODEL
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    if system:
        messages = [{"role": "system", "content": system}, *messages]

    key = hashlib.sha256(
        json.dumps([model, BASE_URL, messages, temperature, max_tokens], ensure_ascii=False).encode()
    ).hexdigest()
    if use_cache:
        with _lock:
            row = _get_db().execute("SELECT v FROM cache WHERE k=?", (key,)).fetchone()
        if row:
            return row[0]

    kw: dict = {"model": model, "messages": messages, "temperature": temperature}
    if REMOTE:
        # reasoning models spend tokens thinking before answering: leave them headroom
        kw["max_tokens"] = max(max_tokens, 4000)
        if REASONING_EFFORT and REASONING_EFFORT != "none":
            kw["extra_body"] = {"reasoning": {"effort": REASONING_EFFORT, "exclude": True}}
    else:
        kw["max_tokens"] = max_tokens

    out = ""
    for attempt in range(3):
        resp = _get_client().chat.completions.create(**kw)
        out = (resp.choices[0].message.content or "").strip() if resp.choices else ""
        if out:
            break
        time.sleep(2 * (attempt + 1))  # empty completion (provider hiccup): retry
    if use_cache and out:
        with _lock:
            _get_db().execute("INSERT OR REPLACE INTO cache VALUES (?, ?)", (key, out))
            _get_db().commit()
    return out


_JSON_RE = re.compile(r"\{.*\}|\[.*\]", re.DOTALL)


def _parse_json(raw: str):
    m = _JSON_RE.search(raw)
    if not m:
        raise ValueError(f"No JSON in LLM reply: {raw[:300]!r}")
    return json.loads(m.group(0))


def chat_json(messages: list[dict] | str, **kw) -> dict | list:
    """Chat and parse the first JSON object/array in the reply (tolerates ```json fences).
    On malformed JSON, asks the model once to repair its own reply."""
    raw = chat(messages, **kw)
    try:
        return _parse_json(raw)
    except (ValueError, json.JSONDecodeError):
        msgs = [{"role": "user", "content": messages}] if isinstance(messages, str) else list(messages)
        repair = msgs + [{"role": "assistant", "content": raw or "(empty)"},
                         {"role": "user", "content": "That reply was not valid JSON (it may have been cut off or "
                                                     "contain unescaped quotes). Reply again with ONLY valid, "
                                                     "complete JSON in the requested format. Keep text fields short."}]
        kw = {**kw, "max_tokens": max(kw.get("max_tokens", 1024), 1500)}
        return _parse_json(chat(repair, **kw))


_LABEL_RE = re.compile(r"^\s*(ES|Spanish|Español|Translation|Traducción)\s*:\s*", re.IGNORECASE)


def clean_translation(out: str) -> str:
    """Normalise an MT reply to ONE line: drop code fences / 'ES:' labels, join multi-line answers.
    (Taking only the first line would silently truncate list-like segments.)"""
    lines = [l.strip() for l in out.strip().strip("`").splitlines() if l.strip() and not l.strip().startswith("```")]
    return _LABEL_RE.sub("", " ".join(lines)).strip()
