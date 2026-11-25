"""Load the study's committed results into flat rows. No LLM calls, no network."""

from __future__ import annotations

import csv
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MT = ROOT / "results" / "mtunit"
PILOT = ROOT / "results" / "transtest" / "judge-claude-sonnet-5.5"

ENGINES = ["llama-4-scout", "gpt-5.4-nano", "gpt-5.4-mini"]
MODES = ["segment", "document"]


def case_status(results: list[dict]) -> str:
    """Same rule as mtunit.run.case_status: any failed assertion fails the case; an ungrounded judge verdict
    with no failure leaves the case unverified (excluded from pass rates)."""
    st = [x["status"] for x in results]
    if "fail" in st:
        return "fail"
    if all(s == "pass" for s in st):
        return "pass"
    return "unverified"


def load_runs() -> list[dict]:
    """One row per engine x mode x case."""
    rows = []
    for eng in ENGINES:
        for mode in MODES:
            for r in json.loads((MT / "runs" / f"{eng}__{mode}.json").read_text(encoding="utf-8")):
                rows.append({"engine": eng, "mode": mode, "case": r["id"], "capability": r["capability"],
                             "cross_segment": r["cross_segment"], "domain": r["domain"],
                             "status": case_status(r["results"]), "qe_flagged_any": any(r["qe_flagged"])})
    return rows


def load_failures() -> list[dict]:
    """One row per failed assertion, joined with its adjudication and (where labelled) its error type.

    adjudication.json has no assertion index, so the join rebuilds the exact order mtunit.adjudicate used
    (sorted run files → cases → assertions) and checks that run and case id line up.
    """
    adj = json.loads((MT / "adjudication.json").read_text(encoding="utf-8"))
    keys = []
    for f in sorted(glob.glob(str(MT / "runs" / "*.json"))):
        run = Path(f).stem
        for r in json.loads(Path(f).read_text(encoding="utf-8")):
            k = 0
            for a, x in zip(r["assertions"], r["results"]):
                if x["status"] == "fail":
                    keys.append((run, r["id"], k, a))
                    k += 1
    if len(keys) != len(adj):
        raise ValueError(f"{len(keys)} failed assertions but {len(adj)} adjudications")
    labels = {}
    with open(MT / "error_types.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            labels[(row["run"], row["id"], int(row["failure_index"]))] = row["error_type"]
    out = []
    for (run, cid, k, a), j in zip(keys, adj):
        if (run, cid) != (j["run"], j["id"]):
            raise ValueError(f"adjudication order mismatch at {run} {cid}")
        eng, mode = run.split("__")
        out.append({"engine": eng, "mode": mode, "case": cid, "failure_index": k, "kind": a.get("kind"),
                    "capability": j["capability"], "cross_segment": j["cross_segment"],
                    "real_error": bool(j.get("real_error")), "qe_identified": bool(j.get("qe_identified")),
                    "qe_flagged_major": bool(j.get("qe_flagged_major")),
                    "error_type": labels.get((run, cid, k))})
    missing = set(labels) - {(f"{x['engine']}__{x['mode']}", x["case"], x["failure_index"]) for x in out}
    if missing:
        raise ValueError(f"error_types.csv rows with no matching failure: {sorted(missing)[:3]}")
    return out


def load_validation() -> dict:
    v = json.loads((MT / "validation.json").read_text(encoding="utf-8"))
    return {k: v[k] for k in ("generated_cases", "valid_cases", "generated_assertions", "valid_assertions")}


def load_pilot() -> dict:
    exp = json.loads((PILOT / "experiment.json").read_text(encoding="utf-8"))
    det = exp["detection"]
    mut = {name: json.loads((PILOT / f"{name}.json").read_text(encoding="utf-8"))
           for name in ("mutation", "mutation_v2")}
    return {
        "planted_errors": len(det),
        "suite_caught": sum(d["transtest"] for d in det),
        "llm_qe_caught": sum(d["gemba_flag"] for d in det),
        "labse_caught": sum(d["labse_flag"] for d in det),
        "suite_false_alarms_on_good": len(exp["false_positives"]["transtest_failed_tests_on_good"]),
        "mutants": len(mut["mutation"]["mutants"]),
        "mutation_score_v1": mut["mutation"]["mutation_score"],
        "mutation_score_v2": mut["mutation_v2"]["mutation_score"],
        "survivors_v2": sorted({m["op"] for m in mut["mutation_v2"]["mutants"] if not m["killed"]}),
    }
