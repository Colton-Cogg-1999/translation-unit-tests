"""Document-level unit tests vs. segment-level QE on the Feverol leaflet.

  uv run python -m transtest.experiments.leaflet_experiment [--skip-mt]

Writes results/transtest/experiment.{json,md}.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from common.embed import ALIGN_MODEL, embed
from common.llm import JUDGE_MODEL, MT_MODEL, chat, chat_json, describe
from transtest.model import Document, Suite
from transtest.runner import run_suite, summarise, write_reports

ROOT = Path(__file__).resolve().parents[2]
EX = ROOT / "transtest" / "examples" / "leaflet"
def _slug(m: str) -> str:
    return m.split("/")[-1].replace(":", "-")


OUT = ROOT / "results" / "transtest" / f"judge-{_slug(JUDGE_MODEL)}"

# source-sentence anchors for each injected error (for scoring segment-level QE)
ANCHORS = {
    "E1": ["weighing more than 50 kg"],
    "E2": ["kidney problems and are over 65"],
    "E3": ["It can increase the effect of warfarin"],
    "E4": ["Avoid drinking alcohol"],
    "E5": ["1 or 2 tablets every", "Do not take more than 8 tablets", "Swallow the tablets whole"],
    "E6": ["Leave at least 4 hours"],
    "E7": ["If you have liver problems"],
    "E8": ["Swallow the tablets whole", "If your fever lasts"],
    "E9": ["even if you feel well"],
}
DOC_LEVEL = {"E3", "E5", "E6", "E8"}

GEMBA = """Score the following translation from English to Spanish on a continuous scale from 0 to 100,
where 0 means "no meaning preserved" and 100 means "perfect meaning and grammar".

English source: "{src}"
Spanish translation: "{tgt}"

