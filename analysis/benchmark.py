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


STACKS = {"segment QE alone": ["segment_qe"], "segment QE + checklist": ["segment_qe", "checklist"],
          "context QE alone": ["context_qe"], "context QE + checklist": ["context_qe", "checklist"]}


def stacks(out_rows, s, rows) -> dict:
    """Recall of combinations of checks (an error counts if any check in the stack found it), with every flag
    counted vs only major/critical flags (what a pipeline that gates on severity would act on)."""
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
            out[f"{model}|{name}|false_alarm_major"] = _stack_false_alarms(rows, model, dets)
            cost = [s["cost"].get(f"{model}|{x}|leaflet") for x in dets]
            out[f"{model}|{name}|usd"] = sum(c["usd_per_100_segments"] for c in cost) if all(cost) else None
    return out


def _stack_false_alarms(rows, model, dets) -> dict:
    """Share of the sampled clean segments (where per-segment QE ran) that any check in the stack flags major+."""
    clean = [r for r in rows if not r["variant"] and r["model"] == model]
    sampled = {(r["doc"], r["segment"]) for r in clean if r["detector"] == "segment_qe"}
    flagged = set()
    for r in clean:
        if r["detector"] in dets:
            for f in r["flags"]:
                if f["severity"] in SEVERE:
                    flagged |= {(r["doc"], n) for n in f["segments"]} & sampled
    return {"k": len(flagged), "n": len(sampled)}


def table_stacks(s) -> str:
    lines = ["| model | checks run | cross-segment errors, any flag | cross-segment errors, major/critical flag | "
             "segment-local errors, major/critical flag | clean segments flagged major/critical | cost per 100 segments |",
             "|---|---|---|---|---|---|---|"]
    for model, name in ((m, n) for m in DETECT_MODELS for n in STACKS):
        st = s["stacks"]
        usd = st.get(f"{model}|{name}|usd")
        lines.append(f"| {SHORT[model]} | {name} | {_ci(st[f'{model}|{name}|cross']['any'])} | **{_ci(st[f'{model}|{name}|cross']['major'])}** | "
                     f"{_ci(st[f'{model}|{name}|local']['major'])} | {_frac(st[f'{model}|{name}|false_alarm_major'])} | "
                     + _usd(usd) + " |")
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


def table_recall(s) -> str:
    lines = ["| detector | model | cross-segment errors | segment-local errors |", "|---|---|---|---|"]
    for det in ("segment_qe", "context_qe", "document_qe", "checklist"):
        for model in DETECT_MODELS:
            r = s["recall"]
            c, l_ = r.get(f"{model}|{det}|cross|all"), r.get(f"{model}|{det}|local|all")
            lines.append(f"| {DET_LABEL[det]} | {SHORT[model]} | {_ci(c and c['detected'])} | {_ci(l_ and l_['detected'])} |")
    return "\n".join(lines)


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


def table_false_alarms(s) -> str:
    lines = ["| detector | model | clean segments flagged, any severity | major/critical | cost per 100 segments (leaflets) |",
             "|---|---|---|---|---|"]
    for det in ("segment_qe", "context_qe", "document_qe", "checklist"):
        for model in DETECT_MODELS:
            fa = [s["false_alarms"].get(f"{model}|{det}|{c}") for c in ("synthetic", "leaflet")]
            fa = [x for x in fa if x]
            n = sum(x["segments"] for x in fa)
            any_ = sum(x["flagged"] for x in fa)
            maj = sum(x["flagged_major"] for x in fa)
            cost = s["cost"].get(f"{model}|{det}|leaflet")
            lines.append(f"| {DET_LABEL[det]} | {SHORT[model]} | {100 * any_ / n:.0f}% | {100 * maj / n:.0f}% | "
                         + _usd(cost["usd_per_100_segments"] if cost else None) + " |")
    return "\n".join(lines)


