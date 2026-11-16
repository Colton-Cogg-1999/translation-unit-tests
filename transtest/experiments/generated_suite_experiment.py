"""Project 1: do AI-generated document test suites catch what segment-level QE misses?

  uv run python -m transtest.experiments.generated_suite_experiment

Per real EMEA leaflet (data/leaflets/<doc>/):
  1. GENERATE a suite from the English source only (no human-written tests), prune it on the source.
  2. TRANSLATE segment by segment (no context) with several LLMs  → natural errors.
  3. PLANT one error of each type into the human reference         → known ground truth.
     + a NULL control (meaning-identical) to measure false detections.
  4. Run the generated suite (document level) AND segment-level MQM QE on every target.
  5. Planted: detection rate per error type for each method.
     Natural: an independent adjudicator decides which flags are real errors and groups flags
     that describe the same underlying error → found by tests only / QE only / both.
Writes results/p1_generated/{report.md, summary.json, review.md, <doc>/...}.
"""

from __future__ import annotations

import argparse
import json
import os
import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path

from rapidfuzz import fuzz

from common.llm import JUDGE_MODEL, chat, chat_json, clean_translation, describe
from transtest.generate import GEN_MODEL, generate_suite, prune_on_source
from transtest.inject import ERROR_TYPES, INJECT_MODEL, plant
from transtest.model import Document, Suite
from transtest.runner import run_suite, summarise
from transtest.segqe import qe_document

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "leaflets"
OUT = ROOT / "results" / "p1_generated"
MT_MODELS = [m.strip() for m in os.environ.get(
    "L10N_P1_MT_MODELS", "openai/gpt-5.4-nano,meta-llama/llama-4-scout").split(",") if m.strip()]
ADJ_MODEL = os.environ.get("L10N_ADJUDICATE_MODEL", "openai/gpt-5.4")

MT_SYS = ("You are a machine translation engine. Translate the user's text from English to Spanish (Spain). "
          "The text is one segment of a medicine package leaflet. Output only the translation.")


def slug(m: str) -> str:
    return m.split("/")[-1].replace(":", "-")


