"""Planted-error benchmark: recall, false alarms and cost of each detector. Reads results/benchmark/ only."""

from __future__ import annotations

import gzip
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

from benchmark.budget import price as budget_price
from benchmark.config import DETECT_MODELS
from benchmark.detectors import DETECTORS
from benchmark.taxonomy import CROSS, ERROR_TYPES, LOCAL

from .stats import SEED, holm

ROOT = Path(__file__).resolve().parent.parent
B = ROOT / "results" / "benchmark"
SEVERE = ("major", "critical")

SHORT = {"gpt-5.4-2026-03-05": "gpt-5.4", "gpt-5.4-mini-2026-03-17": "gpt-5.4-mini", "gpt-5.6-luna": "gpt-5.6-luna"}


def available() -> bool:
    return (B / "detections.jsonl").exists()


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load(d: Path | None = None):
    d = d or B
    variants = {v["id"]: v for v in _jsonl(d / "variants.jsonl")}
    rows = _jsonl(d / "detections.jsonl")
    diag = {(x["variant"], x["detector"], x["model"]): x["matches"] for x in _jsonl(d / "diagnosis.jsonl")}
    cands = _jsonl(d / "candidates.jsonl")
    return variants, rows, diag, cands


def compute_pilot() -> dict:
    """The 51-error pilot (2 short texts + 2 leaflets) ran both gpt-5.4 and gpt-5.4-mini: counts per detector."""
    variants, rows, diag, _ = load(B / "pilot")
    out = defaultdict(lambda: [0, 0, 0])   # detected (any flag), detected with a major/critical flag, n
    for o in outcomes(variants, rows, diag):
        k = f"{o['model']}|{o['detector']}|{o['family']}"
        out[k][0] += o["detected"]
        out[k][1] += o["detected_major"]
        out[k][2] += 1
    return dict(out)


def usage_by_key() -> dict[str, tuple]:
    """Token usage per cache key, from the shipped benchmark cache."""
    out = {}
    path = ROOT / "results" / "cache" / "benchmark.jsonl.gz"
    if path.exists():
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                if "u" in r:
                    u = r["u"]
                    out[r["k"]] = (u["model"], u["prompt"], u["cached"], u["completion"])
    return out


def cost_usd(model: str, prompt: int, cached: int, completion: int) -> float:
    """At standard list price (the Batch API would halve it), so checks and models compare on one footing."""
    return budget_price(model.partition("@")[0], prompt, cached, completion)


# ------------------------------------------------------------------------------------------- per-variant outcomes

def outcomes(variants, rows, diag) -> list[dict]:
    """One row per variant x detector x model: was the edited segment flagged (any / major+), and was the flag
    confirmed to describe the planted change."""
    flags = defaultdict(list)
    for r in rows:
        if r["variant"]:
            flags[(r["variant"], r["detector"], r["model"])] += r["flags"]
    out = []
    for (vid, det, model), fl in flags.items():
        v = variants[vid]
        on = [f for f in fl if v["segment"] in f["segments"]]
        hit = bool(on) and diag.get((vid, det, model), False)
        out.append({"variant": vid, "doc": v["doc"], "corpus": v["corpus"], "type": v["type"], "family": v["family"],
                    "detector": det, "model": model, "flagged": bool(on),
                    "flagged_major": any(f["severity"] in SEVERE for f in on), "detected": hit,
                    "detected_major": hit and any(f["severity"] in SEVERE for f in on)})
    return out


def _boot_rate(items: list[dict], key: str, b: int = 4000, seed: int = SEED) -> dict:
    """Rate of items[key] with a bootstrap CI that resamples documents (errors in one document are not independent)."""
    if not items:
        return {"k": 0, "n": 0, "rate": None, "ci_low": None, "ci_high": None}
    by_doc = defaultdict(list)
    for it in items:
        by_doc[(it["corpus"], it["doc"])].append(bool(it[key]))
    docs = list(by_doc)
    k_doc = np.array([sum(by_doc[d]) for d in docs], dtype=float)
    n_doc = np.array([len(by_doc[d]) for d in docs], dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(docs), size=(b, len(docs)))
    reps = k_doc[idx].sum(1) / n_doc[idx].sum(1)
    k, n = int(k_doc.sum()), int(n_doc.sum())
    return {"k": k, "n": n, "rate": k / n, "ci_low": float(np.percentile(reps, 2.5)),
            "ci_high": float(np.percentile(reps, 97.5))}


