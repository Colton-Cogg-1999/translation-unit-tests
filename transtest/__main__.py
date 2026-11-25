"""CLI:  uv run python -m transtest <command> ...

  run        SUITE TARGET [--lang es] [--out results/prefix]   test a translation
  calibrate  SUITE [--prune OUT.yaml]                          run suite on the source; flag broken tests
  generate   SOURCE --target-lang es --out suite.yaml          LLM-draft a suite from the source
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

from .model import Document, Suite
from .runner import run_suite, summarise, write_reports

console = Console(width=int(__import__("os").environ.get("COLUMNS", 180)))
STYLE = {"pass": "green", "fail": "bold red", "error": "yellow", "skip": "dim"}


def _print(results, title):
    t = Table(title=title, show_lines=False, expand=True)
    for col, kw in [("", {"width": 4}), ("id", {}), ("type", {}), ("sev", {}), ("message", {"ratio": 3})]:
        t.add_column(col, **kw)
    for r in results:
        t.add_row(f"[{STYLE[r.status]}]{r.status}[/]", r.test_id, r.type, r.severity, r.message)
    console.print(t)
    for r in results:
        if r.status == "fail" and r.evidence:
            console.print(f"[bold red]{r.test_id}[/] evidence:")
            for e in r.evidence[:4]:
                if e:
                    console.print(f"   [dim]›[/] {e}")
    console.print(summarise(results))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="transtest")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("suite")
    r.add_argument("target")
    r.add_argument("--out")
    r.add_argument("--only", nargs="*")
    c = sub.add_parser("calibrate")
    c.add_argument("suite")
    c.add_argument("--prune")
    g = sub.add_parser("generate")
    g.add_argument("source")
    g.add_argument("--target-lang", required=True)
    g.add_argument("--out", required=True)
    m = sub.add_parser("mutate")
    m.add_argument("suite")
    m.add_argument("good_target")
    m.add_argument("--per-op", type=int, default=2)
    m.add_argument("--seed", type=int, default=0)
    m.add_argument("--out")
    a = ap.parse_args(argv)

    if a.cmd == "mutate":
        import json

        from .mutate import mutation_test
        suite = Suite.load(a.suite)
        rep = mutation_test(suite, Document.load(a.good_target, suite.target_lang), a.per_op, a.seed)
        for r in rep["mutants"]:
            tag = "[green]KILLED[/]  " if r["killed"] else "[bold red]SURVIVED[/]"
            console.print(f"{tag} {r['op']:14} - {r['before'][:70]}\n{'':24}+ {r['after'][:70]}"
                          f"\n{'':24}[dim]killed by: {', '.join(r['killed_by']) or '—'}[/]")
        console.print(f"mutation score: {rep['mutation_score']}  by operator: {rep['by_operator']}")
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0

    if a.cmd == "run":
        suite = Suite.load(a.suite)
        target = Document.load(a.target, suite.target_lang)
        res = run_suite(suite, target, only=set(a.only) if a.only else None)
        _print(res, f"{suite.name}  ←  {Path(a.target).name}")
        if a.out:
            write_reports(res, {"suite": suite.name, "target": a.target, "mode": "target"}, a.out)
        return 1 if summarise(res)["verdict"] == "FAIL" else 0

    if a.cmd == "calibrate":
        suite = Suite.load(a.suite)
        res = run_suite(suite, None, mode="source")
        _print(res, f"CALIBRATION on source: {suite.name}")
        broken = {x.test_id for x in res if x.status in ("fail", "error")}
        if broken:
            console.print(f"[yellow]{len(broken)} test(s) fail on the SOURCE → they are broken tests:[/] {sorted(broken)}")
        if a.prune:
            raw = yaml.safe_load(Path(a.suite).read_text())
            kept_ids = {s.id for s in suite.tests if s.id not in broken}
            # Suite.load assigns ids in order; mirror that to filter the raw list
            raw["tests"] = [t for t, s in zip(raw["tests"], suite.tests) if s.id in kept_ids]
            Path(a.prune).write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False, width=110))
            console.print(f"pruned suite → {a.prune} ({len(raw['tests'])} tests kept)")
        return 0

    if a.cmd == "generate":
        from .generate import generate_suite
        s = generate_suite(a.source, a.target_lang, a.out)
        console.print(f"wrote {a.out} with {len(s['tests'])} tests — review it, then run `calibrate --prune`")
        return 0


if __name__ == "__main__":
    sys.exit(main())
