"""LLM-backed meaning checks.

Design rules that keep a small local judge honest:
  * The judge reads ONLY the document under test (target), never the source. It
    plays a monolingual reader: "what does this text actually tell a patient/user?"
    That is exactly what segment-level QE does not measure.
  * Every 'supported' verdict must quote verbatim evidence; the quote is verified
    against the document with fuzzy matching. Ungrounded = not supported.
  * The document is placed first in the prompt and marked cacheable, so every test on the
    same document re-reads it from the provider's prompt cache (Anthropic cache_control /
    OpenAI automatic prefix caching / llama.cpp slot cache): ~70-90% cheaper input.
  * Each suite is calibrated by running it on the SOURCE: a test that fails on the
    source is a broken test, not a translation error.
"""

from __future__ import annotations

import re

from rapidfuzz import fuzz

from common.llm import JUDGE_MODEL, chat_json

from ..model import Result, TestSpec
from . import Context, check

SYSTEM = (
    "You are a meticulous reader checking what a document literally says. "
    "Use only the document text. Do not use outside knowledge, do not assume what "
    "the document 'should' say, and do not correct its mistakes. Pay close attention "
    "to negation, numbers, units, conditions (if/and/or), and who/what pronouns refer to."
)


def _doc_block(ctx: Context) -> str:
    d = ctx.doc_under_test
    return f"<document lang=\"{d.lang}\">\n{d.text.strip()}\n</document>\n\n"


def _doc_messages(ctx: Context, question: str, doc: str | None = None) -> list[dict]:
    """Document first (cacheable prefix), question last."""
    return [{"role": "user", "content": [
        {"type": "text", "text": doc or _doc_block(ctx), "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": question},
    ]}]


def _grounded(quote: str, text: str, thr: int = 88) -> bool:
    q = (quote or "").strip().strip("\"'«»“”")
    if len(q) < 4:
        return False
    def norm(s):
        return re.sub(r"\s+", " ", s).lower()
    return fuzz.partial_ratio(norm(q), norm(text)) >= thr


# ---------------------------------------------------------------- assert

ASSERT_PROMPT = """Claim (written in English; the document may be in another language):
"{claim}"

Does the document, as literally written, state or clearly entail this claim?
- "supported": the document says this (any wording, any language).
- "contradicted": the document says something incompatible with it.
- "not_stated": the document does not address it.

Work step by step. First copy the most relevant sentence, then restate in plain English
exactly what THAT sentence says (keep who-does-what-to-whom, negation, numbers, and/or),
then compare it to the claim.

Reply with JSON only, in this key order:
{{"evidence": "<the most relevant sentence copied EXACTLY from the document>", "evidence_in_english": "<literal English rendering of that sentence>", "reasoning": "<does the rendering say the same as the claim? one sentence>", "verdict": "supported|contradicted|not_stated"}}"""


def judge_claim(ctx: Context, claim: str) -> dict:
    out = chat_json(
        _doc_messages(ctx, ASSERT_PROMPT.format(claim=claim)),
        system=SYSTEM, max_tokens=400, model=JUDGE_MODEL,
    )
    verdict = str(out.get("verdict", "")).strip().lower().replace(" ", "_")
    grounded = _grounded(out.get("evidence", ""), ctx.doc_under_test.text)
    if verdict == "supported" and not grounded:
        verdict = "not_stated (ungrounded)"
    return {**out, "verdict": verdict, "grounded": grounded}


@check("assert")
def assert_claim(spec: TestSpec, ctx: Context) -> Result:
    """params.claim: str; params.expect: true (default) = must be stated, false = must NOT be stated."""
    claim = spec.params["claim"]
    expect = spec.params.get("expect", True)
    j = judge_claim(ctx, claim)
    supported = j["verdict"] == "supported"
    ok = supported if expect else not supported
    label = "MUST state" if expect else "must NOT state"
    return Result(spec.id, spec.type, "pass" if ok else "fail", spec.severity,
                  f"[{label}] {claim} → judge: {j['verdict']} ({j.get('reasoning', '')})",
                  evidence=[j.get("evidence", "")], details=j)


# ---------------------------------------------------------------- QA probe

QA_PROMPT = """Answer the question using ONLY the document. If the document does not answer it, answer "NOT IN DOCUMENT".
Question: {q}

Reply with JSON only: {{"evidence": "<sentence(s) copied EXACTLY from the document>", "answer": "<short answer in English>"}}"""

GRADE_PROMPT = """A reader answered a question about a document.
Question: {q}
Expected answer: {expected}
Reader's answer: {answer}

Does the reader's answer convey the same facts as the expected answer? Numbers, units,
time spans, conditions and negation must match; wording and extra harmless detail do not matter.
Reply with JSON only: {{"reason": "<one sentence>", "match": true|false}}"""