Reply with JSON only: {{"score": <0-100>}}"""


# ------------------------------------------------------------------ segment-level QE baseline

def align_pairs(src_sents: list[str], tgt_sents: list[str]) -> list[tuple[int, int, float]]:
    """For each source sentence, its best target sentence (LaBSE). Returns (i, j, cos)."""
    a, b = embed(src_sents, ALIGN_MODEL), embed(tgt_sents, ALIGN_MODEL)
    sims = a @ b.T
    return [(i, int(np.argmax(sims[i])), float(np.max(sims[i]))) for i in range(len(src_sents))]


def segment_qe(src: Document, tgt: Document) -> list[dict]:
    S, T = src.sentences, tgt.sentences
    rows = []
    for i, j, cos in align_pairs(S, T):
        try:
            g = float(chat_json(GEMBA.format(src=S[i], tgt=T[j]), max_tokens=30, model=JUDGE_MODEL).get("score", -1))
        except Exception:
            g = -1.0
        rows.append({"i": i, "src": S[i], "tgt": T[j], "labse": round(cos, 3), "gemba": g})
    return rows


def flagged(row, labse_thr=0.80, gemba_thr=75):
    return {"labse": row["labse"] < labse_thr, "gemba": 0 <= row["gemba"] < gemba_thr}


# ------------------------------------------------------------------ natural MT

MT_SYS = ("You are a professional medical translator. Translate from English to Spanish (Spain) for a "
          "patient information leaflet. Output only the translation.")


def mt_sentence_by_sentence(src_text: str) -> str:
    """Like a segment-based CAT/MT pipeline: every line translated with zero context."""
    out = []
    for line in src_text.splitlines():
        if not line.strip():
            out.append("")
            continue
        prefix = line[: len(line) - len(line.lstrip("#").lstrip())]
        body = line[len(prefix):]
        out.append(prefix + chat(body, system=MT_SYS, max_tokens=200, model=MT_MODEL).strip())
    return "\n".join(out)


def mt_whole_document(src_text: str) -> str:
    return chat("Translate this whole document. Keep the Markdown structure, one sentence per line.\n\n" + src_text,
                system=MT_SYS, max_tokens=3000, model=MT_MODEL).strip()


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-mt", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    print(describe())

    suite = Suite.load(EX / "suite.yaml")
    report: dict = {}

    # 1) calibration on source
    cal = run_suite(suite, None, mode="source")
    report["calibration"] = summarise(cal)
    broken = [r.test_id for r in cal if r.status in ("fail", "error")]
    print("calibration:", report["calibration"], "broken:", broken)

    # 2) good + flawed targets
    targets = {"good": EX / "target_good.es.md", "flawed": EX / "target_flawed.es.md"}
    if not a.skip_mt:
        src_text = suite.source.text
        for name, fn in [("mt_sentence", mt_sentence_by_sentence), ("mt_document", mt_whole_document)]:
            p = OUT.parent / "mt" / f"leaflet_{name}__{_slug(MT_MODEL)}.es.md"
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                print(f"translating ({name}) ...")
                p.write_text(fn(src_text) + "\n", encoding="utf-8")
            targets[name] = p

    results = {}
    for name, path in targets.items():
        print(f"running suite on {name} ...")
        tgt = Document.load(path, suite.target_lang)
        res = run_suite(suite, tgt)
        write_reports(res, {"suite": suite.name, "target": str(path.relative_to(ROOT)), "mode": "target"},
                      OUT / f"leaflet_{name}")
        results[name] = res
        report[f"suite_{name}"] = summarise(res)
        print(" ", report[f"suite_{name}"])

    # 3) detection matrix on flawed: transtest vs segment QE
    spec_catches = {s.id: s.params.get("catches", []) for s in suite.tests}
    failed_flawed = {r.test_id for r in results["flawed"] if r.status == "fail"}
    failed_good = [r.test_id for r in results["good"] if r.status == "fail"]

    print("segment-level QE (good / flawed) ...")
    qe = {n: segment_qe(suite.source, Document.load(targets[n], "es")) for n in ("good", "flawed")}
    rows = []
    for err, anchors in ANCHORS.items():
        caught_by = sorted(t for t in failed_flawed if err in spec_catches.get(t, []))
        seg = [r for r in qe["flawed"] if any(an in r["src"] for an in anchors)]
        rows.append({
            "error": err, "doc_level": err in DOC_LEVEL,
            "transtest": bool(caught_by), "transtest_tests": caught_by,
            "labse_flag": any(flagged(r)["labse"] for r in seg),
            "gemba_flag": any(flagged(r)["gemba"] for r in seg),
            "segments": [{k: r[k] for k in ("src", "tgt", "labse", "gemba")} for r in seg],
        })
    fp = {
        "transtest_failed_tests_on_good": failed_good,
        "labse_flags_on_good": sum(flagged(r)["labse"] for r in qe["good"]),
        "gemba_flags_on_good": sum(flagged(r)["gemba"] for r in qe["good"]),
        "n_segments": len(qe["good"]),
    }
    report["detection"] = rows
    report["false_positives"] = fp
    report["segment_qe_mean"] = {n: {"labse": float(np.mean([r["labse"] for r in q])),
                                     "gemba": float(np.mean([r["gemba"] for r in q if r["gemba"] >= 0]))}
                                 for n, q in qe.items()}
    (OUT / "experiment.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # markdown summary
    md = ["# Leaflet experiment: document unit tests vs segment-level QE", "",
          f"Calibration on source: {report['calibration']}", "",
          "## Suite results", "", "| target | verdict | passed | failed | critical fails |", "|---|---|---|---|---|"]
    for n in targets:
        s = report[f"suite_{n}"]
        md.append(f"| {n} | {s['verdict']} | {s['passed']} | {s['failed']} | {s['critical_failures']} |")
    md += ["", "## Injected-error detection (target_flawed)", "",
           "| error | doc-level? | transtest | LaBSE seg-QE (<0.80) | LLM seg-QE GEMBA (<75) |", "|---|---|---|---|---|"]
    def yn(b):
        return "✅" if b else "—"
    for r in rows:
        md.append(f"| {r['error']} | {'yes' if r['doc_level'] else 'no'} | {yn(r['transtest'])} "
                  f"{', '.join(r['transtest_tests'])} | {yn(r['labse_flag'])} | {yn(r['gemba_flag'])} |")
    def tot(k):
        return sum(r[k] for r in rows)
    md += [f"| **total** | | **{tot('transtest')}/9** | **{tot('labse_flag')}/9** | **{tot('gemba_flag')}/9** |", "",
           "## False positives on the good translation", "", f"```\n{json.dumps(fp, indent=2)}\n```", "",
           "Models: " + describe(), "", "Mean segment-QE scores (good vs flawed): " + json.dumps(report["segment_qe_mean"])]
    (OUT / "experiment.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
