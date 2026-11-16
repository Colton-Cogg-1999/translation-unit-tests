"""Sentence embeddings, local (sentence-transformers) or hosted (OpenRouter).

Model names prefixed with "openrouter:" are embedded via the OpenRouter embeddings API,
e.g. "openrouter:baai/bge-m3". Anything else is loaded locally with sentence-transformers.
"""

from __future__ import annotations

import os
import threading
from functools import lru_cache

import numpy as np

from . import env  # noqa: F401  (loads .env)

_HAS_KEY = bool(os.environ.get("OPENROUTER_API_KEY", "").strip())
# Retrieval (TM search / RAG). Hosted BGE-M3 when a key is present, else local BGE-M3.
RETRIEVAL_MODEL = os.environ.get("L10N_RETRIEVAL_MODEL",
                                 "openrouter:baai/bge-m3" if _HAS_KEY else "BAAI/bge-m3")
if RETRIEVAL_MODEL.startswith("openrouter:") and not _HAS_KEY:
    RETRIEVAL_MODEL = "BAAI/bge-m3"
EXTRA_RETRIEVAL_MODELS = [m.strip() for m in os.environ.get("L10N_EXTRA_RETRIEVAL_MODELS", "").split(",")
                          if m.strip() and (_HAS_KEY or not m.strip().startswith("openrouter:"))]
# LaBSE: trained specifically for translation-pair (bitext) detection → alignment. Small; stays local.
ALIGN_MODEL = os.environ.get("L10N_ALIGN_MODEL", "sentence-transformers/LaBSE")


_LOCAL_LOCK = threading.Lock()  # local torch models are not safe to share across threads


@lru_cache(maxsize=4)
def get_model(name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(name, device="cpu")


def _embed_remote(texts: list[str], model: str, batch_size: int = 128, show_progress: bool = False) -> np.ndarray:
    from openai import OpenAI

    client = OpenAI(base_url=os.environ.get("L10N_EMBED_BASE_URL", "https://openrouter.ai/api/v1"),
                    api_key=os.environ["OPENROUTER_API_KEY"], timeout=300, max_retries=5)
    out: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        resp = client.embeddings.create(model=model, input=batch)
        out.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
        if show_progress:
            print(f"  embedded {min(i + batch_size, len(texts))}/{len(texts)} with {model}", flush=True)
    v = np.asarray(out, dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def embed(texts: list[str], model: str = RETRIEVAL_MODEL, batch_size: int = 32,
          show_progress: bool = False) -> np.ndarray:
    """Return L2-normalised embeddings, shape (n, d), float32."""
    if model.startswith("openrouter:"):
        return _embed_remote(texts, model.removeprefix("openrouter:"), show_progress=show_progress)
    with _LOCAL_LOCK:
        m = get_model(model)
        vecs = m.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                        show_progress_bar=show_progress, convert_to_numpy=True)
    return vecs.astype(np.float32)
