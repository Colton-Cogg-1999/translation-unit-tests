"""Recompute every number, table and figure in the README from the committed results. No LLM calls.

  uv run python -m analysis            # write results/analysis/, figures/, and refresh README tables
  uv run python -m analysis --check    # exit 1 if the README's tables or quoted numbers are out of date

README tables live between <!-- BEGIN analysis:NAME --> and <!-- END analysis:NAME --> markers and are
regenerated. Numbers quoted in the prose are listed in `claims()` and must appear verbatim in the README.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter

from mtunit.capabilities import CAPABILITIES

from . import benchmark as bench
from . import figures
from .data import ENGINES, MODES, ROOT, load_failures, load_pilot, load_runs, load_validation
from .stats import bootstrap_mode_effects, did_from_replicates, fisher, gee_logit, holm, mode_delta, sign_test

OUT = ROOT / "results" / "analysis"
FIG = ROOT / "figures"
README = ROOT / "README.md"
SHORT = {"llama-4-scout": "scout", "gpt-5.4-nano": "nano", "gpt-5.4-mini": "mini"}
LABEL = {
    "negation": "negation", "numbers_locale": "numbers & locale formats", "placeholders_tags": "placeholders/tags",
    "dnt": "do-not-translate terms", "condition_scope": "logical/condition scope",
    "coreference_agreement": "pronoun & gender agreement", "term_consistency": "terminology consistency",
    "register_consistency": "register consistency", "implicit_subject_ellipsis": "implicit subjects/ellipsis",
    "list_inheritance": "list items inheriting a lead-in", "context_disambiguation": "context-dependent word sense",
    "ui_reference_consistency": "UI-label references",
}
CAPS = list(CAPABILITIES)
CROSS = [c for c in CAPS if CAPABILITIES[c]["cross_segment"]]
LOCAL = [c for c in CAPS if not CAPABILITIES[c]["cross_segment"]]


def pct(a: int, b: int) -> int:
    return round(100 * a / b) if b else 0


def fmt_p(p: float) -> str:
    if p < 1e-3:
        m, e = f"{p:.0e}".split("e")
        return f"{m}×10⁻{str(int(e[1:])).translate(str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹'))}"
    return f"{p:.2f}" if p >= 0.01 else f"{p:.3f}"


# --------------------------------------------------------------------------------------------- compute

def compute() -> dict:
    runs, fails = load_runs(), load_failures()
    s: dict = {"validation": load_validation(), "pilot": load_pilot()}

    # RQ1: pass rates (unverified cases excluded, as in mtunit.run)
    def rate(rows):
        d = [r for r in rows if r["status"] != "unverified"]
        return [sum(r["status"] == "pass" for r in d), len(d)]

    s["pass"] = {cap: {f"{e}__{m}": rate([r for r in runs if r["capability"] == cap and r["engine"] == e
                                          and r["mode"] == m]) for e in ENGINES for m in MODES} for cap in CAPS}
    s["pass_group"] = {g: {f"{e}__{m}": rate([r for r in runs if r["capability"] in caps and r["engine"] == e
                                              and r["mode"] == m]) for e in ENGINES for m in MODES}
                       for g, caps in (("cross", CROSS), ("local", LOCAL))}
    s["pass_pooled"] = {g: {m: rate([r for r in runs if r["capability"] in caps and r["mode"] == m]) for m in MODES}
                        for g, caps in (("cross", CROSS), ("local", LOCAL))}
    s["unverified_rows"] = sum(r["status"] == "unverified" for r in runs)

    # paired by engine x case: which mode failed
    by = {(r["engine"], r["case"], r["mode"]): r for r in runs}
    paired = {}
    for g, caps in [("cross", CROSS), ("local", LOCAL)] + [(c, [c]) for c in CAPS]:
        seg_only = doc_only = 0
        for (e, c, m), r in by.items():
            if m != "segment" or r["capability"] not in caps:
                continue
            d = by[(e, c, "document")]
            if "unverified" in (r["status"], d["status"]):
                continue
            seg_only += r["status"] == "fail" and d["status"] == "pass"
            doc_only += r["status"] == "pass" and d["status"] == "fail"
        paired[g] = {"seg_only_fail": seg_only, "doc_only_fail": doc_only, "p": sign_test(seg_only, doc_only)}
    adj = holm({c: paired[c]["p"] for c in CAPS})
    for c in CAPS:
        paired[c]["p_holm"] = adj[c]
    s["paired"] = paired

    groups = {"cross": CROSS, "local": LOCAL} | {c: [c] for c in CAPS}
    boot = bootstrap_mode_effects(runs, groups)
    s["mode_effect"] = {k: v for k, v in boot.items() if not k.startswith("_")}
    s["mode_effect"]["did"] = did_from_replicates(boot, "cross", "local")
    s["engine_cross_delta"] = {e: mode_delta([r for r in runs if r["engine"] == e and r["cross_segment"]])
                               for e in ENGINES}
    s["gee"] = gee_logit(runs)

    # RQ2 / RQ3: failures and adjudication
    real = [f for f in fails if f["real_error"]]
    s["failures"] = {"n": len(fails), "real": len(real), "artifacts": len(fails) - len(real),
                     "real_qe_major_case": sum(f["qe_flagged_major"] for f in real),
                     "real_qe_identified": sum(f["qe_identified"] for f in real)}
    s["by_cap"] = {c: {"failures": sum(f["capability"] == c for f in fails),
                       "real": sum(f["capability"] == c for f in real),
                       "qe_identified": sum(f["capability"] == c and f["qe_identified"] for f in real),
                       "qe_major_case": sum(f["capability"] == c and f["qe_flagged_major"] for f in real)}
                   for c in CAPS}
    for g, caps in (("cross", CROSS), ("local", LOCAL)):
        rg = [f for f in real if f["capability"] in caps]
        s["failures"][g] = {"real": len(rg), "qe_identified": sum(f["qe_identified"] for f in rg),
                            "qe_major_case": sum(f["qe_flagged_major"] for f in rg)}
    fc, fl = s["failures"]["cross"], s["failures"]["local"]
    s["failures"]["p_identified_local_vs_cross"] = fisher(fl["qe_identified"], fl["real"], fc["qe_identified"], fc["real"])
    s["failures"]["p_major_local_vs_cross"] = fisher(fl["qe_major_case"], fl["real"], fc["qe_major_case"], fc["real"])

    # evidence location (labelled error types only): needs another segment vs visible inside the segment
    need = [f for f in real if f["error_type"] in ("gender_agreement_cross_segment", "tu_text_slips_into_usted")
            or f["capability"] == "list_inheritance"]
    inside = [f for f in real if f["error_type"] in ("usted_text_slips_into_tu", "consistent_tu_in_formal_text",
                                                     "visible_within_segment")]
    s["evidence_location"] = {"another_segment": [sum(f["qe_identified"] for f in need), len(need)],
                              "inside_segment": [sum(f["qe_identified"] for f in inside), len(inside)]}
    s["evidence_location"]["p"] = fisher(*s["evidence_location"]["another_segment"],
                                         *s["evidence_location"]["inside_segment"])

    types = Counter(f["error_type"] for f in real if f["error_type"])
    s["error_types"] = {t: {"n": n, "qe_identified": sum(f["qe_identified"] for f in real if f["error_type"] == t)}
                        for t, n in sorted(types.items())}
    s["error_types_by_mode"] = {t: dict(Counter(f["mode"] for f in real if f["error_type"] == t))
                                for t in sorted(types)}

    if bench.available():
        s["benchmark"] = bench.compute()

    passing = [r for r in runs if r["status"] == "pass"]
    s["qe_noise"] = {"passing_cases": len(passing), "qe_flagged": sum(r["qe_flagged_any"] for r in passing)}
    return s


# --------------------------------------------------------------------------------------------- tables

def table_rq1(s) -> str:
    keys = [f"{e}__{m}" for e in ENGINES for m in MODES]
    head = "| capability | cross-segment | " + " | ".join(f"{SHORT[e]} {m[:3]}" for e in ENGINES for m in MODES) + " |"
    lines = [head, "|---|---|" + "---|" * len(keys)]
    for c in CAPS:
        lines.append(f"| {LABEL[c]} | {'yes' if c in CROSS else ''} | "
                     + " | ".join(f"{p}/{n}" for p, n in (s["pass"][c][k] for k in keys)) + " |")
    for g, name in (("local", "segment-local"), ("cross", "cross-segment")):
        lines.append(f"| **{name}** | | " + " | ".join(f"**{pct(*s['pass_group'][g][k])}%**" for k in keys) + " |")
    return "\n".join(lines)


def table_rq1_tests(s) -> str:
    me, pr, gee = s["mode_effect"], s["paired"], s["gee"]

    def ci(d):
        return f"{d['delta_pp']:+.0f} pp [{d['ci_low']:+.0f}, {d['ci_high']:+.0f}]"

    def orr(d):
        return f"{d['odds_ratio']:.1f} [{d['ci_low']:.1f}, {d['ci_high']:.1f}]"

    return "\n".join([
        "| | document − segment pass rate, 95% CI | failed only in segment mode | failed only in document mode | sign test |",
        "|---|---|---|---|---|",
        f"| cross-segment capabilities | {ci(me['cross'])} | {pr['cross']['seg_only_fail']} | "
        f"{pr['cross']['doc_only_fail']} | p = {fmt_p(pr['cross']['p'])} |",
        f"| segment-local capabilities | {ci(me['local'])} | {pr['local']['seg_only_fail']} | "
        f"{pr['local']['doc_only_fail']} | p = {fmt_p(pr['local']['p'])} |",
        f"| **difference (cross − local)** | **{ci(me['did'])}** | | | |",
        "",
        f"GEE logistic regression on all {gee['_n_obs']} decided engine × mode × case rows, clustered by case "
        f"({gee['_n_cases']} cases), with engine as a covariate:",
        "",
        "| term | odds ratio [95% CI] | p |",
        "|---|---|---|",
        f"| document mode (segment-local capabilities) | {orr(gee['document'])} | {fmt_p(gee['document']['p'])} |",
        f"| document mode (cross-segment capabilities) | {orr(gee['document_within_cross'])} | "
        f"{fmt_p(gee['document_within_cross']['p'])} |",
        f"| **document × cross-segment interaction** | **{orr(gee['document:cross_segment'])}** | "
        f"**{fmt_p(gee['document:cross_segment']['p'])}** |",
    ])


def table_rq1_caps(s) -> str:
    lines = ["| capability | document − segment, 95% CI | failed only seg / only doc | sign test p (Holm) |",
             "|---|---|---|---|"]
    for c in CROSS + LOCAL:
        e, p = s["mode_effect"][c], s["paired"][c]
        lines.append(f"| {LABEL[c]}{' *(control)*' if c in LOCAL else ''} | {e['delta_pp']:+.0f} pp "
                     f"[{e['ci_low']:+.0f}, {e['ci_high']:+.0f}] | {p['seg_only_fail']} / {p['doc_only_fail']} | "
                     f"{fmt_p(p['p_holm'])} |")
    return "\n".join(lines)


def table_rq2(s) -> str:
    lines = ["| capability | real errors | QE identified (any severity) | QE major/critical flag in the case |",
             "|---|---|---|---|"]
    for c in CROSS + LOCAL:
        b = s["by_cap"][c]
        if b["real"]:
            lines.append(f"| {LABEL[c]}{' *(control)*' if c in LOCAL else ''} | {b['real']} | {b['qe_identified']} | "
                         f"{b['qe_major_case']} |")
    for g, name in (("cross", "cross-segment"), ("local", "segment-local")):
        f = s["failures"][g]
        lines.append(f"| **{name} total** | **{f['real']}** | **{f['qe_identified']} ({pct(f['qe_identified'], f['real'])}%)** | "
                     f"**{f['qe_major_case']} ({pct(f['qe_major_case'], f['real'])}%)** |")
    return "\n".join(lines)


ERROR_TYPE_ROWS = [
    # (label, error_type or capability, evidence location)
    ("Pronoun gender set by a noun in an earlier segment", "gender_agreement_cross_segment", "another segment"),
    ("List item doesn't complete its lead-in", "cap:list_inheritance", "another segment"),
    ("Informal (tú) text slips into usted", "tu_text_slips_into_usted", "another segment"),
    ("Formal (usted) text slips into tú", "usted_text_slips_into_tu", "inside the segment"),
    ("tú used consistently in formal text (document mode)", "consistent_tu_in_formal_text", "inside the segment"),
    ("Pronoun/reference error visible inside the segment", "visible_within_segment", "inside the segment"),
    ("Segment-local capabilities (negation, numbers, DNT)", "group:local", "inside the segment"),
]


def error_type_rows(s) -> list[dict]:
    out = []
    for label, key, where in ERROR_TYPE_ROWS:
        if key.startswith("cap:"):
            b = s["by_cap"][key[4:]]
            k, n = b["qe_identified"], b["real"]
        elif key.startswith("group:"):
            f = s["failures"][key[6:]]
            k, n = f["qe_identified"], f["real"]
        else:
            k, n = s["error_types"][key]["qe_identified"], s["error_types"][key]["n"]
        out.append({"label": label, "k": k, "n": n, "where": where, "needs_context": where == "another segment"})
    return out


def table_rq2_types(s) -> str:
    lines = ["| error type | evidence is… | real errors | QE identified |", "|---|---|---|---|"]
    for r in error_type_rows(s):
        lines.append(f"| {r['label']} | {r['where']} | {r['n']} | **{r['k']}** |")
    return "\n".join(lines)


def table_rq3(s) -> str:
    lines = ["| capability | failures | test artifacts | real errors |", "|---|---|---|---|"]
    for c in CROSS + LOCAL:
        b = s["by_cap"][c]
        if b["failures"]:
            lines.append(f"| {LABEL[c]} | {b['failures']} | {b['failures'] - b['real']} | {b['real']} |")
    f = s["failures"]
    lines.append(f"| **total** | **{f['n']}** | **{f['artifacts']} ({pct(f['artifacts'], f['n'])}%)** | "
                 f"**{f['real']} ({pct(f['real'], f['n'])}%)** |")
    return "\n".join(lines)


TABLES = {"rq1_table": table_rq1, "rq1_tests": table_rq1_tests, "rq1_caps": table_rq1_caps,
          "rq2_table": table_rq2, "rq2_types": table_rq2_types, "rq3_table": table_rq3}
if bench.available():
    TABLES |= {name: (lambda s, fn=fn: fn(s["benchmark"])) for name, fn in bench.TABLES.items()}


# --------------------------------------------------------------------------------------------- prose claims

def claims(s) -> list[str]:
    """Numbers quoted in README prose. Each string must appear verbatim in README.md."""
    f, et, pr, me, pl = s["failures"], s["error_types"], s["paired"], s["mode_effect"], s["pilot"]
    pc, pl_ = s["pass_pooled"]["cross"], s["pass_pooled"]["local"]
    v = s["validation"]
    extra = bench.claims(s["benchmark"]) if "benchmark" in s else []
    return extra + [
        f"QE identified **{et['gender_agreement_cross_segment']['qe_identified']} of "
        f"{et['gender_agreement_cross_segment']['n']}**",
        f"**{s['by_cap']['list_inheritance']['qe_identified']} of {s['by_cap']['list_inheritance']['real']}**",
        f"{et['usted_text_slips_into_tu']['qe_identified']} of {et['usted_text_slips_into_tu']['n']}",
        f"{et['tu_text_slips_into_usted']['qe_identified']} of {et['tu_text_slips_into_usted']['n']}",
        f"{pct(*pc['document'])}% with whole-document translation and {pct(*pc['segment'])}% segment by segment",
        f"({pct(*pl_['document'])}% vs {pct(*pl_['segment'])}%)",
        f"{pr['cross']['seg_only_fail']} engine × case pairs failed only in segment mode and "
        f"{pr['cross']['doc_only_fail']} only in document mode",
        f"{me['did']['delta_pp']:+.0f} percentage points (95% CI {me['did']['ci_low']:+.0f} to {me['did']['ci_high']:+.0f})",
        f"{f['real']} of the {f['n']} failures ({pct(f['real'], f['n'])}%)",
        f"{f['artifacts']} ({pct(f['artifacts'], f['n'])}%)",
        f"{f['local']['qe_major_case']} of {f['local']['real']} segment-local errors and "
        f"{f['cross']['qe_major_case']} of {f['cross']['real']} cross-segment errors",
        f"{f['local']['qe_identified']} of {f['local']['real']} ({pct(f['local']['qe_identified'], f['local']['real'])}%)",
        f"{f['cross']['qe_identified']} of {f['cross']['real']} ({pct(f['cross']['qe_identified'], f['cross']['real'])}%)",
        f"Fisher p = {fmt_p(f['p_identified_local_vs_cross'])}",
        f"**{v['valid_cases']}/{v['generated_cases']} cases and {v['valid_assertions']}/{v['generated_assertions']} assertions**",
        f"{s['qe_noise']['qe_flagged']} of the {s['qe_noise']['passing_cases']}",
        f"**{pl['suite_caught']}/{pl['planted_errors']}**",
        f"LLM segment QE caught {pl['llm_qe_caught']}/{pl['planted_errors']}",
        f"LaBSE similarity caught {pl['labse_caught']}/{pl['planted_errors']}",
        f"{pl['mutants']} single-edit mutants",
        f"scored {pl['mutation_score_v1']:.2f}",
        f"to {pl['mutation_score_v2']:.2f}",
        "QE identified {} of {}".format(*s["evidence_location"]["another_segment"]),
        "{} of {}".format(*s["evidence_location"]["inside_segment"]),
        f"odds ratio of {s['gee']['document:cross_segment']['odds_ratio']:.1f}",
        f"only list inheritance stays significant (Holm-adjusted p = {fmt_p(pr['list_inheritance']['p_holm'])})",
        f"{s['unverified_rows']} engine × mode × case rows",
        "segmentation cost Scout {:.0f} points, nano {:.0f} and mini {:.0f}".format(
            *(s["engine_cross_delta"][e] for e in ENGINES)),
    ]


# --------------------------------------------------------------------------------------------- outputs

def render_readme(text: str, s: dict) -> str:
    for name, fn in TABLES.items():
        pat = re.compile(rf"(<!-- BEGIN analysis:{name} -->\n)(?:.*?\n)?(<!-- END analysis:{name} -->)", re.DOTALL)
        if not pat.search(text):
            raise SystemExit(f"README is missing the analysis:{name} block")
        body = fn(s)
        text = pat.sub(lambda m, body=body: m.group(1) + body + "\n" + m.group(2), text)
    return text


def make_figures(s: dict) -> None:
    eff = [{"label": LABEL[c], "cross_segment": c in CROSS, **s["mode_effect"][c]} for c in CROSS + LOCAL]
    grp = [{"label": "All cross-segment", "cross_segment": True, **s["mode_effect"]["cross"]},
           {"label": "All segment-local", "cross_segment": False, **s["mode_effect"]["local"]}]
    figures.mode_effect(eff, grp, FIG)
    figures.qe_detection(error_type_rows(s), FIG)
    art = sorted(([{"label": LABEL[c], "artifacts": b["failures"] - b["real"], "failures": b["failures"]}
                   for c, b in s["by_cap"].items() if b["failures"]]),
                 key=lambda r: -r["artifacts"] / r["failures"])
    figures.artifact_rate(art, FIG)
    if "benchmark" in s:
        b, m = s["benchmark"], bench.DETECT_MODELS[0]
        series = [("detected", "any flag on the error"), ("detected_major", "major/critical flag on the error")]
        rows = [{"label": bench.DET_LABEL[d],
                 "cross": {k: b["recall"][f"{m}|{d}|cross|all"][k] for k, _ in series},
                 "local": {k: b["recall"][f"{m}|{d}|local|all"][k] for k, _ in series}}
                for d in ("segment_qe", "context_qe", "document_qe", "checklist")]
        figures.bench_recall(rows, series, FIG)

def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, list | tuple):
        return [_jsonable(v) for v in o]
    if hasattr(o, "item"):
        return o.item()
    return round(o, 6) if isinstance(o, float) else o


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="fail if README tables or quoted numbers are stale")
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args(argv)
    s = compute()
    text = README.read_text(encoding="utf-8")
    new = render_readme(text, s)
    missing = [c for c in claims(s) if c not in new]

    if a.check:
        ok = True
        if new != text:
            print("README tables are out of date: run `uv run python -m analysis`", file=sys.stderr)
            ok = False
        for c in missing:
            print(f"README does not contain the computed figure: {c!r}", file=sys.stderr)
            ok = False
        print("README matches the results" if ok else "", file=sys.stderr if not ok else sys.stdout)
        return 0 if ok else 1

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(_jsonable(s), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (OUT / "tables.md").write_text("\n\n".join(f"## {n}\n\n{fn(s)}" for n, fn in TABLES.items()) + "\n",
                                   encoding="utf-8")
    if not a.no_figures:
        make_figures(s)
    README.write_text(new, encoding="utf-8")
    print(f"wrote {OUT / 'summary.json'}, {OUT / 'tables.md'}" + ("" if a.no_figures else f", {FIG}/") + ", README tables")
    for c in missing:
        print(f"  README prose is missing: {c!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
