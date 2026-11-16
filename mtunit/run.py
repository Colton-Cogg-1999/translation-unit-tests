"""Unit-test MT/LLM engines with an AI-generated capability suite, and compare with segment-level QE.

  uv run python -m mtunit.run [--per-cap 8] [--engines a,b,c]

Outputs (results/mtunit/): suite.generated.json, suite.json (validated), validation.json,
runs/<engine>__<mode>.json, junit/<engine>__<mode>.xml, report.md, qe_misses.md
"""

from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from xml.sax.saxutils import escape

from common.llm import JUDGE_MODEL, describe
from transtest.segqe import flagged, qe_segment

from .assertions import evaluate_case
from .capabilities import CAPABILITIES
from .engines import translate_case
from .generate import GEN_MODEL, GOLD_MODEL, generate, validate

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "mtunit"
DEFAULT_ENGINES = "meta-llama/llama-4-scout,openai/gpt-5.4-nano,openai/gpt-5.4-mini"
MODES = ["segment", "document"]


def slug(m: str) -> str:
    return m.split("/")[-1]


def run_engine(cases: list[dict], model: str, mode: str) -> list[dict]:
    def one(case):
        try:
            tgt = translate_case(case, model, mode)
        except Exception as e:
            tgt = [""] * len(case["segments"])
            print(f"  translate failed {case['id']} {model} {mode}: {e}")
        res = evaluate_case(case, case["segments"], tgt)
        qe = [qe_segment(s, t) for s, t in zip(case["segments"], tgt)]
        return {"id": case["id"], "capability": case["capability"], "cross_segment": case["cross_segment"],
                "domain": case["domain"], "src": case["segments"], "tgt": tgt, "assertions": case["assertions"],
                "results": res, "qe": qe, "qe_flagged": [flagged(q) for q in qe]}
    with ThreadPoolExecutor(8) as ex:
        return list(ex.map(one, cases))


def case_status(r: dict) -> str:
    st = [x["status"] for x in r["results"]]
    if "fail" in st:
        return "fail"
    if all(s == "pass" for s in st):
        return "pass"
    return "unverified"


def failed_assertions(r: dict) -> list[tuple[dict, dict]]:
    return [(a, x) for a, x in zip(r["assertions"], r["results"]) if x["status"] == "fail"]


def qe_caught(r: dict, a: dict) -> bool:
    seg = a.get("segment")
    if seg in (None, "", 0) or a.get("kind") == "preserve":
        return any(r["qe_flagged"])
    i = int(seg) - 1
    return 0 <= i < len(r["qe_flagged"]) and r["qe_flagged"][i]


