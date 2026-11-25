"""Plant one error per document variant, verify each one independently, and keep a balanced sample.

  uv run python -m benchmark.plant [--limit-docs N]

Edits are verified in a seeded order that spreads them across documents, only until MAX_PER_CELL per error type
pass (verification is the expensive step). Writes results/benchmark/candidates.jsonl (every verified edit, kept
or rejected, with the reason) and results/benchmark/variants.jsonl (the kept sample).
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from rapidfuzz import fuzz

from common import llm
from common.llm import chat_json

from . import budget, config
from .corpus import DOMAINS, Doc, load_leaflets, load_synthetic
from .taxonomy import ERROR_TYPES

OUT = Path(__file__).resolve().parent.parent / "results" / "benchmark"

PLANT_PROMPT = """You are building a benchmark of translation errors, to test translation quality checkers. Below is {domain}
in English with its correct Spanish (Spain) translation, split into numbered segments.

{numbered}

Plant this kind of error: {etype}
{definition}

Propose up to {k} different edits, each in a DIFFERENT segment. Each edit changes ONE Spanish segment and must:
- introduce exactly one error of this kind, with no other change to wording or meaning;
- leave the segment fluent, grammatical Spanish;
- be a mistake a real translator or MT engine could plausibly make.
{family_rule}
If no segment fits this kind of error naturally, return an empty list. Do not force it.

Reply with JSON only:
{{"edits": [{{"segment": <number>, "edited": "<the full edited Spanish segment>", "evidence_segments": [<numbers of the segments that show the error>], "description": "<one sentence in English: what changed and why it is wrong>"}}]}}"""

FAMILY_RULE = {
    "cross": ("- The error must be IMPOSSIBLE to detect from the edited segment and its own English source segment "
              "alone. The evidence is in another segment, which you list in evidence_segments."),
    "local": "- The error must be detectable by comparing the edited segment with its own English source segment.",
}

VERIFY_PROMPT = """You are auditing one planted error in a translation-error benchmark.

Document: English source and the ORIGINAL, correct Spanish translation, in numbered segments:
{numbered}

The edit changed segment {n}:
  original: {original}
  edited:   {edited}
Claimed error type: {etype}. {definition}

Answer each question independently:
1. one_error: Does the edit introduce exactly one error, of the claimed type, and no other change in meaning or quality?
2. fluent_alone: Reading ONLY the edited Spanish segment, is it fluent, grammatical Spanish?
3. visible_alone: Reading ONLY English source segment {n} and the edited Spanish segment {n}, and ignoring every other
   segment, could a careful bilingual reviewer tell that the edited segment is wrong?

