"""The five quality checks compared on the planted-error benchmark.

  segment_qe   MQM QE on one (source, target) segment, as a TMS runs it. Same prompt as the main study.
  context_qe   the same MQM judgement of one segment, with the whole document given as context
  document_qe  MQM QE over the whole document in one call
  checklist    generic document unit tests: 7 fixed requirements, one call each, grounded by a verbatim quote
  case_tests   the main study's case-specific assertions (synthetic documents only)

Every check returns flags: [{"segments": [...], "severity", "category", "explanation"}]. Prompts put the
document first so repeated calls on one document share a cacheable prefix.
"""

from __future__ import annotations

import re

from rapidfuzz import fuzz

from common import llm
from common.llm import chat_json
from mtunit.assertions import evaluate_case
from transtest.segqe import PROMPT as SEGMENT_QE_PROMPT

from . import config
from .corpus import DOMAINS, Doc

SEVERITY = ("Severity: critical (could mislead the reader in a way that causes harm), major (meaning changed or "
            "important information lost), minor (imperfect but meaning preserved).")
CATEGORIES = ("Categories: accuracy/mistranslation, accuracy/omission, accuracy/addition, accuracy/untranslated, "
              "terminology, fluency, style/register, consistency.")

DOC_HEADER = """Document ({domain}): English source and Spanish (Spain) translation, in numbered segments.
{numbered}
"""

CONTEXT_QE_PROMPT = DOC_HEADER + """
You are an expert translation quality evaluator (MQM). Evaluate ONLY segment {n} of the translation:
Source: {src}
Translation: {tgt}

Use the rest of the document as context: an error in this segment can also be a problem of agreement, consistency
or coherence with other segments. List every translation error in segment {n}.
{categories}
{severity}

Reply with JSON only: {{"errors": [{{"category": "...", "severity": "minor|major|critical", "span": "<target text>", "explanation": "..."}}]}}
Return {{"errors": []}} if segment {n} is correct."""

DOCUMENT_QE_PROMPT = DOC_HEADER + """
You are an expert translation quality evaluator (MQM). List every translation error in the Spanish translation.
Judge each segment against its source and against the rest of the document: errors can also involve agreement,
consistency or coherence across segments.
{categories}
{severity}

Reply with JSON only: {{"errors": [{{"segments": [<segment numbers>], "category": "...", "severity": "minor|major|critical", "span": "<target text>", "explanation": "..."}}]}}
Return {{"errors": []}} if the translation is correct."""

CHECKS = {
    "agreement": "Every pronoun, clitic, determiner and adjective agrees in gender and number with the noun it refers "
                 "to, including when that noun is in another segment.",
    "register": "The translation addresses the reader with one consistent form of address (tú or usted) in every "
                "segment that addresses the reader.",
    "terminology": "Each recurring source term is translated the same way in every segment where it appears.",
    "list_fit": "Every list item or continuation segment grammatically completes the lead-in it continues.",
    "numbers": "Every number, dose, unit, frequency, duration and age in the source appears with the same value in "
               "the translation.",
    "logic": "Negations, conditions, quantifiers and time relations (not, never, unless, and/or, all/some, at least/at "
             "most, before/after) mean the same in the translation as in the source.",
    "meaning": "Every segment conveys the full meaning of its source segment: nothing is omitted, added or "
               "mistranslated.",
}

CHECK_PROMPT = DOC_HEADER + """
You are running ONE unit test on this Spanish translation.
Requirement: {requirement}

Find every place where the translation violates this requirement. Quote the Spanish text exactly as evidence.
Reply with JSON only: {{"violations": [{{"segments": [<segment numbers>], "evidence": "<exact quote from the translation>", "explanation": "<one sentence>"}}]}}
Return {{"violations": []}} if the requirement holds everywhere."""

DETECTORS = ["segment_qe", "context_qe", "document_qe", "checklist", "case_tests"]


def _call(prompt: str, model: str, max_tokens: int) -> tuple[dict, str]:
    kw = {"model": model, "max_tokens": max_tokens, "reasoning_effort": config.DETECT_EFFORT}
    out = chat_json(prompt, **kw)
    return (out if isinstance(out, dict) else {}), llm.cache_key(prompt, **kw)


