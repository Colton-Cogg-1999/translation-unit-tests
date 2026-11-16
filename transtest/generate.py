"""AI-generated test suites: draft a full suite from the SOURCE document alone.

The generator never sees a translation, so the same suite applies to any MT/LLM output in
any target language. Calibration (`calibrate --prune`, or prune_on_source() here) then drops
any test that fails on the source itself.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from common.llm import JUDGE_MODEL, chat_json

GEN_MODEL = os.environ.get("L10N_GEN_MODEL", JUDGE_MODEL)

LANG_NAMES = {"es": "Spanish (Spain)", "de": "German", "fr": "French", "it": "Italian", "pt": "Portuguese",
              "nl": "Dutch", "ja": "Japanese", "zh": "Chinese (Simplified)", "ko": "Korean"}

GEN_PROMPT = """You are a localization QA engineer writing an automated UNIT-TEST SUITE for translations
of the source document below into {lang_name}. The translation will be produced by NMT/LLM
engines working SEGMENT BY SEGMENT (one line at a time, no context), then reassembled.
Segment-level QE will already be run on each line in isolation, so focus your tests on what
can only be judged by reading the WHOLE translated document:

- meaning that depends on more than one segment: pronouns/subjects whose referent is in an
  earlier line ("It can increase…"), list items that inherit a condition from a lead-in line
  ("Do not take X" → "- if you are…"), cross-references, headings that scope what follows
- critical invariants a reader must come away with: doses, limits, time spans, ages, who must
  NOT do what, warnings, conditions (and/or), exceptions
- recurring key terms that must be rendered ONE consistent way across the document
- consistent register / form of address appropriate for this genre in {lang_name}
- names and codes that must not be translated

Write:
1. "claims": {n_claims} atomic statements (in English) that the translated document MUST convey.
   Prefer ones whose meaning depends on negation, numbers, conditions, or combining segments.
2. "false_claims": {n_false} plausible MISreadings (in English) a careless segment-by-segment translation
   could produce (flipped negation, wrong number/unit, and↔or, wrong referent, lost condition).
   Each must be clearly FALSE according to the source.
3. "qa": {n_qa} questions whose correct answer needs information from MORE THAN ONE segment, with short answers.
4. "key_terms": up to {n_terms} recurring source terms (not brand names) that must be translated consistently.
5. "dnt": brand/product names and codes that must appear unchanged in the translation.
6. "register": {{"expected": "<the expected form of address in {lang_name} for this genre, with example forms>",
                 "violation": "<the wrong form of address to flag, with example forms>"}}

Reply with JSON only:
{{"claims": ["..."], "false_claims": ["..."], "qa": [{{"question": "...", "expected": "..."}}],
  "key_terms": ["..."], "dnt": ["..."], "register": {{"expected": "...", "violation": "..."}}}}

<source_document lang="en">
{doc}
</source_document>"""


def generate_suite_dict(source_text: str, target_lang: str, n_claims: int = 10, n_false: int = 6,
                        n_qa: int = 5, n_terms: int = 4) -> dict:
    lang_name = LANG_NAMES.get(target_lang, target_lang)
    out = chat_json(GEN_PROMPT.format(doc=source_text, lang_name=lang_name, n_claims=n_claims,
                                      n_false=n_false, n_qa=n_qa, n_terms=n_terms),
                    max_tokens=4000, model=GEN_MODEL)
    tests: list[dict] = [{"type": "numbers", "severity": "critical"},
                         {"type": "coverage", "severity": "major"},
                         {"type": "placeholders", "severity": "minor"}]
    dnt = [d for d in out.get("dnt", []) if isinstance(d, str) and d.strip() and d in source_text]
    if dnt:
        tests.append({"type": "dnt", "severity": "minor"})
    reg = out.get("register") or {}
    if reg.get("expected") and reg.get("violation"):
        tests.append({"type": "register", "id": "gen-register", "expected": reg["expected"],
                      "violation": reg["violation"], "severity": "major"})
    tests += [{"type": "term_consistency_llm", "id": f"gen-term-{i + 1}", "term": t, "severity": "major"}
              for i, t in enumerate(out.get("key_terms", [])) if isinstance(t, str)]
    tests += [{"type": "assert", "id": f"gen-claim-{i + 1}", "claim": c, "severity": "major"}
              for i, c in enumerate(out.get("claims", []))]
    tests += [{"type": "assert", "id": f"gen-false-{i + 1}", "claim": c, "expect": False, "severity": "critical"}
              for i, c in enumerate(out.get("false_claims", []))]
    tests += [{"type": "qa", "id": f"gen-qa-{i + 1}", "question": q["question"], "expected": q["expected"],
               "severity": "major"} for i, q in enumerate(out.get("qa", [])) if "question" in q]
    return {"source_lang": "en", "target_lang": target_lang, "dnt": dnt, "tests": tests,
            "generator": GEN_MODEL}


def generate_suite(source_path: str | Path, target_lang: str, out_path: str | Path, **kw) -> dict:
    source_path, out_path = Path(source_path), Path(out_path)
    suite = generate_suite_dict(source_path.read_text(encoding="utf-8"), target_lang, **kw)
    suite = {"suite": f"auto-generated: {source_path.parent.name}/{source_path.name}",
             "source": os.path.relpath(source_path.resolve(), out_path.resolve().parent), **suite}
    out_path.write_text(yaml.safe_dump(suite, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")
    return suite


def prune_on_source(suite_path: str | Path, out_path: str | Path) -> tuple[int, list[str]]:
    """Run the suite on its own source; drop tests that fail or error there (broken tests)."""
    from .model import Suite
    from .runner import run_suite

    suite = Suite.load(suite_path)
    res = run_suite(suite, None, mode="source")
    broken = [r.test_id for r in res if r.status in ("fail", "error")]
    raw = yaml.safe_load(Path(suite_path).read_text(encoding="utf-8"))
    raw["tests"] = [t for t, s in zip(raw["tests"], suite.tests) if s.id not in broken]
    raw["pruned_on_source"] = broken
    Path(out_path).write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")
    return len(raw["tests"]), broken