def mcnemar(a: list[bool], b: list[bool]) -> dict:
    only_a = sum(x and not y for x, y in zip(a, b))
    only_b = sum(y and not x for x, y in zip(a, b))
    n = only_a + only_b
    return {"only_a": only_a, "only_b": only_b, "p": 1.0 if n == 0 else float(binomtest(only_a, n, 0.5).pvalue)}


# ------------------------------------------------------------------------------------------- summary

def compute() -> dict:
    variants, rows, diag, cands = load()
    out_rows = outcomes(variants, rows, diag)
    s: dict = {}

    # what was planted
    s["planting"] = {
        "proposed": len(cands), "verified": sum(c["keep"] for c in cands),
        "rejected": dict(sorted(_count(c["reject_reason"] for c in cands if not c["keep"]).items())),
        "variants": len(variants),
        "by_cell": {f"{corp}:{t}": sum(v["corpus"] == corp and v["type"] == t for v in variants.values())
                    for corp in ("synthetic", "leaflet") for t in ERROR_TYPES},
        "documents": {corp: len({v["doc"] for v in variants.values() if v["corpus"] == corp})
                      for corp in ("synthetic", "leaflet")}}

    # recall
    rec = {}
    for model in DETECT_MODELS:
        for det in DETECTORS:
            for fam in ("cross", "local"):
                for corp in ("all", "synthetic", "leaflet"):
                    items = [o for o in out_rows if o["model"] == model and o["detector"] == det and o["family"] == fam
                             and (corp == "all" or o["corpus"] == corp)]
                    if items:
                        rec[f"{model}|{det}|{fam}|{corp}"] = {k: _boot_rate(items, k) for k in
                                                              ("detected", "detected_major", "flagged")}
            for t in ERROR_TYPES:
                items = [o for o in out_rows if o["model"] == model and o["detector"] == det and o["type"] == t]
                if items:
                    rec[f"{model}|{det}|{t}|all"] = {"detected": _boot_rate(items, "detected")}
    s["recall"] = rec

    # paired comparisons on the same variants (diagnosed detection), Holm-corrected within the family of tests
    pairs = [("context_qe", "segment_qe"), ("document_qe", "segment_qe"), ("checklist", "segment_qe"),
             ("context_qe", "document_qe"), ("context_qe", "checklist"), ("document_qe", "checklist")]
    comp = {}
    for model in DETECT_MODELS:
        for fam in ("cross", "local"):
            for a_, b_ in pairs:
                da = {o["variant"]: o["detected"] for o in out_rows if o["model"] == model and o["detector"] == a_
                      and o["family"] == fam}
                db = {o["variant"]: o["detected"] for o in out_rows if o["model"] == model and o["detector"] == b_
                      and o["family"] == fam}
                common = sorted(set(da) & set(db))
                comp[f"{model}|{fam}|{a_}>{b_}"] = mcnemar([da[v] for v in common], [db[v] for v in common])
        # model comparison: same detector, big vs mini
    adj = holm({k: v["p"] for k, v in comp.items()})
    for k in comp:
        comp[k]["p_holm"] = adj[k]
    s["paired"] = comp

    # false alarms on clean documents (per segment checked)
    s["false_alarms"] = false_alarms(rows)
    s["cost"] = costs(rows)
    s["stacks"] = stacks(out_rows, s, rows)
    if (B / "pilot" / "detections.jsonl").exists():
        s["pilot"] = compute_pilot()
    s["detection_mismatch"] = {  # flagged the edited segment but for a different reason
        f"{model}|{det}": [sum(o["flagged"] and not o["detected"] for o in out_rows if o["model"] == model
                               and o["detector"] == det),
                           sum(o["flagged"] for o in out_rows if o["model"] == model and o["detector"] == det)]
        for model in DETECT_MODELS for det in DETECTORS}
    return s


# Checks and combinations compared in the README (a combination finds an error if any of its checks does).
STACKS = {"segment QE": ["segment_qe"],
          "segment QE + document context": ["context_qe"],
          "whole-document QE": ["document_qe"],
          "document checklist": ["checklist"],
          "segment QE + checklist": ["segment_qe", "checklist"],
          "segment QE with context + checklist": ["context_qe", "checklist"]}


