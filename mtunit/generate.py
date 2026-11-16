"""AI test generation + validation for engine unit tests.

A test case = short multi-segment English input + assertions about the Spanish output.
Validation: assertions must hold on a careful 'gold' translation; failing assertions are dropped
(they are either wrong or too strict), and cases left with no assertions are discarded.
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common.llm import JUDGE_MODEL, chat_json

from .assertions import evaluate_case
from .capabilities import CAPABILITIES, DOMAINS

GEN_MODEL = os.environ.get("L10N_GEN_MODEL", JUDGE_MODEL)
GOLD_MODEL = os.environ.get("L10N_GOLD_MODEL", "openai/gpt-5.4")

GEN_PROMPT = """You write UNIT TESTS for machine translation engines (English → Spanish (Spain)), like software unit
tests: each test isolates ONE capability and has precise, checkable assertions about the output.

Capability under test: {cap}
What it means: {desc}
Cross-segment capability: {cross} (if yes, the correct output must depend on information in a DIFFERENT
segment, so an engine translating segments one at a time is at real risk of failing)

Write {n} test cases, spread across these content domains: {domains}.
Each case is a short source text split into 1–6 segments (the way a CAT tool would segment it), realistic
for its domain, and designed so a plausible engine mistake would violate an assertion.

Assertion kinds (use the most precise kind that works; segments are numbered from 1):
- {{"kind": "preserve", "strings": ["{{count}}", "<b>"]}}: exact substrings that must appear in the output
- {{"kind": "contains", "segment": 3, "any_of": ["enfermera", "enfermeras"]}}: at least one variant must appear
  in that output segment (list ALL acceptable spellings/inflections; matching is case-insensitive)
- {{"kind": "not_contains", "segment": 3, "any_of": ["..."]}}: none may appear
- {{"kind": "judge", "segment": 3 or null, "property": "<a precise property of the Spanish output, stated so a
  bilingual reviewer can verify it, e.g. 'the adjective describing the nurse is feminine (cansada)'>"}}
  (segment null = whole output). Use judge for consistency, agreement, register, logic and scope.
Only assert what the capability is about: no general style or fluency assertions. 1–3 assertions per case.

Reply with JSON only:
{{"cases": [{{"domain": "<one of {domain_keys}>", "segments": ["...", "..."],
              "rationale": "<what failure this catches>", "assertions": [ ... ]}}]}}"""

GOLD_SYS = ("You are a senior professional English→Spanish (Spain) localizer. Translate with full document context, "
            "consistent terminology and form of address, exact placeholders/tags, and correct agreement.")
GOLD_PROMPT = """Translate this {domain_desc} text. It is split into {n} numbered segments; translate every segment
using the whole text as context. Reply with JSON only: {{"translations": ["<segment 1>", ...]}} with exactly {n} items.

{numbered}"""


def gold_translate(case: dict) -> list[str]:
    numbered = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(case["segments"]))
    out = chat_json(GOLD_PROMPT.format(domain_desc=DOMAINS.get(case["domain"], case["domain"]),
                                       n=len(case["segments"]), numbered=numbered),
                    system=GOLD_SYS, model=GOLD_MODEL, max_tokens=3000)
    tr = out.get("translations", []) if isinstance(out, dict) else out
    return [str(t) for t in tr][: len(case["segments"])]


def generate(n_per_cap: int = 8, out_path: Path | None = None) -> list[dict]:
    domain_keys = list(DOMAINS)

    def one(cap):
        c = CAPABILITIES[cap]
        out = chat_json(GEN_PROMPT.format(cap=cap, desc=c["desc"], cross="yes" if c["cross_segment"] else "no",
                                          n=n_per_cap, domains=", ".join(f"{k} ({v})" for k, v in DOMAINS.items()),
                                          domain_keys=domain_keys),
                        model=GEN_MODEL, max_tokens=8000)
        cases = []
        for i, cs in enumerate(out.get("cases", [])):
            if cs.get("segments") and cs.get("assertions"):
                cases.append({"id": f"{cap}-{i + 1:02d}", "capability": cap,
                              "cross_segment": c["cross_segment"], **cs})
        return cases

    with ThreadPoolExecutor(6) as ex:
        cases = [c for lst in ex.map(one, CAPABILITIES) for c in lst]
    if out_path:
        out_path.write_text(json.dumps(cases, ensure_ascii=False, indent=1), encoding="utf-8")
    return cases


def validate(cases: list[dict], out_path: Path | None = None) -> tuple[list[dict], dict]:
    """Keep only assertions that hold on the gold translation."""
    def one(case):
        gold = gold_translate(case)
        if len(gold) != len(case["segments"]):
            return None, {"dropped_case": case["id"], "why": "gold misaligned"}
        res = evaluate_case(case, case["segments"], gold)
        kept = [a for a, r in zip(case["assertions"], res) if r["status"] == "pass"]
        dropped = [{"assertion": a, "result": r} for a, r in zip(case["assertions"], res) if r["status"] != "pass"]
        if not kept:
            return None, {"dropped_case": case["id"], "why": "no assertion held on gold", "dropped": dropped}
        return {**case, "assertions": kept, "gold": gold}, ({"case": case["id"], "dropped": dropped} if dropped else None)

    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(one, cases))
    valid = [c for c, _ in results if c]
    log = [l for _, l in results if l]
    stats = {"generated_cases": len(cases), "valid_cases": len(valid),
             "generated_assertions": sum(len(c["assertions"]) for c in cases),
             "valid_assertions": sum(len(c["assertions"]) for c in valid), "log": log}
    if out_path:
        out_path.write_text(json.dumps(valid, ensure_ascii=False, indent=1), encoding="utf-8")
    return valid, stats
