"""Verify the API setup:  uv run python -m common.check

Makes one tiny call to each model the main study uses (generator/judge/QE, gold, adjudicator, engines),
bypassing the cache.
"""

from __future__ import annotations

import os
import sys

from common import llm


def main() -> int:
    from mtunit.adjudicate import ADJ_MODEL
    from mtunit.generate import GEN_MODEL, GOLD_MODEL
    from mtunit.run import DEFAULT_ENGINES

    print(llm.describe())
    if llm.OFFLINE:
        print("L10N_OFFLINE is set: nothing to check, every call is answered from the cache.")
        return 0
    if not llm.REMOTE:
        print("OPENROUTER_API_KEY is blank in .env → using the local OpenAI-compatible server (must be running).")
    engines = os.environ.get("L10N_MTUNIT_ENGINES", DEFAULT_ENGINES).split(",")
    roles = [("generator", GEN_MODEL), ("judge/QE", llm.JUDGE_MODEL), ("gold", GOLD_MODEL), ("adjudicator", ADJ_MODEL)]
    roles += [("engine", e.strip()) for e in engines if e.strip()]
    ok = True
    for role, model in dict.fromkeys(roles):
        try:
            out = llm.chat("Translate to Spanish, output only the translation: Keep out of the reach of children.",
                           model=model, max_tokens=60, use_cache=False)
            print(f"  ✓ {role:11} {model:40} → {out!r}")
        except Exception as e:
            ok = False
            print(f"  ✗ {role:11} {model:40} → {type(e).__name__}: {e}")
    print("all good" if ok else "some checks failed (see above)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
