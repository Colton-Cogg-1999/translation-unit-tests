"""Run a suite against a target document (or the source, for calibration)."""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path

from .checks import Context, run_check
from .model import Document, Result, Suite

WORKERS = int(os.environ.get("TRANSTEST_WORKERS", "2"))  # = llama.cpp parallel slots


def run_suite(suite: Suite, target: Document | None, mode: str = "target",
              only: set[str] | None = None) -> list[Result]:
    ctx = Context(suite=suite, source=suite.source, target=target or suite.source, mode=mode)
    specs = [s for s in suite.tests if not only or s.id in only or s.type in only]
    with ThreadPoolExecutor(WORKERS) as ex:
        return list(ex.map(lambda s: run_check(s, ctx), specs))


def summarise(results: list[Result]) -> dict:
    counted = [r for r in results if r.status in ("pass", "fail")]
    fails = [r for r in results if r.status == "fail"]
    return {
        "tests": len(results),
        "passed": sum(r.status == "pass" for r in results),
        "failed": len(fails),
        "errors": sum(r.status == "error" for r in results),
        "skipped": sum(r.status == "skip" for r in results),
        "pass_rate": round(sum(r.status == "pass" for r in counted) / max(1, len(counted)), 3),
        "penalty": sum(r.penalty for r in results),
        "critical_failures": sum(r.severity == "critical" for r in fails),
        "verdict": "FAIL" if any(r.severity == "critical" for r in fails) else ("WARN" if fails else "PASS"),
    }


def to_json(results: list[Result], meta: dict) -> str:
    return json.dumps({"meta": meta, "summary": summarise(results),
                       "results": [asdict(r) for r in results]}, ensure_ascii=False, indent=2)


def to_markdown(results: list[Result], meta: dict) -> str:
    s = summarise(results)
    icon = {"pass": "✅", "fail": "❌", "error": "⚠️", "skip": "⏭️"}
    lines = [f"# transtest report — {meta.get('suite')}", "",
             f"- target: `{meta.get('target')}`  ", f"- mode: {meta.get('mode')}",
             f"- **verdict: {s['verdict']}** — {s['passed']} passed, {s['failed']} failed "
             f"({s['critical_failures']} critical), {s['errors']} errors, {s['skipped']} skipped; "
             f"penalty {s['penalty']}", "",
             "| | id | type | severity | message |", "|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {icon[r.status]} | {r.test_id} | {r.type} | {r.severity} | {r.message.replace('|', '/')} |")
    fails = [r for r in results if r.status == "fail" and r.evidence]
    if fails:
        lines += ["", "## Evidence for failures", ""]
        for r in fails:
            lines.append(f"**{r.test_id}**")
            lines += [f"> {e}" for e in r.evidence if e]
            lines.append("")
    return "\n".join(lines)


def write_reports(results: list[Result], meta: dict, out_prefix: str | Path) -> None:
    out = Path(out_prefix)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(to_json(results, meta), encoding="utf-8")
    out.with_suffix(".md").write_text(to_markdown(results, meta), encoding="utf-8")
