"""Thin OpenAI-compatible chat client with role-based model selection.

Configuration comes from `.env` (see that file) or real environment variables:

  OPENROUTER_API_KEY   if set → OpenRouter; otherwise the local llama.cpp server
  L10N_JUDGE_MODEL     model that reads documents and judges meaning
  L10N_MT_MODEL        model that translates in the experiments
  L10N_LLM_MODEL       fallback for both
  L10N_LLM_BASE_URL    override the endpoint (e.g. https://api.openai.com/v1 with OPENAI_API_KEY)
  use_openai()         switch this process to the OpenAI API directly (OPENAI_API_KEY); used by benchmark/
  L10N_OFFLINE=1       answer only from the cache; a cache miss raises CacheMiss instead of calling an API.
                       Used to replay the study from results/cache/ (see `python -m common.cache`).

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
OFFLINE = os.environ.get("L10N_OFFLINE", "").strip().lower() in ("1", "true", "yes")
if _OR_KEY or OFFLINE:   # offline replay uses the OpenRouter cache keys the study was run with
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

OPENAI_URL = "https://api.openai.com/v1"

_CACHE_PATH = Path(os.environ.get("L10N_CACHE_PATH",
                                  Path(__file__).resolve().parent.parent / ".cache" / "llm_cache.sqlite"))
_lock = threading.Lock()
_client: OpenAI | None = None
_db: sqlite3.Connection | None = None


before_api_call = None   # optional callables around every uncached request (benchmark.budget sets them)
after_api_call = None


class CacheMiss(RuntimeError):
    """Raised in offline mode (L10N_OFFLINE=1) when a request is not in the cache."""


def use_openai(reasoning_effort: str = "low") -> None:
    """Send this process's calls straight to the OpenAI API. Cache keys then include the reasoning effort."""
    global BASE_URL, API_KEY, REMOTE, REASONING_EFFORT, _client
    BASE_URL, REMOTE, REASONING_EFFORT, _client = OPENAI_URL, True, reasoning_effort, None
    API_KEY = os.environ.get("OPENAI_API_KEY", "")
    if not API_KEY and not OFFLINE:
        raise RuntimeError("OPENAI_API_KEY is not set (put it in .env), or set L10N_OFFLINE=1 to replay from the cache")


def describe() -> str:
    return f"endpoint={BASE_URL}{' (offline)' if OFFLINE else ''}  judge={JUDGE_MODEL}  mt={MT_MODEL}"


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=600, max_retries=8)
    return _client


def _get_db() -> sqlite3.Connection:
    global _db
    if _db is None:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _db = sqlite3.connect(_CACHE_PATH, check_same_thread=False)
        _db.execute("CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v TEXT)")
        _db.execute("CREATE TABLE IF NOT EXISTS usage (k TEXT PRIMARY KEY, model TEXT, prompt INTEGER, "
                    "cached INTEGER, completion INTEGER, reasoning INTEGER)")
    return _db


def chat(
    messages: list[dict] | str,
    *,
    system: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    use_cache: bool = True,
    reasoning_effort: str | None = None,
) -> str:
    model = model or MODEL
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    if system:
        messages = [{"role": "system", "content": system}, *messages]

    direct = BASE_URL == OPENAI_URL
    effort = reasoning_effort or REASONING_EFFORT
    key_parts = [model, BASE_URL, messages, temperature, max_tokens] + ([effort] if direct else [])
    key = hashlib.sha256(json.dumps(key_parts, ensure_ascii=False).encode()).hexdigest()
    if use_cache:
        with _lock:
            row = _get_db().execute("SELECT v FROM cache WHERE k=?", (key,)).fetchone()
        if row:
            return row[0]

    if OFFLINE:
        raise CacheMiss(f"not in cache (model={model}): {json.dumps(messages, ensure_ascii=False)[:200]}")
    if before_api_call is not None:
        before_api_call()   # e.g. a spending cap; runs only when a request will actually reach the API
    try:
        return _call_api(model, messages, temperature, max_tokens, effort, direct, key, use_cache)
    finally:
        if after_api_call is not None:
            after_api_call()


def _call_api(model, messages, temperature, max_tokens, effort, direct, key, use_cache) -> str:

    kw: dict = {"model": model, "messages": messages, "temperature": temperature}
    if direct:
        # OpenAI reasoning models: temperature is fixed at 1 unless reasoning is off; reasoning tokens count
        # against max_completion_tokens, so leave headroom
        kw = {"model": model, "messages": messages, "reasoning_effort": effort,
              "max_completion_tokens": max_tokens + 16000}
        if effort == "none":
            kw["temperature"] = temperature
    elif REMOTE:
        # reasoning models spend tokens thinking before answering: leave them headroom
        kw["max_tokens"] = max(max_tokens, 4000)
        if REASONING_EFFORT and REASONING_EFFORT != "none":
            kw["extra_body"] = {"reasoning": {"effort": REASONING_EFFORT, "exclude": True}}
    else:
        kw["max_tokens"] = max_tokens

    out, resp = "", None
    for attempt in range(3):
        resp = _get_client().chat.completions.create(**kw)
        out = (resp.choices[0].message.content or "").strip() if resp.choices else ""
        if out:
            break
        time.sleep(2 * (attempt + 1))  # empty completion (provider hiccup): retry
    if use_cache and out:
        u = getattr(resp, "usage", None)
        with _lock:
            _get_db().execute("INSERT OR REPLACE INTO cache VALUES (?, ?)", (key, out))
            if u is not None:
                pd, cd = getattr(u, "prompt_tokens_details", None), getattr(u, "completion_tokens_details", None)
                _get_db().execute("INSERT OR REPLACE INTO usage VALUES (?, ?, ?, ?, ?, ?)", (
                    key, model, u.prompt_tokens, getattr(pd, "cached_tokens", 0) or 0, u.completion_tokens,
                    getattr(cd, "reasoning_tokens", 0) or 0))
            _get_db().commit()
    return out


def cache_key(messages: list[dict] | str, *, system: str | None = None, model: str | None = None,
              temperature: float = 0.0, max_tokens: int = 1024, reasoning_effort: str | None = None) -> str:
    """The cache key chat() would use for these arguments (to look up recorded token usage)."""
    model = model or MODEL
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    if system:
        messages = [{"role": "system", "content": system}, *messages]
    parts = [model, BASE_URL, messages, temperature, max_tokens]
    if BASE_URL == OPENAI_URL:
        parts.append(reasoning_effort or REASONING_EFFORT)
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()


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
