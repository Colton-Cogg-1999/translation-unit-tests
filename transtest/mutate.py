"""Mutation testing for translation test suites.

Take a translation you trust, apply ONE small meaning-breaking edit (a "mutant"), and
check whether the suite fails ("kills" it). Mutation score = killed / total.
A suite that lets mutants survive has blind spots — exactly like code mutation testing.

Operators are deterministic regex edits (currently tuned for Spanish targets).
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from .model import Document, Suite
from .runner import run_suite, summarise


@dataclass
class Mutant:
    op: str
    before: str
    after: str
    text: str


def _body_lines(text: str) -> list[int]:
    lines = text.splitlines()
    return [i for i, l in enumerate(lines) if l.strip() and not l.lstrip().startswith("#")]


def _apply_on_line(text: str, rng: random.Random, pattern: str, repl, flags=0):
    lines = text.splitlines()
    cands = [i for i in _body_lines(text) if re.search(pattern, lines[i], flags)]
    if not cands:
        return None
    i = rng.choice(cands)
    before = lines[i]
    after = re.sub(pattern, repl, before, count=1, flags=flags)
    if after == before:
        return None
    lines[i] = after
    return before, after, "\n".join(lines) + "\n"


def op_number(text, rng, suite):
    def bump(m):
        n = m.group(0)
        return str(int(n) * 2) if n.isdigit() and int(n) > 1 else str(int(n) + 1) if n.isdigit() else n
    return _apply_on_line(text, rng, r"(?<![\d.,])\d+(?![\d.,]\d)", bump)


def op_drop_sentence(text, rng, suite):
    lines = text.splitlines()
    i = rng.choice(_body_lines(text))
    before = lines.pop(i)
    return before, "", "\n".join(lines) + "\n"


def op_and_or(text, rng, suite):
    return _apply_on_line(text, rng, r"\by\b(?= (?:es|está|tiene|el|la|un|una|\w+))", "o")


def op_negation_drop(text, rng, suite):
    r = _apply_on_line(text, rng, r"^No (\w)", lambda m: m.group(1).upper())
    return r or _apply_on_line(text, rng, r"\bno ", "")


def op_comparative(text, rng, suite):
    swaps = {"más de": "menos de", "menos de": "más de", "al menos": "como máximo",
             "menores de": "mayores de", "mayores de": "menores de", "mayor de": "menor de",
             "superior a": "inferior a", "incluso si": "solo si", "antes de": "después de"}
    pat = "|".join(map(re.escape, swaps))
    return _apply_on_line(text, rng, pat, lambda m: swaps[m.group(0)])


def op_term_swap(text, rng, suite):
    for g in rng.sample(suite.glossary, len(suite.glossary)):
        for ok in g.get("target", []):
            if g.get("forbidden"):
                r = _apply_on_line(text, rng, rf"\b{re.escape(ok)}\b", rng.choice(g["forbidden"]))
                if r:
                    return r
    return None


def op_register(text, rng, suite):
    swaps = {"su médico": "tu médico", "Consulte": "Consulta", "No tome": "No tomes", "Tome": "Toma",
             "Trague": "Traga", "Lea": "Lee", "Evite": "Evita"}
    pat = "|".join(map(re.escape, swaps))
    return _apply_on_line(text, rng, pat, lambda m: swaps[m.group(0)])


OPERATORS = {
    "number": op_number, "drop_sentence": op_drop_sentence, "and_or": op_and_or,
    "negation_drop": op_negation_drop, "comparative": op_comparative,
    "term_swap": op_term_swap, "register": op_register,
}


def make_mutants(text: str, suite: Suite, per_op: int = 2, seed: int = 0) -> list[Mutant]:
    rng = random.Random(seed)
    out, seen = [], set()
    for name, fn in OPERATORS.items():
        for _ in range(per_op * 4):
            if sum(m.op == name for m in out) >= per_op:
                break
            r = fn(text, rng, suite)
            if r and r[2] not in seen:
                seen.add(r[2])
                out.append(Mutant(name, r[0], r[1], r[2]))
    return out


def mutation_test(suite: Suite, good_target: Document, per_op: int = 2, seed: int = 0) -> dict:
    mutants = make_mutants(good_target.text, suite, per_op, seed)
    rows = []
    for m in mutants:
        res = run_suite(suite, Document(m.text, good_target.lang))
        killers = [r.test_id for r in res if r.status == "fail"]
        rows.append({"op": m.op, "before": m.before, "after": m.after,
                     "killed": bool(killers), "killed_by": killers, "summary": summarise(res)})
    by_op = {}
    for r in rows:
        k = by_op.setdefault(r["op"], [0, 0])
        k[0] += r["killed"]
        k[1] += 1
    return {"mutation_score": round(sum(r["killed"] for r in rows) / max(1, len(rows)), 3),
            "by_operator": {k: f"{a}/{b}" for k, (a, b) in by_op.items()}, "mutants": rows}