def _ints(xs, n_max: int) -> list[int]:
    out = []
    for x in xs if isinstance(xs, list) else [xs]:
        try:
            i = int(x)
        except (TypeError, ValueError):
            continue
        if 1 <= i <= n_max:
            out.append(i)
    return sorted(set(out))


def _mqm_flags(errors, segments: list[int] | None, n_max: int) -> list[dict]:
    flags = []
    for e in errors if isinstance(errors, list) else []:
        if not isinstance(e, dict):
            continue
        segs = segments if segments is not None else _ints(e.get("segments", []), n_max)
        sev = str(e.get("severity", "")).lower()
        flags.append({"segments": segs, "severity": sev if sev in ("minor", "major", "critical") else "minor",
                      "category": str(e.get("category", "")), "explanation": str(e.get("explanation", "")),
                      "span": str(e.get("span", ""))})
    return flags


def segment_qe(doc: Doc, n: int, model: str) -> dict:
    src, tgt = doc.src[n - 1], doc.tgt[n - 1]
    if not tgt.strip():
        return {"flags": [{"segments": [n], "severity": "critical", "category": "accuracy/omission",
                           "explanation": "empty translation", "span": ""}], "keys": []}
    out, key = _call(SEGMENT_QE_PROMPT.format(src=src, tgt=tgt, src_lang="English", tgt_lang="Spanish"), model, 800)
    return {"flags": _mqm_flags(out.get("errors"), [n], len(doc.tgt)), "keys": [key]}


def context_qe(doc: Doc, n: int, model: str) -> dict:
    out, key = _call(CONTEXT_QE_PROMPT.format(domain=DOMAINS[doc.domain], numbered=doc.numbered(), n=n,
                                              src=doc.src[n - 1], tgt=doc.tgt[n - 1], categories=CATEGORIES,
                                              severity=SEVERITY), model, 800)
    return {"flags": _mqm_flags(out.get("errors"), [n], len(doc.tgt)), "keys": [key]}


def document_qe(doc: Doc, model: str) -> dict:
    out, key = _call(DOCUMENT_QE_PROMPT.format(domain=DOMAINS[doc.domain], numbered=doc.numbered(),
                                               categories=CATEGORIES, severity=SEVERITY), model, 4000)
    return {"flags": _mqm_flags(out.get("errors"), None, len(doc.tgt)), "keys": [key]}


def _grounded(quote: str, text: str) -> bool:
    q = re.sub(r"\s+", " ", quote or "").strip().strip("\"'«»“”").lower()
    return len(q) >= 3 and fuzz.partial_ratio(q, re.sub(r"\s+", " ", text).lower()) >= 85


def checklist(doc: Doc, check: str, model: str) -> dict:
    out, key = _call(CHECK_PROMPT.format(domain=DOMAINS[doc.domain], numbered=doc.numbered(),
                                         requirement=CHECKS[check]), model, 2000)
    target = "\n".join(doc.tgt)
    flags = []
    for v in out.get("violations", []) if isinstance(out.get("violations"), list) else []:
        if isinstance(v, dict) and _grounded(str(v.get("evidence", "")), target):
            flags.append({"segments": _ints(v.get("segments", []), len(doc.tgt)), "severity": "major",
                          "category": f"check/{check}", "explanation": str(v.get("explanation", "")),
                          "span": str(v.get("evidence", ""))})
    return {"flags": flags, "keys": [key]}


def case_tests(doc: Doc, case: dict, model: str) -> dict:
    """The main study's validated assertions for this case. Not localised: a failure flags the whole document."""
    res = evaluate_case(case, list(doc.src), list(doc.tgt), model=model, reasoning_effort=config.DETECT_EFFORT)
    flags = [{"segments": list(range(1, len(doc.tgt) + 1)), "severity": "major", "category": f"assert/{a.get('kind')}",
              "explanation": r.get("detail", ""), "span": ""}
             for a, r in zip(case["assertions"], res) if r["status"] == "fail"]
    return {"flags": flags, "keys": [], "statuses": [r["status"] for r in res]}