def stacks(out_rows, s, rows) -> dict:
    """Recall of each check or combination (any flag, and major/critical flags only), share of clean segments it
    flags, and cost."""
    out = {}
    for model in DETECT_MODELS:
        by = defaultdict(dict)
        for o in out_rows:
            if o["model"] == model:
                by[o["variant"]][o["detector"]] = o
        for name, dets in STACKS.items():
            for fam in ("cross", "local"):
                items = []
                for d in by.values():
                    if all(x in d for x in dets) and d[dets[0]]["family"] == fam:
                        o0 = d[dets[0]]
                        items.append({"corpus": o0["corpus"], "doc": o0["doc"],
                                      "any": any(d[x]["detected"] for x in dets),
                                      "major": any(d[x]["detected_major"] for x in dets)})
                out[f"{model}|{name}|{fam}"] = {"any": _boot_rate(items, "any"), "major": _boot_rate(items, "major")}
            out[f"{model}|{name}|false_alarm_any"] = _stack_false_alarms(rows, model, dets, severe_only=False)
            out[f"{model}|{name}|false_alarm_major"] = _stack_false_alarms(rows, model, dets, severe_only=True)
            cost = [s["cost"].get(f"{model}|{x}|leaflet") for x in dets]
            out[f"{model}|{name}|usd"] = sum(c["usd_per_100_segments"] for c in cost) if all(cost) else None
    return out


def _stack_false_alarms(rows, model, dets, severe_only: bool) -> dict:
    """Share of the sampled clean segments (12 per leaflet, where per-segment QE ran) that any check in the
    combination flags. Every check is scored on the same segments, so the rates compare directly."""
    clean = [r for r in rows if not r["variant"] and r["model"] == model]
    sampled = {(r["doc"], r["segment"]) for r in clean if r["detector"] == "segment_qe"}
    flagged = set()
    for r in clean:
        if r["detector"] in dets:
            for f in r["flags"]:
                if not severe_only or f["severity"] in SEVERE:
                    flagged |= {(r["doc"], n) for n in f["segments"]} & sampled
    return {"k": len(flagged), "n": len(sampled)}


def table_main(s) -> str:
    lines = ["| check | model | cross-segment errors found | errors inside the segment found | "
             "correct segments flagged | cost per 100 segments |", "|---|---|---|---|---|---|"]
    st = s["stacks"]
    for name in STACKS:
        for m in DETECT_MODELS:
            k = f"{m}|{name}"
            lines.append(f"| {name} | {SHORT[m]} | {_ci(st[k + '|cross']['any'])} | {_ci(st[k + '|local']['any'])} | "
                         f"{_frac(st[k + '|false_alarm_any'])} | {_usd(st[k + '|usd'])} |")
    return "\n".join(lines)


def table_severity(s) -> str:
    lines = ["| check | model | cross-segment errors found | …of those rated major/critical |", "|---|---|---|---|"]
    for name in ("segment QE", "segment QE + document context", "whole-document QE"):
        for m in DETECT_MODELS:
            c = s["stacks"][f"{m}|{name}|cross"]
            lines.append(f"| {name} | {SHORT[m]} | {c['any']['k']} of {c['any']['n']} | {c['major']['k']} |")
    return "\n".join(lines)


def _count(xs):
    out = defaultdict(int)
    for x in xs:
        out[x] += 1
    return out


def false_alarms(rows) -> dict:
    """Per clean segment: share flagged (any severity / major+). Segment-level checks were run on every segment of
    synthetic documents and a fixed sample of leaflet segments; document-level checks cover every segment."""
    clean = [r for r in rows if not r["variant"]]
    out = {}
    for model in DETECT_MODELS:
        for det in ("segment_qe", "context_qe", "document_qe", "checklist"):
            for corp in ("synthetic", "leaflet"):
                rs = [r for r in clean if r["model"] == model and r["detector"] == det and _corpus(r) == corp]
                if not rs:
                    continue
                if det in ("segment_qe", "context_qe"):
                    n = len(rs)
                    any_ = sum(bool(r["flags"]) for r in rs)
                    maj = sum(any(f["severity"] in SEVERE for f in r["flags"]) for r in rs)
                else:
                    by_doc = defaultdict(list)
                    for r in rs:
                        by_doc[r["doc"]] += r["flags"]
                    n = sum(_doc_len(d) for d in by_doc)
                    any_ = sum(len({s for f in fl for s in f["segments"]}) for fl in by_doc.values())
                    maj = sum(len({s for f in fl if f["severity"] in SEVERE for s in f["segments"]})
                              for fl in by_doc.values())
                out[f"{model}|{det}|{corp}"] = {"segments": n, "flagged": any_, "flagged_major": maj}
        rs = [r for r in clean if r["model"] == model and r["detector"] == "case_tests"]
        out[f"{model}|case_tests|synthetic"] = {"documents": len(rs), "failed": sum(bool(r["flags"]) for r in rs)}
    return out


