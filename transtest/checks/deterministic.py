"""Deterministic (rule-based) checks: cheap, exact, no model needed."""

from __future__ import annotations

import re
from collections import Counter

from ..model import Result, TestSpec
from . import Context, check

# ---------------------------------------------------------------- numbers

_NUM_RE = re.compile(r"(?<![\w.,])\d{1,3}(?:[.,   ]\d{3})+(?:[.,]\d+)?(?![\w])|(?<![\w.,])\d+(?:[.,]\d+)?(?![\w])")


def _normalise_number(tok: str) -> str:
    """Locale-agnostic normalisation: '1,000.5' / '1.000,5' / '1 000,5' -> '1000.5'."""
    t = tok.replace(" ", "").replace(" ", "").replace(" ", "")
    if "," in t and "." in t:
        dec = "," if t.rfind(",") > t.rfind(".") else "."
        thou = "." if dec == "," else ","
        t = t.replace(thou, "").replace(dec, ".")
    elif "," in t or "." in t:
        sep = "," if "," in t else "."
        head, _, tail = t.rpartition(sep)
        if t.count(sep) > 1 or (len(tail) == 3 and head != "0"):
            t = t.replace(sep, "")  # thousands: 1.000.000 / ambiguous 1,000 -> 1000
        else:
            t = t.replace(sep, ".")  # decimal: 0,5 / 2.5
    try:
        f = float(t)
        return str(int(f)) if f.is_integer() else str(f)
    except ValueError:
        return t


def extract_numbers(text: str) -> Counter:
    return Counter(_normalise_number(m.group(0)) for m in _NUM_RE.finditer(text))


@check("numbers")
def numbers(spec: TestSpec, ctx: Context) -> Result:
    """Every number in the source must appear in the target (same multiset)."""
    ignore = {str(x) for x in spec.params.get("ignore", [])}
    src = extract_numbers(ctx.source.text)
    tgt = extract_numbers(ctx.doc_under_test.text)
    for k in ignore:
        src.pop(k, None)
        tgt.pop(k, None)
    missing = src - tgt
    extra = tgt - src
    ok = not missing and (not extra or not spec.params.get("strict_extra", True))
    msg = []
    if missing:
        msg.append("missing in target: " + ", ".join(f"{k}×{v}" for k, v in missing.items()))
    if extra:
        msg.append("unexpected in target: " + ", ".join(f"{k}×{v}" for k, v in extra.items()))
    return Result(spec.id, spec.type, "pass" if ok else "fail", spec.severity,
                  "; ".join(msg) or f"{sum(src.values())} numbers preserved",
                  details={"missing": dict(missing), "extra": dict(extra)})


# ---------------------------------------------------------------- placeholders / markup

_PH_RE = re.compile(r"\{[^{}\s]+\}|%\d*\$?[sdif]|<[^<>]+>|\[\[[^\]]+\]\]|\$\{[^}]+\}")


@check("placeholders")
def placeholders(spec: TestSpec, ctx: Context) -> Result:
    src = Counter(_PH_RE.findall(ctx.source.text))
    tgt = Counter(_PH_RE.findall(ctx.doc_under_test.text))
    missing, extra = src - tgt, tgt - src
    ok = not missing and not extra
    return Result(spec.id, spec.type, "pass" if ok else "fail", spec.severity,
                  "placeholders/tags intact" if ok else
                  f"missing={dict(missing)} extra={dict(extra)}")


# ---------------------------------------------------------------- do-not-translate

@check("dnt")
def dnt(spec: TestSpec, ctx: Context) -> Result:
    """Do-not-translate strings must appear verbatim as often as in the source."""
    terms = spec.params.get("terms") or ctx.suite.dnt
    problems = []
    for term in terms:
        n_src = ctx.source.text.count(term)
        n_tgt = ctx.doc_under_test.text.count(term)
        if n_tgt < n_src:
            problems.append(f"{term!r}: {n_src} in source, {n_tgt} in target")
    return Result(spec.id, spec.type, "fail" if problems else "pass", spec.severity,
                  "; ".join(problems) or f"{len(terms)} DNT terms preserved")


# ---------------------------------------------------------------- glossary + term consistency

def _count_word(text: str, word: str) -> int:
    return len(re.findall(rf"(?<!\w){re.escape(word)}(?!\w)", text, flags=re.IGNORECASE))


@check("glossary")
def glossary(spec: TestSpec, ctx: Context) -> Result:
    """Approved target terms must be used; forbidden variants must not appear."""
    if ctx.mode == "source":
        return Result(spec.id, spec.type, "skip", spec.severity, "target-language check")
    problems, evidence = [], []
    text = ctx.target.text
    for entry in ctx.suite.glossary:
        src_n = _count_word(ctx.source.text, entry["source"])
        if src_n == 0:
            continue
        approved = entry.get("target", [])
        approved = [approved] if isinstance(approved, str) else approved
        tgt_n = sum(_count_word(text, t) for t in approved)
        for bad in entry.get("forbidden", []):
            n = _count_word(text, bad)
            if n:
                problems.append(f"forbidden {bad!r} used {n}× (approved: {approved})")
                evidence += [s for s in ctx.target.sentences if _count_word(s, bad)][:3]
        if tgt_n == 0:
            problems.append(f"{entry['source']!r} occurs {src_n}× in source but approved {approved} never used")
    return Result(spec.id, spec.type, "fail" if problems else "pass", spec.severity,
                  "; ".join(problems) or "glossary respected", evidence=evidence)


@check("term_consistency")
def term_consistency(spec: TestSpec, ctx: Context) -> Result:
    """A source term should be rendered by ONE target variant throughout the document.

    params.terms: list of {source: str, variants: [str, ...]} — the candidate renderings
    to watch for. If omitted, glossary entries (target + forbidden) are used.
    This is invisible to segment-level QE: each segment is fine in isolation.
    """
    if ctx.mode == "source":
        return Result(spec.id, spec.type, "skip", spec.severity, "target-language check")
    terms = spec.params.get("terms") or [
        {"source": g["source"], "variants": list(g.get("target", [])) + list(g.get("forbidden", []))}
        for g in ctx.suite.glossary
    ]
    problems, evidence = [], []
    for t in terms:
        # group inflections: variants listed together as "a|b" count as one rendering
        groups = [v.split("|") for v in t["variants"]]
        used = {}
        for g in groups:
            n = sum(_count_word(ctx.target.text, v) for v in g)
            if n:
                used[g[0]] = n
        if len(used) > 1:
            problems.append(f"{t['source']!r} rendered inconsistently: {used}")
            for g in groups:
                for s in ctx.target.sentences:
                    if any(_count_word(s, v) for v in g):
                        evidence.append(s)
                        break
    return Result(spec.id, spec.type, "fail" if problems else "pass", spec.severity,
                  "; ".join(problems) or "terms rendered consistently", evidence=evidence)


@check("length_ratio")
def length_ratio(spec: TestSpec, ctx: Context) -> Result:
    lo, hi = spec.params.get("min", 0.8), spec.params.get("max", 1.6)
    r = len(ctx.doc_under_test.text) / max(1, len(ctx.source.text))
    ok = lo <= r <= hi
    return Result(spec.id, spec.type, "pass" if ok else "fail", spec.severity,
                  f"target/source char ratio {r:.2f} (allowed {lo}–{hi})")
