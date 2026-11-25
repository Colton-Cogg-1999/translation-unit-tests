"""Evaluate a test case's assertions against an engine's output segments."""

from __future__ import annotations

import re

from rapidfuzz import fuzz

from common.llm import JUDGE_MODEL, CacheMiss, chat_json

JUDGE_PROMPT = """You are verifying ONE property of a Spanish translation produced by a machine translation engine.

Source (English), numbered segments:
{src}

Translation (Spanish), numbered segments:
{tgt}

Property to verify{scope}:
{prop}

Quote the relevant Spanish text exactly, then decide whether the property HOLDS for the translation as written.
Reply with JSON only: {{"evidence": "<exact quote from the translation>", "reason": "<one sentence>", "holds": true|false}}"""


def _numbered(segs: list[str]) -> str:
    return "\n".join(f"{i + 1}. {s}" for i, s in enumerate(segs))


def _seg_text(segs: list[str], seg) -> str:
    if seg in (None, "", 0):
        return "\n".join(segs)
    i = int(seg) - 1
    return segs[i] if 0 <= i < len(segs) else ""


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).lower()


def evaluate_assertion(a: dict, src: list[str], tgt: list[str]) -> dict:
    kind = a.get("kind")
    try:
        if kind == "preserve":
            text = "\n".join(tgt)
            missing = [s for s in a.get("strings", []) if s not in text]
            return {"status": "fail" if missing else "pass", "detail": f"missing {missing}" if missing else "all preserved"}
        if kind in ("contains", "not_contains"):
            text = _norm(_seg_text(tgt, a.get("segment")))
            hits = [v for v in a.get("any_of", []) if _norm(v) in text]
            ok = bool(hits) if kind == "contains" else not hits
            return {"status": "pass" if ok else "fail",
                    "detail": (f"found {hits}" if hits else f"none of {a.get('any_of')} found")}
        if kind == "judge":
            seg = a.get("segment")
            scope = f" (focus on translated segment {seg})" if seg not in (None, "", 0) else " (whole translation)"
            out = chat_json(JUDGE_PROMPT.format(src=_numbered(src), tgt=_numbered(tgt), scope=scope,
                                                prop=a["property"]), max_tokens=500, model=JUDGE_MODEL)
            ev = str(out.get("evidence", ""))
            grounded = len(ev.strip()) < 3 or fuzz.partial_ratio(_norm(ev), _norm("\n".join(tgt))) >= 85
            if not grounded:
                return {"status": "unverified", "detail": f"ungrounded evidence: {ev[:120]}"}
            return {"status": "pass" if out.get("holds") else "fail", "detail": out.get("reason", ""), "evidence": ev}
        return {"status": "error", "detail": f"unknown assertion kind {kind!r}"}
    except CacheMiss:
        raise
    except Exception as e:
        return {"status": "error", "detail": f"{type(e).__name__}: {e}"[:200]}


def evaluate_case(case: dict, src: list[str], tgt: list[str]) -> list[dict]:
    return [evaluate_assertion(a, src, tgt) for a in case["assertions"]]