_DOC_LEN: dict[str, int] = {}


def _corpus(r) -> str:
    return "leaflet" if (ROOT / "benchmark" / "leaflets" / r["doc"]).exists() else "synthetic"


def _doc_len(doc: str) -> int:
    if not _DOC_LEN:
        from benchmark.corpus import load_all
        _DOC_LEN.update({d.id: len(d.tgt) for d in load_all()})
    return _DOC_LEN[doc]


def costs(rows) -> dict:
    """USD to check 100 segments of a clean document, per detector, model and corpus (from recorded usage)."""
    usage = usage_by_key()
    if not usage:
        return {}
    out = {}
    clean = [r for r in rows if not r["variant"]]
    for model in DETECT_MODELS:
        for det in ("segment_qe", "context_qe", "document_qe", "checklist"):
            for corp in ("synthetic", "leaflet"):
                rs = [r for r in clean if r["model"] == model and r["detector"] == det and _corpus(r) == corp]
                us = [usage[k] for r in rs for k in r["keys"] if k in usage]
                if not us:
                    continue
                usd = sum(cost_usd(m, p, c, o) for m, p, c, o in us)
                segs = len(rs) if det in ("segment_qe", "context_qe") else sum(_doc_len(d) for d in {r["doc"] for r in rs})
                out[f"{model}|{det}|{corp}"] = {"usd_per_100_segments": 100 * usd / segs, "segments": segs,
                                                "calls": len(us)}
    return out


# ------------------------------------------------------------------------------------------- tables

DET_LABEL = {"segment_qe": "segment QE", "context_qe": "segment QE + document context",
             "document_qe": "whole-document QE", "checklist": "document checklist (7 unit tests)",
             "case_tests": "case-specific tests"}


def _usd(x) -> str:
    return "–" if x is None else (f"${x:.2f}" if x >= 0.01 else f"${x:.3f}")


def _frac(d) -> str:
    return f"{100 * d['k'] / d['n']:.0f}%" if d and d["n"] else "–"


def _pct(d) -> str:
    return "–" if d is None or d.get("rate") is None else f"{100 * d['rate']:.0f}%"


def _ci(d) -> str:
    return "–" if d is None or d.get("rate") is None else \
        f"{100 * d['rate']:.0f}% [{100 * d['ci_low']:.0f}–{100 * d['ci_high']:.0f}]"