TABLES = {"bench_stacks": table_stacks, "bench_recall": table_recall, "bench_types": table_types,
          "bench_false_alarms": table_false_alarms}


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
    r, st, pr = s["recall"], s["stacks"], s["paired"]

    def rk(m, det, fam, key="detected"):
        return r[f"{m}|{det}|{fam}|all"][key]

    def pc(d):
        return round(100 * d["rate"])

    def fa(m, name):
        x = st[f"{m}|{name}|false_alarm_major"]
        return round(100 * x["k"] / x["n"])

    def best(t):
        return max(r[f"{m}|{d}|{t}|all"]["detected"]["k"] for m in DETECT_MODELS
                   for d in ("segment_qe", "context_qe", "document_qe", "checklist"))

    seg = {m: rk(m, "segment_qe", "cross") for m in (mini, luna)}
    ctx = {m: rk(m, "context_qe", "cross") for m in (mini, luna)}
    ctxm = {m: rk(m, "context_qe", "cross", "detected_major") for m in (mini, luna)}
    alone, both = "segment QE alone", "segment QE + checklist"
    cs = {m: pr[f"{m}|cross|context_qe>segment_qe"] for m in (mini, luna)}
    ck = {m: pr[f"{m}|cross|context_qe>checklist"] for m in (mini, luna)}
    let_through = min(1 - ctxm[m]["rate"] for m in (mini, luna))
    p = s.get("pilot", {}).get("gpt-5.4-2026-03-05|context_qe|cross", [0, 0, 0])
    out = [
        f"plants {s['planting']['variants']} errors", f"into {s['planting']['documents']['leaflet']} real EU patient leaflets",
        f"giving **{s['planting']['variants']} variants**", f"{_leaflet_segments():,} segments in all",
        f"against {rk(mini, 'segment_qe', 'local')['k']} and {rk(luna, 'segment_qe', 'local')['k']} of 60 errors visible",
        f"found {ctx[mini]['k']} of 48 (gpt-5.4-mini) and {ctx[luna]['k']} of 48 (gpt-5.6-luna)",
        f"flagged only {ctxm[mini]['k']} and {ctxm[luna]['k']} of them as major or critical",
        f"more than {int(100 * let_through) // 10 * 10}% of these errors through",
        *(f"from {st[f'{m}|{alone}|cross']['major']['k']} to {st[f'{m}|{both}|cross']['major']['k']} of 48 ({SHORT[m]})"
          for m in (mini, luna)),
        f"kept {pc(st[f'{mini}|{both}|local']['major'])}% and {pc(st[f'{luna}|{both}|local']['major'])}% of segment-local errors",
        f"from {fa(mini, alone)}% to {fa(mini, both)}% and from {fa(luna, alone)}% to {fa(luna, both)}%",
        f"{_usd(st[f'{mini}|{both}|usd'])} instead of {_usd(st[f'{mini}|{alone}|usd'])} per 100 segments with gpt-5.4-mini",
        f"{_usd(st[f'{luna}|{both}|usd'])} instead of {_usd(st[f'{luna}|{alone}|usd'])} with gpt-5.6-luna",
        f"({pc(ctx[luna])}% vs {pc(ctx[mini])}%)",
        f"({pc(rk(luna, 'document_qe', 'cross'))}% vs {pc(rk(mini, 'document_qe', 'cross'))}%)",
        f"rated {ctxm[luna]['k']} of 48 major",
        f"found {best('agreement')} of 12 agreement errors and {best('terminology')} of 12 inconsistent terms",
        f"found {cs[mini]['only_a']} (gpt-5.4-mini) and {cs[luna]['only_a']} (gpt-5.6-luna) errors that plain segment QE missed",
        f"found {pc(rk(mini, 'document_qe', 'cross'))}% (gpt-5.4-mini) and {pc(rk(luna, 'document_qe', 'cross'))}% (gpt-5.6-luna)",
        f"({pc(rk(mini, 'checklist', 'local'))}%, mainly omissions",
        f"reaches {pc(rk(luna, 'checklist', 'local'))}%",
        f"GPT-5.4 with context found {p[0]} of {p[2]} and rated {p[1]} of {p[2]} major or critical",
        f"cost ${total_spend():.0f} at list prices",
    ]
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
