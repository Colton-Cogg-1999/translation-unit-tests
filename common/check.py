"""Verify the API setup:  uv run python -m common.check

Makes one tiny call per role (judge, MT, embeddings), bypassing the cache.
"""

from __future__ import annotations

import sys

from common import llm
from common.embed import EXTRA_RETRIEVAL_MODELS, RETRIEVAL_MODEL, embed


def main() -> int:
    print(llm.describe())
    if not llm.REMOTE:
        print("OPENROUTER_API_KEY is blank in .env → using the local llama.cpp server (must be running).")
    ok = True
    for role, model in [("judge", llm.JUDGE_MODEL), ("mt", llm.MT_MODEL)]:
        try:
            out = llm.chat("Translate to Spanish, output only the translation: Keep out of the reach of children.",
                           model=model, max_tokens=60, use_cache=False)
            print(f"  ✓ {role:9} {model:40} → {out!r}")
        except Exception as e:
            ok = False
            print(f"  ✗ {role:9} {model:40} → {type(e).__name__}: {e}")
    for model in [RETRIEVAL_MODEL, *EXTRA_RETRIEVAL_MODELS]:
        try:
            v = embed(["Do not take with alcohol.", "No tomar con alcohol.", "Store below 25 °C."], model)
            print(f"  ✓ embed     {model:40} → dim {v.shape[1]}, sim(en,es)={v[0] @ v[1]:.2f}, sim(en,other)={v[0] @ v[2]:.2f}")
        except Exception as e:
            ok = False
            print(f"  ✗ embed     {model:40} → {type(e).__name__}: {e}")
    print("all good" if ok else "some checks failed (see above)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