def junit(rows: list[dict], name: str) -> str:
    tc = []
    for r in rows:
        st = case_status(r)
        body = ""
        if st == "fail":
            msg = "; ".join(f"{a.get('kind')}: {x['detail']}" for a, x in failed_assertions(r))
            body = f'<failure message="{escape(msg, {chr(34): "&quot;"})}">{escape(json.dumps(r["tgt"], ensure_ascii=False))}</failure>'
        elif st == "unverified":
            body = '<skipped message="judge evidence not grounded"/>'
        tc.append(f'  <testcase classname="{r["capability"]}" name="{r["id"]}">{body}</testcase>')
    fails = sum(case_status(r) == "fail" for r in rows)
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<testsuite name="{escape(name)}" tests="{len(rows)}" '
            f'failures="{fails}">\n' + "\n".join(tc) + "\n</testsuite>\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-cap", type=int, default=8)
    ap.add_argument("--engines", default=os.environ.get("L10N_MTUNIT_ENGINES", DEFAULT_ENGINES))
    a = ap.parse_args()
    engines = [e.strip() for e in a.engines.split(",") if e.strip()]
    for d in ("runs", "junit"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    print(describe(), f"generator={GEN_MODEL} gold={GOLD_MODEL} engines={engines}", flush=True)

    gen_p, suite_p = OUT / "suite.generated.json", OUT / "suite.json"
    cases = json.loads(gen_p.read_text()) if gen_p.exists() else generate(a.per_cap, gen_p)
    print(f"generated {len(cases)} cases", flush=True)
    if suite_p.exists():
        suite = json.loads(suite_p.read_text())
        stats = json.loads((OUT / "validation.json").read_text())
    else:
        suite, stats = validate(cases, suite_p)
        (OUT / "validation.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    print(f"validated: {stats['valid_cases']}/{stats['generated_cases']} cases, "
          f"{stats['valid_assertions']}/{stats['generated_assertions']} assertions", flush=True)

    runs = {}
    for eng in engines:
        for mode in MODES:
            key = f"{slug(eng)}__{mode}"
            rows = run_engine(suite, eng, mode)
            runs[key] = rows
            (OUT / "runs" / f"{key}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
            (OUT / "junit" / f"{key}.xml").write_text(junit(rows, key))
            p = sum(case_status(r) == "pass" for r in rows)
            print(f"  {key:32} pass {p}/{len(rows)}", flush=True)

    # ------------------------------------------------------------ report
    keys = list(runs)
    caps = list(CAPABILITIES)

    def rate(rows):
        dec = [r for r in rows if case_status(r) != "unverified"]
        return sum(case_status(r) == "pass" for r in dec), len(dec)

    md = ["# Engine unit tests: AI-generated capability suite (EN→ES)", "",
          f"Suite generated by **{GEN_MODEL}**, validated against a gold translation by **{GOLD_MODEL}**; "
          f"assertions judged by **{JUDGE_MODEL}**. Segment QE = MQM-style per-segment evaluation by the same judge.", "",
          f"Validation kept **{stats['valid_cases']}/{stats['generated_cases']} cases** and "
          f"**{stats['valid_assertions']}/{stats['generated_assertions']} assertions** (assertions that failed on the "
          f"gold translation were dropped as wrong or too strict).", "",
          "## Test dashboard: case pass rate by capability", "",
          "| capability | cross-segment? | " + " | ".join(keys) + " |", "|---|---|" + "---|" * len(keys)]
    for cap in caps:
        cells = []
        for k in keys:
            p, n = rate([r for r in runs[k] if r["capability"] == cap])
            cells.append(f"{p}/{n}" if n else "–")
        md.append(f"| {cap} | {'yes' if CAPABILITIES[cap]['cross_segment'] else ''} | " + " | ".join(cells) + " |")
    for label, f in [("**segment-local total**", lambda r: not r["cross_segment"]),
                     ("**cross-segment total**", lambda r: r["cross_segment"])]:
        cells = []
        for k in keys:
            p, n = rate([r for r in runs[k] if f(r)])
            cells.append(f"**{p}/{n} ({100 * p / max(1, n):.0f}%)**")
        md.append(f"| {label} | | " + " | ".join(cells) + " |")

    # QE comparison over all failed assertions
    md += ["", "## Would segment-level QE have caught these failures?", "",
           "For every failed assertion: did segment QE flag (major/critical) the segment the assertion is about?", "",
           "| capability | cross-segment? | failed assertions (all engines/modes) | caught by segment QE | missed by segment QE |",
           "|---|---|---|---|---|"]
    misses = []
    tot = {True: [0, 0], False: [0, 0]}
    for cap in caps:
        n = c = 0
        for k in keys:
            for r in runs[k]:
                if r["capability"] != cap:
                    continue
                for a_, x in failed_assertions(r):
                    n += 1
                    if qe_caught(r, a_):
                        c += 1
                    else:
                        misses.append((k, r, a_, x))
        cs = CAPABILITIES[cap]["cross_segment"]
        tot[cs][0] += n
        tot[cs][1] += c
        md.append(f"| {cap} | {'yes' if cs else ''} | {n} | {c} ({100 * c / max(1, n):.0f}%) | {n - c} |")
    for cs, label in [(False, "**segment-local total**"), (True, "**cross-segment total**")]:
        n, c = tot[cs]
        md.append(f"| {label} | | **{n}** | **{c} ({100 * c / max(1, n):.0f}%)** | **{n - c}** |")

    # QE false alarms on passing cases
    pas = [(k, r) for k in keys for r in runs[k] if case_status(r) == "pass"]
    fa = sum(any(r["qe_flagged"]) for _, r in pas)
    md += ["", f"Segment QE flagged at least one segment in **{fa}/{len(pas)}** cases that passed every unit test "
               f"(either QE noise or issues outside the tested capability)."]
    (OUT / "report.md").write_text("\n".join(md), encoding="utf-8")

    ex = ["# Failures that segment-level QE missed (sample)", ""]
    for k, r, a_, x in sorted(misses, key=lambda m: (not m[1]["cross_segment"], m[1]["capability"]))[:40]:
        ex += [f"### {r['id']} · {k} · {r['capability']}", "",
               "| # | source | translation | segment QE |", "|---|---|---|---|"]
        for i, (s, t, q) in enumerate(zip(r["src"], r["tgt"], r["qe_flagged"])):
            ex.append(f"| {i + 1} | {s} | {t} | {'flagged' if q else 'ok'} |")
        ex += ["", f"**Failed assertion** ({a_.get('kind')}, segment {a_.get('segment')}): "
                   f"{a_.get('property') or a_.get('any_of') or a_.get('strings')}  ", f"→ {x['detail']}", ""]
    (OUT / "qe_misses.md").write_text("\n".join(ex), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