Reply with JSON only: {{"one_error": true|false, "fluent_alone": true|false, "visible_alone": true|false, "reason": "<one sentence>"}}"""


def plant(doc: Doc, etype: str, k: int) -> list[dict]:
    t = ERROR_TYPES[etype]
    out = chat_json(PLANT_PROMPT.format(domain=DOMAINS[doc.domain], numbered=doc.numbered(), etype=etype,
                                        definition=t["definition"], k=k, family_rule=FAMILY_RULE[t["family"]]),
                    model=config.PLANT_MODEL, reasoning_effort=config.PLANT_EFFORT, max_tokens=3000)
    edits = out.get("edits", []) if isinstance(out, dict) else []
    cands, seen = [], set()
    for e in edits[:k]:
        try:
            n = int(e["segment"])
        except (KeyError, TypeError, ValueError):
            continue
        if n in seen:
            continue
        seen.add(n)
        cands.append({"doc": doc.id, "corpus": doc.corpus, "type": etype, "family": t["family"], "segment": n,
                      "edited": str(e.get("edited", "")).strip(), "evidence_segments": e.get("evidence_segments", []),
                      "description": str(e.get("description", ""))})
    return cands


def check(doc: Doc, c: dict) -> dict:
    """Deterministic checks, then the independent LLM verification. Adds `keep` and `reject_reason`."""
    n = c["segment"]
    if not 1 <= n <= len(doc.tgt):
        return {**c, "keep": False, "reject_reason": "segment out of range"}
    orig = doc.tgt[n - 1]
    c = {**c, "original": orig}
    if not c["edited"] or c["edited"] == orig or "\n" in c["edited"]:
        return {**c, "keep": False, "reject_reason": "empty or unchanged edit"}
    if fuzz.ratio(orig, c["edited"]) < 50:
        return {**c, "keep": False, "reject_reason": "edit rewrote the segment"}
    t = ERROR_TYPES[c["type"]]
    v = chat_json(VERIFY_PROMPT.format(numbered=doc.numbered(), n=n, original=orig, edited=c["edited"],
                                       etype=c["type"], definition=t["definition"]),
                  model=config.PLANT_MODEL, reasoning_effort=config.PLANT_EFFORT, max_tokens=600)
    v = v if isinstance(v, dict) else {}
    want_visible = t["family"] == "local"
    reason = ("not exactly one error of this type" if not v.get("one_error") else
              "not fluent on its own" if not v.get("fluent_alone") else
              ("not visible from its own segment" if want_visible else "visible from its own segment")
              if bool(v.get("visible_alone")) != want_visible else None)
    return {**c, "verification": v, "keep": reason is None, "reject_reason": reason}


def queues(cands: list[dict], seed: int) -> dict[tuple, list[dict]]:
    """Per corpus x type, the proposed edits in a seeded order that spreads them across documents (round-robin).
    An edit proposed under two types (e.g. mistranslation and condition) is kept under the first type only."""
    rng = random.Random(seed)
    cells: dict[tuple, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    seen = set()
    order = {t: i for i, t in enumerate(ERROR_TYPES)}
    for c in sorted(cands, key=lambda c: (c["doc"], c["segment"], order[c["type"]])):
        sig = (c["doc"], c["segment"], " ".join(c["edited"].split()))
        if sig in seen:
            continue
        seen.add(sig)
        cells[(c["corpus"], c["type"])][c["doc"]].append(c)
    out = {}
    for key in sorted(cells):
        by_doc = cells[key]
        docs = sorted(by_doc)
        rng.shuffle(docs)
        for d in docs:
            rng.shuffle(by_doc[d])
        q, rnd = [], 0
        while any(len(by_doc[d]) > rnd for d in docs):
            q += [by_doc[d][rnd] for d in docs if len(by_doc[d]) > rnd]
            rnd += 1
        out[key] = q
    return out


def verify_until_full(q: list[dict], by_id: dict, cap: int, batch: int) -> tuple[list[dict], list[dict]]:
    """Verify edits in queue order until `cap` pass. Returns (checked, kept); edits after that stay unverified."""
    checked, kept, i = [], [], 0
    while len(kept) < cap and i < len(q):
        chunk = q[i: i + batch]
        i += len(chunk)
        with ThreadPoolExecutor(batch) as ex:
            res = list(ex.map(lambda c: check(by_id[c["doc"]], c), chunk))
        checked += res
        kept += [c for c in res if c["keep"]]
    kept = kept[:cap]
    for c in kept:
        c["id"] = f"{c['doc']}::{c['type']}::{c['segment']}"
    return checked, kept


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-docs", type=int, default=0, help="pilot: only the first N documents of each corpus")
    ap.add_argument("--stop-at", type=float, help="lower spending cap (USD, all benchmark calls) for this step")
    a = ap.parse_args(argv)
    if a.stop_at:
        config.BUDGET_USD = min(config.BUDGET_USD, a.stop_at)
    llm.use_openai(config.DETECT_EFFORT)
    budget.install()
    print(f"spent so far: ${budget.spent():.2f} of ${config.BUDGET_USD:.2f}", flush=True)
    docs = [d for d in load_synthetic() + load_leaflets() if d.corpus in config.CORPORA]
    if a.limit_docs:
        docs = [d for c in ("synthetic", "leaflet") for d in [x for x in docs if x.corpus == c][: a.limit_docs]]
    by_id = {d.id: d for d in docs}
    jobs = [(d, t, config.CANDIDATES_PER_DOC[d.corpus]) for d in docs for t in ERROR_TYPES]
    print(f"planting: {len(docs)} documents x {len(ERROR_TYPES)} error types = {len(jobs)} requests", flush=True)
    with ThreadPoolExecutor(config.WORKERS) as ex:
        cands = [c for lst in ex.map(lambda j: plant(*j), jobs) for c in lst]
    checked, variants = [], []
    for key, q in queues(cands, config.SEED).items():
        ch, kept = verify_until_full(q, by_id, config.MAX_PER_CELL, config.VERIFY_BATCH)
        checked += ch
        variants += kept
        print(f"  {key[0]}:{key[1]:15} {len(kept):3} kept of {len(ch)} verified ({len(q)} proposed)", flush=True)
    variants.sort(key=lambda c: c["id"])
    OUT.mkdir(parents=True, exist_ok=True)
    suffix = "" if not a.limit_docs else ".pilot"
    for name, rows in ((f"candidates{suffix}.jsonl", checked), (f"variants{suffix}.jsonl", variants)):
        (OUT / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"{len(cands)} edits proposed, {len(checked)} verified, {len(variants)} variants kept; "
          f"spent ${budget.spent():.2f}", flush=True)


if __name__ == "__main__":
    main()
