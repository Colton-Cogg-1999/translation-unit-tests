"""Engines under test, run as translation workloads: segment-by-segment or whole-document."""

from __future__ import annotations

from common.llm import chat, chat_json, clean_translation

from .capabilities import DOMAINS

SYS = ("You are a professional English→Spanish (Spain) translation engine for {domain}. "
       "Output only the translation.")
DOC_PROMPT = """Translate this text into Spanish (Spain). It is split into {n} numbered segments; use the whole text as
context. Reply with JSON only: {{"translations": ["<segment 1>", ...]}} with exactly {n} items, same order.

{numbered}"""


def translate_case(case: dict, model: str, mode: str) -> list[str]:
    sys = SYS.format(domain=DOMAINS.get(case["domain"], case["domain"]))
    segs = case["segments"]
    if mode == "segment":   # how most TMS/NMT pipelines run: one segment at a time, no context
        return [clean_translation(chat(s, system=sys, model=model, max_tokens=600)) for s in segs]
    numbered = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(segs))
    out = chat_json(DOC_PROMPT.format(n=len(segs), numbered=numbered), system=sys, model=model, max_tokens=3000)
    tr = out.get("translations", []) if isinstance(out, dict) else out
    tr = [clean_translation(str(t)) for t in tr]
    return (tr + [""] * len(segs))[: len(segs)]   # misaligned output → empty segments count as failures
