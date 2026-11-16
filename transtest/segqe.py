"""Segment-level QE baseline: what a TMS/QE step sees: one (source, target) segment at a time.

MQM-style error annotation by an LLM (GEMBA-MQM-like). A segment is "flagged" if the model
reports any major or critical error. Uses the same judge model as transtest for a fair fight.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

from common.llm import JUDGE_MODEL, chat_json

PROMPT = """You are an expert translation quality evaluator (MQM). Evaluate this single segment.

Source ({src_lang}): {src}
Translation ({tgt_lang}): {tgt}

List every translation error. Categories: accuracy/mistranslation, accuracy/omission,
accuracy/addition, accuracy/untranslated, terminology, fluency, style/register.
Severity: critical (could mislead the reader in a way that causes harm), major (meaning changed
or important information lost), minor (imperfect but meaning preserved).

Reply with JSON only: {{"errors": [{{"category": "...", "severity": "minor|major|critical", "span": "<target text>", "explanation": "..."}}]}}
Return {{"errors": []}} if the translation is correct."""

WORKERS = int(os.environ.get("SEGQE_WORKERS", "8"))


def qe_segment(src: str, tgt: str, src_lang: str = "English", tgt_lang: str = "Spanish") -> dict:
    if not tgt.strip():
        return {"errors": [{"category": "accuracy/omission", "severity": "critical", "span": "",
                            "explanation": "empty translation"}]}
    try:
        out = chat_json(PROMPT.format(src=src, tgt=tgt, src_lang=src_lang, tgt_lang=tgt_lang),
                        max_tokens=800, model=JUDGE_MODEL)
        return out if isinstance(out, dict) else {"errors": []}
    except Exception as e:
        return {"errors": [], "error": str(e)}


def flagged(qe: dict) -> bool:
    return any(str(e.get("severity", "")).lower() in ("major", "critical") for e in qe.get("errors", []))


def qe_document(src_lines: list[str], tgt_lines: list[str]) -> list[dict]:
    assert len(src_lines) == len(tgt_lines), "segment QE needs 1:1 segments"
    with ThreadPoolExecutor(WORKERS) as ex:
        res = list(ex.map(lambda p: qe_segment(*p), zip(src_lines, tgt_lines)))
    return [{"line": i, "src": s, "tgt": t, "flagged": flagged(r), **r}
            for i, (s, t, r) in enumerate(zip(src_lines, tgt_lines, res))]