def table_types(s) -> str:
    dets = ("segment_qe", "context_qe", "document_qe", "checklist")
    names = " / ".join(SHORT[m] for m in DETECT_MODELS)
    lines = ["| error type | evidence | n | " + " | ".join(DET_LABEL[d] for d in dets) + " |",
             "|---|---|---|" + "---|" * len(dets)]
    for t in CROSS + LOCAL:
        cells = []
        for d in dets:
            vals = [s["recall"].get(f"{m}|{d}|{t}|all", {}).get("detected") for m in DETECT_MODELS]
            cells.append(" / ".join(_pct(v) for v in vals))
        n = s["recall"][f"{DETECT_MODELS[0]}|segment_qe|{t}|all"]["detected"]["n"]
        lines.append(f"| {t} | {'other segment' if t in CROSS else 'same segment'} | {n} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + f"\n\nEach cell: {names}."


TABLES = {"bench_main": table_main, "bench_types": table_types, "bench_severity": table_severity}


def table_pilot(s) -> str:
    p = s.get("pilot", {})
    lines = ["| detector | gpt-5.4: any flag | gpt-5.4: major/critical | gpt-5.4-mini: any flag | gpt-5.4-mini: major/critical |",
             "|---|---|---|---|---|"]
    for det in ("segment_qe", "context_qe", "document_qe", "checklist"):
        cells = []
        for m in ("gpt-5.4-2026-03-05", "gpt-5.4-mini-2026-03-17"):
            k, km, n = p.get(f"{m}|{det}|cross", [0, 0, 0])
            cells += [f"{k}/{n}", f"{km}/{n}"]
        lines.append(f"| {DET_LABEL[det]} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


TABLES["bench_pilot"] = table_pilot


def total_spend() -> float:
    """What was actually paid: batch requests at the batch rate."""
    return sum(budget_price(m, p, c, o) for m, p, c, o in usage_by_key().values())


def claims(s) -> list[str]:
    """Study A numbers quoted in README prose (each must appear verbatim)."""
    mini, luna = "gpt-5.4-mini-2026-03-17", "gpt-5.6-luna"
    st, pr, r = s["stacks"], s["paired"], s["recall"]

    def pc(d):
        return round(100 * d["rate"])

    def rec(m, name, fam):
        return pc(st[f"{m}|{name}|{fam}"]["any"])

    def noise(m, name):
        x = st[f"{m}|{name}|false_alarm_any"]
        return round(100 * x["k"] / x["n"])

    def best(t):
        return max(r[f"{m}|{d}|{t}|all"]["detected"]["k"] for m in DETECT_MODELS
                   for d in ("segment_qe", "context_qe", "document_qe", "checklist"))

    SEG, CTX, DOC, CK = "segment QE", "segment QE + document context", "whole-document QE", "document checklist"
    BOTH = "segment QE with context + checklist"
    seg = {m: st[f"{m}|{SEG}|cross"]["any"] for m in (mini, luna)}
    local_seg = sorted(rec(m, SEG, "local") for m in (mini, luna))
    cs = {m: pr[f"{m}|cross|context_qe>segment_qe"] for m in (mini, luna)}
    ck = {m: pr[f"{m}|cross|context_qe>checklist"] for m in (mini, luna)}
    ratio = max(st[f"{luna}|{n}|usd"] / st[f"{mini}|{n}|usd"] for n in (SEG, CTX, DOC, CK))
    sev = st[f"{luna}|{CTX}|cross"]
    p = s.get("pilot", {}).get("gpt-5.4-2026-03-05|context_qe|cross", [0, 0, 0])
    out = [
        f"plants {s['planting']['variants']} errors", f"into {s['planting']['documents']['leaflet']} real EU patient leaflets",
        f"giving **{s['planting']['variants']} variants**", f"{_leaflet_segments():,} segments in all",
        f"{local_seg[0]}–{local_seg[1]}% of errors inside a segment",
        f"found {rec(luna, CTX, 'cross')}% of them (gpt-5.6-luna; {rec(mini, CTX, 'cross')}% with gpt-5.4-mini)",
        f"found {rec(luna, BOTH, 'cross')}% while still catching {rec(luna, BOTH, 'local')}% of errors inside a segment",
        f"found {rec(luna, CK, 'cross')}% of cross-segment errors and {rec(luna, CK, 'local')}% of errors inside a "
        f"segment while flagging {noise(luna, CK)}% of correct segments",
        f"against {noise(luna, CTX)}% for QE with context and {noise(luna, SEG)}% for plain segment QE",
        f"costs {_usd(st[f'{luna}|{CK}|usd'])} per 100 segments",
        f"({rec(luna, CTX, 'cross')}% vs {rec(mini, CTX, 'cross')}%)", f"({rec(luna, DOC, 'cross')}% vs {rec(mini, DOC, 'cross')}%)",
        f"({rec(luna, CK, 'local')}% vs {rec(mini, CK, 'local')}%)",
        f"found {best('agreement')} of 12 agreement errors and {best('terminology')} of 12 inconsistent terms",
        f"rated only {sev['major']['k']} of the {sev['any']['k']} it found as major or critical",
        f"found {cs[mini]['only_a']} (gpt-5.4-mini) and {cs[luna]['only_a']} (gpt-5.6-luna) errors that plain segment QE missed",
        f"found {rec(mini, DOC, 'cross')}% (gpt-5.4-mini) and {rec(luna, DOC, 'cross')}% (gpt-5.6-luna)",
        f"GPT-5.4 with context found {p[0]} of {p[2]} and rated {p[1]} of {p[2]} major or critical",
        f"cost ${total_spend():.0f} at list prices",
    ]
    if ratio < 0.5:
        out.append("less than half the cost")
    if seg[mini]["k"] == seg[luna]["k"]:
        out.append(f"found {seg[mini]['k']} of 48 planted cross-segment errors ({pc(seg[mini])}%) with either model")
    if cs[mini]["only_b"] == cs[luna]["only_b"] and max(cs[m]["p"] for m in cs) < 0.001:
        out.append(f"against {cs[mini]['only_b']} the other way (McNemar p < 0.001 for both)")
    if min(ck[m]["p"] for m in ck) > 0.5:
        out.append("McNemar p > 0.5 for both models")
    return out


def _leaflet_segments() -> int:
    from benchmark.corpus import load_leaflets
    return sum(len(d.tgt) for d in load_leaflets())