@check("qa")
def qa(spec: TestSpec, ctx: Context) -> Result:
    """Reading-comprehension probe. Often needs info spread across sentences/sections,
    so it tests document-level meaning (coreference, conditions, cross-references)."""
    q, expected = spec.params["question"], spec.params["expected"]
    a = chat_json(_doc_messages(ctx, QA_PROMPT.format(q=q)),
                  system=SYSTEM, max_tokens=400, model=JUDGE_MODEL)
    answer = str(a.get("answer", ""))
    g = chat_json(GRADE_PROMPT.format(q=q, expected=expected, answer=answer), max_tokens=200, model=JUDGE_MODEL)
    ok = bool(g.get("match")) and "NOT IN DOCUMENT" not in answer.upper()
    return Result(spec.id, spec.type, "pass" if ok else "fail", spec.severity,
                  f"Q: {q} | expected: {expected} | got: {answer}",
                  evidence=[a.get("evidence", "")], details={"answer": a, "grade": g})


# ---------------------------------------------------------------- register / style consistency

REGISTER_PROMPT = """Classify how each numbered sentence addresses the reader.
- "ok": matches the expected style: {expected}
- "violation": {violation}
- "none": no direct address to the reader: headings, statements, and impersonal instructions
  (infinitives such as "Conservar…", "Mantener…", "No utilizar…", passive or "se" constructions).
  Only label "violation" when the sentence actually addresses the reader in the wrong form.

Reply with JSON only, one label per sentence number, e.g. {{"1": "ok", "2": "none", ...}}

{numbered}"""


@check("register")
def register(spec: TestSpec, ctx: Context) -> Result:
    """Document-wide style consistency (e.g. usted vs tú, Sie vs du, vous vs tu)."""
    if ctx.mode == "source" and not spec.params.get("applies_to_source"):
        return Result(spec.id, spec.type, "skip", spec.severity, "target-language check")
    sents = ctx.doc_under_test.sentences
    numbered = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(sents))
    out = chat_json(REGISTER_PROMPT.format(expected=spec.params["expected"],
                                           violation=spec.params["violation"], numbered=numbered),
                    max_tokens=20 * len(sents) + 50, model=JUDGE_MODEL)
    idx = [int(k) - 1 for k, v in out.items()
           if str(k).isdigit() and 0 < int(k) <= len(sents) and "viol" in str(v).lower()]
    ev = [sents[i] for i in idx]
    return Result(spec.id, spec.type, "fail" if idx else "pass", spec.severity,
                  f"{len(idx)} sentence(s) break register: {spec.params['expected']}" if idx
                  else f"register consistent ({spec.params['expected']})", evidence=ev)


@check("forbidden_patterns")
def forbidden_patterns(spec: TestSpec, ctx: Context) -> Result:
    """Deterministic regex screen, e.g. Spanish informal 'tú' markers."""
    if ctx.mode == "source":
        return Result(spec.id, spec.type, "skip", spec.severity, "target-language check")
    hits = []
    for s in ctx.target.sentences:
        for pat in spec.params["patterns"]:
            if re.search(pat, s, flags=re.IGNORECASE):
                hits.append(f"/{pat}/ in: {s}")
    return Result(spec.id, spec.type, "fail" if hits else "pass", spec.severity,
                  f"{len(hits)} forbidden pattern hit(s)" if hits else "no forbidden patterns",
                  evidence=hits[:8])


# ---------------------------------------------------------------- terminology consistency (LLM)

TERM_PROMPT = """Key source term: "{term}"

Find every place in the TARGET document where this source term (or the concept it names) is
translated. List each DISTINCT target-language rendering, with one sentence copied EXACTLY from
the target document as evidence. Inflection (singular/plural, gender, case) of the same word is
the SAME rendering; different words (synonyms, e.g. "comprimido" vs "tableta" vs "pastilla") are
DIFFERENT renderings.

Reply with JSON only:
{{"renderings": [{{"rendering": "<target word(s)>", "evidence": "<exact target sentence>"}}], "consistent": true|false}}"""


@check("term_consistency_llm")
def term_consistency_llm(spec: TestSpec, ctx: Context) -> Result:
    """A recurring source term must be rendered ONE way throughout the target document.
    Language-agnostic: the judge discovers the renderings (no glossary needed).
    Uses source + target together, because the question is cross-lingual."""
    if ctx.mode == "source":
        return Result(spec.id, spec.type, "skip", spec.severity, "target-language check")
    term = spec.params["term"]
    doc = (f"<source lang=\"{ctx.source.lang}\">\n{ctx.source.text.strip()}\n</source>\n\n"
           f"<target lang=\"{ctx.target.lang}\">\n{ctx.target.text.strip()}\n</target>\n\n")
    out = chat_json(_doc_messages(ctx, TERM_PROMPT.format(term=term), doc=doc),
                    system=SYSTEM, max_tokens=600, model=JUDGE_MODEL)
    rends = [r for r in out.get("renderings", []) if _grounded(r.get("evidence", ""), ctx.target.text)]
    distinct = sorted({str(r.get("rendering", "")).strip().lower() for r in rends if r.get("rendering")})
    bad = (out.get("consistent") is False) and len(distinct) >= 2
    return Result(spec.id, spec.type, "fail" if bad else "pass", spec.severity,
                  f"'{term}' rendered as: {distinct}" if bad else f"'{term}' consistent: {distinct}",
                  evidence=[r.get("evidence", "") for r in rends] if bad else [], details=out)