def lines_of(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").rstrip("\n").split("\n")


# ------------------------------------------------------------------ per-document pipeline

def build_targets(doc: str, src_lines: list[str], ref_lines: list[str], d: Path) -> dict[str, dict]:
    tdir = d / "targets"
    tdir.mkdir(parents=True, exist_ok=True)
    targets: dict[str, dict] = {"reference": {"kind": "reference", "lines": ref_lines}}

    # natural: segment-by-segment MT, no context (like a TMS pipeline)
    for m in MT_MODELS:
        p = tdir / f"mt_{slug(m)}.es.md"
        if not p.exists():
            with ThreadPoolExecutor(8) as ex:
                out = list(ex.map(lambda s: clean_translation(chat(s, system=MT_SYS, model=m, max_tokens=400)),
                                  src_lines))
            p.write_text("\n".join(out) + "\n", encoding="utf-8")
        targets[f"mt_{slug(m)}"] = {"kind": "mt", "model": m, "lines": lines_of(p)}

    # planted: one error per type into the human reference (+ null control)
    manifest_p = d / "planted.json"
    manifest = json.loads(manifest_p.read_text()) if manifest_p.exists() else {}
    for et in ERROR_TYPES:
        if et not in manifest:
            try:
                r = plant(src_lines, ref_lines, et)
            except Exception as e:
                print(f"  [{doc}] plant {et} failed: {e}")
                r = None
            if r:
                manifest[et] = r
    manifest_p.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    for et, r in manifest.items():
        targets[f"planted_{et}"] = {"kind": "planted", "lines": r["text_lines"], "plant": r}
    targets["planted_null"] = {"kind": "null", "lines": ref_lines, "null": True}
    return targets


def doc_text(lines: list[str], null: bool = False) -> str:
    # null control: identical segments, but the document text differs by layout only
    # (blank line inserted mid-document), so every judge prompt is fresh.
    if null:
        mid = len(lines) // 2
        return "\n".join(lines[:mid]) + "\n\n" + "\n".join(lines[mid:]) + "\n"
    return "\n".join(lines) + "\n"


def run_document(doc: str) -> dict:
    d_in, d = DATA / doc, OUT / doc
    d.mkdir(parents=True, exist_ok=True)
    src_lines, ref_lines = lines_of(d_in / "source.en.md"), lines_of(d_in / "reference.es.md")

    # 1. generate + prune (AI-written suite, from the source only)
    gen_p, pruned_p = d / "suite.generated.yaml", d / "suite.yaml"
    if not gen_p.exists():
        generate_suite(d_in / "source.en.md", "es", gen_p)
    n_kept, broken = prune_on_source(gen_p, pruned_p)
    suite = Suite.load(pruned_p)
    print(f"[{doc}] suite: {len(suite.tests)} tests ({len(broken)} pruned on source)", flush=True)

    # 2./3. targets
    targets = build_targets(doc, src_lines, ref_lines, d)

    # 4. run both methods on every target
    rows = {}
    for name, t in targets.items():
        tgt_doc = Document(doc_text(t["lines"], t.get("null", False)), "es")
        res = run_suite(suite, tgt_doc)
        qe = qe_document(src_lines, t["lines"])
        rows[name] = {"kind": t["kind"], "results": [asdict(r) for r in res], "summary": summarise(res),
                      "segqe": qe, "plant": t.get("plant"), "model": t.get("model")}
        print(f"[{doc}] {name:28} tests failed={rows[name]['summary']['failed']:2}  "
              f"segQE flagged={sum(q['flagged'] for q in qe):2}", flush=True)
    (d / "runs.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"doc": doc, "n_tests": len(suite.tests), "pruned": broken, "rows": rows,
            "src_lines": src_lines, "ref_lines": ref_lines}


# ------------------------------------------------------------------ scoring

def failing(row) -> set[str]:
    return {r["test_id"] for r in row["results"] if r["status"] == "fail"}


DETERMINISTIC = {"numbers", "coverage", "placeholders", "dnt", "glossary", "term_consistency", "forbidden_patterns"}


def _norm(t: str) -> str:
    return " ".join(str(t).lower().split())


def new_failures(row: dict, ref: dict) -> list[dict]:
    """Tests that newly fail, or that already failed on the reference but now report NEW evidence."""
    ref_by = {r["test_id"]: r for r in ref["results"]}
    out = []
    for r in row["results"]:
        if r["status"] != "fail":
            continue
        rr = ref_by.get(r["test_id"])
        if rr is None or rr["status"] != "fail":
            out.append(r)
        else:
            old = {_norm(e) for e in rr["evidence"]}
            if any(_norm(e) not in old for e in r["evidence"] if e):
                out.append(r)
    return out


def attributed(r: dict, edited_after: list[str]) -> bool:
    """Does this failure point at the planted edit? (deterministic checks always count)"""
    if r["type"] in DETERMINISTIC:
        return True
    ev = [e for e in r.get("evidence", []) if e]
    ans = (r.get("details") or {}).get("answer") or {}
    if isinstance(ans, dict) and ans.get("evidence"):
        ev.append(ans["evidence"])
    for e in ev:
        for line in edited_after:
            if line and (fuzz.partial_ratio(_norm(line), _norm(e)) >= 85 or fuzz.partial_ratio(_norm(e), _norm(line)) >= 85):
                return True
    return False


def score_planted(D: dict) -> list[dict]:
    ref = D["rows"]["reference"]
    out = []
    for name, row in D["rows"].items():
        if row["kind"] not in ("planted", "null"):
            continue
        nf = new_failures(row, ref)
        if row["kind"] == "null":
            after = []
            qe_new = [q["line"] for q in row["segqe"] if q["flagged"] and not ref["segqe"][q["line"]]["flagged"]]
            att = [r for r in nf if r["type"] in DETERMINISTIC]
        else:
            after = row["plant"]["after"]
            ed = row["plant"]["lines"]
            qe_new = [i for i in ed if row["segqe"][i]["flagged"] and
                      (not ref["segqe"][i]["flagged"] or len(row["segqe"][i].get("errors", [])) > len(ref["segqe"][i].get("errors", [])))]
            att = [r for r in nf if attributed(r, after)]
        out.append({"doc": D["doc"], "type": name.removeprefix("planted_"),
                    "doc_level": (row["plant"] or {}).get("doc_level", False),
                    "description": (row["plant"] or {}).get("description", "null control"),
                    "tests_caught": bool(att), "tests_by": sorted(r["test_id"] for r in att),
                    "tests_unattributed": sorted(r["test_id"] for r in nf if r not in att),
                    "qe_caught": bool(qe_new), "qe_lines": qe_new})
    return out


ADJ_PROMPT = """You are a senior medical translator adjudicating automated QA flags on a machine translation.
You get the English SOURCE, the machine TRANSLATION (Spanish, produced segment by segment), and a
trusted human REFERENCE translation, all aligned by line number. Then two lists of flags:
T* = failures of document-level tests, S* = segment-level QE flags.

For EVERY flag decide whether it points to a REAL error in the machine translation (something a
reviewer would fix: meaning, omission, terminology inconsistency, wrong register for the genre,
wrong referent...). Style preferences that differ from the reference are NOT errors.
Then group the real flags that describe the SAME underlying error into issues.

Reply with JSON only:
{{"flags": {{"T1": {{"real": true|false, "why": "..."}}, "S1": {{...}}}},
  "issues": [{{"flags": ["T1","S3"], "severity": "minor|major|critical", "doc_level": true|false,
               "description": "..."}}]}}
An issue is doc_level if spotting it requires looking beyond the single segment (consistency
across segments, referents in earlier lines, conditions inherited from a lead-in line, register drift).

SOURCE:
{src}

MACHINE TRANSLATION:
{mt}

REFERENCE:
{ref}

T flags (document tests):
{tflags}

S flags (segment QE):
{sflags}"""


def adjudicate(D: dict, name: str) -> dict:
    row, ref = D["rows"][name], D["rows"]["reference"]
    ref_fail = failing(ref)
    num = lambda ls: "\n".join(f"{i + 1}: {l}" for i, l in enumerate(ls))
    t_items = [r for r in row["results"] if r["status"] == "fail" and r["test_id"] not in ref_fail]
    s_items = [q for q in row["segqe"] if q["flagged"]]
    tflags = "\n".join(f"T{k + 1}: [{r['test_id']}] {r['message'][:300]} | evidence: {' / '.join(r['evidence'][:3])[:300]}"
                       for k, r in enumerate(t_items)) or "(none)"
    sflags = "\n".join(f"S{k + 1}: line {q['line'] + 1}: " + "; ".join(
        f"{e.get('severity')} {e.get('category')}: {e.get('explanation', '')[:160]}" for e in q.get("errors", [])
        if str(e.get("severity", "")).lower() in ("major", "critical")) for k, q in enumerate(s_items)) or "(none)"
    if not t_items and not s_items:
        return {"flags": {}, "issues": [], "t_items": [], "s_items": []}
    out = chat_json(ADJ_PROMPT.format(src=num(D["src_lines"]), mt=num([q["tgt"] for q in row["segqe"]]),
                                      ref=num(D["ref_lines"]), tflags=tflags, sflags=sflags),
                    max_tokens=6000, model=ADJ_MODEL)
    out["t_items"] = [r["test_id"] for r in t_items]
    out["s_items"] = [q["line"] for q in s_items]
    return out


def score_natural(D: dict) -> list[dict]:
    out = []
    for name, row in D["rows"].items():
        if row["kind"] != "mt":
            continue
        try:
            adj = adjudicate(D, name)
        except Exception as e:
            print(f"  adjudication failed for {D['doc']}/{name}: {e}")
            adj = {"flags": {}, "issues": [], "t_items": [], "s_items": [], "error": str(e)}
        flags = adj.get("flags", {})
        real = lambda k: bool((flags.get(k) or {}).get("real"))
        n_t, n_s = len(adj.get("t_items", [])), len(adj.get("s_items", []))
        issues = []
        for iss in adj.get("issues", []):
            fl = [f for f in iss.get("flags", []) if real(f)]
            if not fl:
                continue
            issues.append({**iss, "flags": fl, "by_tests": any(f.startswith("T") for f in fl),
                           "by_qe": any(f.startswith("S") for f in fl)})
        out.append({"doc": D["doc"], "target": name, "model": row["model"],
                    "t_flags": n_t, "t_real": sum(real(f"T{k + 1}") for k in range(n_t)),
                    "s_flags": n_s, "s_real": sum(real(f"S{k + 1}") for k in range(n_s)),
                    "issues": issues, "adjudication": adj})
    return out


# ------------------------------------------------------------------ report

def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "–"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", nargs="*")
    ap.add_argument("--parallel-docs", type=int, default=3)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    docs = a.docs or sorted(p.name for p in DATA.iterdir() if p.is_dir())
    print(describe(), f"gen={GEN_MODEL} inject={INJECT_MODEL} adjudicate={ADJ_MODEL} mt={MT_MODELS}", flush=True)

    with ThreadPoolExecutor(a.parallel_docs) as ex:
        Ds = list(ex.map(run_document, docs))

    planted = [p for D in Ds for p in score_planted(D)]
    with ThreadPoolExecutor(4) as ex:
        natural = [n for lst in ex.map(score_natural, Ds) for n in lst]

    summary = {"models": {"judge": JUDGE_MODEL, "generator": GEN_MODEL, "injector": INJECT_MODEL,
                          "adjudicator": ADJ_MODEL, "mt": MT_MODELS},
               "suites": {D["doc"]: {"tests": D["n_tests"], "pruned_on_source": D["pruned"]} for D in Ds},
               "false_alarms_on_reference": {D["doc"]: {
                   "tests_failed": sorted(failing(D["rows"]["reference"])),
                   "segqe_flagged_lines": sum(q["flagged"] for q in D["rows"]["reference"]["segqe"]),
                   "n_lines": len(D["src_lines"])} for D in Ds},
               "planted": planted, "natural": [{k: v for k, v in n.items() if k != "adjudication"} for n in natural]}
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "adjudications.json").write_text(json.dumps(natural, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- markdown report
    md = ["# Project 1: AI-generated document tests vs segment-level QE", "",
          f"Judge **{JUDGE_MODEL}** · suite generator **{GEN_MODEL}** · error planter **{INJECT_MODEL}** · "
          f"adjudicator **{ADJ_MODEL}** · MT (segment by segment) **{', '.join(MT_MODELS)}**", "",
          f"{len(Ds)} real EMEA patient leaflets ({sum(len(D['src_lines']) for D in Ds)} segments), "
          f"human Spanish references from EMEA.", "",
          "## Generated suites", "", "| leaflet | segments | tests kept | pruned on source |", "|---|---|---|---|"]
    for D in Ds:
        md.append(f"| {D['doc']} | {len(D['src_lines'])} | {D['n_tests']} | {len(D['pruned'])} |")

    md += ["", "## A. Planted errors (known ground truth)", "",
           "| error type | doc-level? | generated tests | segment QE | either | tests only | QE only |",
           "|---|---|---|---|---|---|---|"]
    for et in [*ERROR_TYPES, "null"]:
        P = [p for p in planted if p["type"] == et]
        if not P:
            continue
        t = sum(p["tests_caught"] or (et == "null" and bool(p["tests_unattributed"])) for p in P)
        q = sum(p["qe_caught"] for p in P)
        e = sum(p["tests_caught"] or p["qe_caught"] for p in P)
        to = sum(p["tests_caught"] and not p["qe_caught"] for p in P)
        qo = sum(p["qe_caught"] and not p["tests_caught"] for p in P)
        label = "**null control** (no error: lower is better)" if et == "null" else et
        md.append(f"| {label} | {'yes' if P[0]['doc_level'] else ''} | {pct(t, len(P))} | {pct(q, len(P))} | "
                  f"{pct(e, len(P))} | {to} | {qo} |")
    nu = sum(bool(p["tests_unattributed"]) for p in planted)
    md += ["", f"Tests count as catching an error only when a newly failing test's evidence points at the edited "
               f"line(s) (deterministic checks always count). Unattributed new failures (judge noise) occurred on "
               f"{nu}/{len(planted)} planted documents and are excluded; the null control row shows the raw rate."]
    for grp, f in [("doc-level types", lambda p: p["doc_level"]),
                   ("segment-level types", lambda p: not p["doc_level"] and p["type"] != "null")]:
        P = [p for p in planted if f(p)]
        md.append(f"| **{grp}** | | **{pct(sum(p['tests_caught'] for p in P), len(P))}** | "
                  f"**{pct(sum(p['qe_caught'] for p in P), len(P))}** | "
                  f"**{pct(sum(p['tests_caught'] or p['qe_caught'] for p in P), len(P))}** | | |")

    md += ["", "## B. Natural errors from segment-by-segment MT (adjudicated)", "",
           "| MT model | test flags (real) | QE flags (real) | real issues | found by tests only | by QE only | by both | doc-level issues: tests / QE |",
           "|---|---|---|---|---|---|---|---|"]
    for m in MT_MODELS:
        N = [n for n in natural if n["model"] == m]
        I = [i for n in N for i in n["issues"]]
        DL = [i for i in I if i.get("doc_level")]
        md.append(f"| {m} | {sum(n['t_flags'] for n in N)} ({sum(n['t_real'] for n in N)}) | "
                  f"{sum(n['s_flags'] for n in N)} ({sum(n['s_real'] for n in N)}) | {len(I)} | "
                  f"{sum(i['by_tests'] and not i['by_qe'] for i in I)} | {sum(i['by_qe'] and not i['by_tests'] for i in I)} | "
                  f"{sum(i['by_tests'] and i['by_qe'] for i in I)} | {sum(i['by_tests'] for i in DL)}/{len(DL)} · "
                  f"{sum(i['by_qe'] for i in DL)}/{len(DL)} |")
    md += ["", "## False alarms on the human reference", "",
           "| leaflet | tests failing on reference | segment-QE lines flagged |", "|---|---|---|"]
    for doc, fa in summary["false_alarms_on_reference"].items():
        md.append(f"| {doc} | {len(fa['tests_failed'])} {fa['tests_failed'][:4]} | {fa['segqe_flagged_lines']}/{fa['n_lines']} |")
    (OUT / "report.md").write_text("\n".join(md), encoding="utf-8")

    # ---- human review sheet: every issue found only by tests + a random sample of the rest
    rng = random.Random(0)
    rev = ["# Review sheet: please spot-check the adjudicator", "",
           "Issues found ONLY by the generated document tests (all), then a random sample of other confirmed issues.", ""]
    I = [(n, i) for n in natural for i in n["issues"]]
    only_t = [x for x in I if x[1]["by_tests"] and not x[1]["by_qe"]]
    rest = [x for x in I if not (x[1]["by_tests"] and not x[1]["by_qe"])]
    for n, i in only_t + rng.sample(rest, min(10, len(rest))):
        tag = "TESTS ONLY" if (i["by_tests"] and not i["by_qe"]) else ("QE ONLY" if not i["by_tests"] else "BOTH")
        rev.append(f"### [{tag}] {n['doc']} · {n['model']} · {i.get('severity')} · {'doc-level' if i.get('doc_level') else 'segment'}")
        rev.append(f"{i.get('description', '')}  \nflags: {i['flags']}")
        rev.append("- [ ] agree   - [ ] disagree\n")
    (OUT / "review.md").write_text("\n".join(rev), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
