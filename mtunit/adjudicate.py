"""Independent adjudication of every unit-test failure.

For each failed assertion, a model that neither generated nor judged the tests decides:
  real_error   — is this a genuine translation error a reviewer would fix? (filters over-specific tests)
  qe_identified — did ANY segment-QE comment (any severity) identify this same problem?
Writes results/mtunit/adjudication.json and appends a section to report.md.

  uv run python -m mtunit.adjudicate
"""

from __future__ import annotations

import glob
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common.llm import CacheMiss, chat_json
from common.manifest import prompt_hash, update_manifest

from .capabilities import CAPABILITIES

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "mtunit"
ADJ_MODEL = os.environ.get("L10N_ADJUDICATE_MODEL", "openai/gpt-5.4")

PROMPT = """You are a senior English→Spanish (Spain) localization reviewer auditing an automated unit test.

Source segments (EN) and the engine's translation (ES):
{pairs}

An automated test assertion FAILED on this translation:
  assertion: {assertion}
  failure detail: {detail}

Independently, a segment-level QE tool reviewed each segment IN ISOLATION and reported:
{qe}

Answer two questions:
1. real_error: Is there a genuine translation problem here of the kind the assertion targets, one a professional
   reviewer would fix (e.g. wrong agreement/referent, inconsistent register or terminology, broken DNT, wrong
   number/locale, list item that doesn't fit its lead-in)? Answer false if the assertion is merely over-specific
   (demands one wording when another is equally correct) or wrong.
2. qe_identified: Did ANY of the QE comments (any severity) identify THIS SAME problem? Comments about other issues don't count.

Reply with JSON only:
{{"real_error": true|false, "severity": "minor|major|critical|none", "qe_identified": true|false, "reason": "<one sentence>"}}"""


def main():
    items = []
    for f in sorted(glob.glob(str(OUT / "runs" / "*.json"))):
        run = Path(f).stem
        for r in json.load(open(f)):
            for a, x in zip(r["assertions"], r["results"]):
                if x["status"] == "fail":
                    items.append((run, r, a, x))

    def one(it):
        run, r, a, x = it
        pairs = "\n".join(f"{i + 1}. EN: {s}\n   ES: {t}" for i, (s, t) in enumerate(zip(r["src"], r["tgt"])))
        qe = "\n".join(f"segment {i + 1}: " + ("; ".join(f"[{e.get('severity')}] {e.get('category')}: {e.get('explanation', '')}"
                                                         for e in q.get("errors", [])) or "no errors")
                       for i, q in enumerate(r["qe"]))
        try:
            j = chat_json(PROMPT.format(pairs=pairs, assertion=json.dumps(a, ensure_ascii=False), detail=x["detail"], qe=qe),
                          model=ADJ_MODEL, max_tokens=400)
        except CacheMiss:
            raise
        except Exception as e:
            j = {"error": str(e)}
        return {"run": run, "id": r["id"], "capability": r["capability"], "cross_segment": r["cross_segment"],
                "qe_flagged_major": any(r["qe_flagged"]), **j}

    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(one, items))
    (OUT / "adjudication.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    update_manifest(OUT / "manifest.json", "adjudicate",
                    {"model": ADJ_MODEL, "prompt_hash": prompt_hash(PROMPT), "failures_adjudicated": len(res)})

    md = ["", "## Independent adjudication of every failure", "",
          f"Adjudicator **{ADJ_MODEL}** (did not generate or judge the tests). *Real* = a reviewer would fix it; "
          "*QE identified* = some segment-QE comment, at **any** severity, described the same problem.", "",
          "| capability | cross-segment? | failures | real errors | QE identified (any severity) | QE missed |",
          "|---|---|---|---|---|---|"]
    tot = {True: [0, 0, 0], False: [0, 0, 0]}
    for cap, c in CAPABILITIES.items():
        R = [x for x in res if x["capability"] == cap]
        real = [x for x in R if x.get("real_error")]
        qi = sum(bool(x.get("qe_identified")) for x in real)
        t = tot[c["cross_segment"]]
        t[0] += len(R)
        t[1] += len(real)
        t[2] += qi
        if R:
            md.append(f"| {cap} | {'yes' if c['cross_segment'] else ''} | {len(R)} | {len(real)} | {qi} | {len(real) - qi} |")
    for cs, label in [(False, "**segment-local total**"), (True, "**cross-segment total**")]:
        n, real, qi = tot[cs]
        md.append(f"| {label} | | **{n}** | **{real} ({100 * real / max(1, n):.0f}%)** | "
                  f"**{qi} ({100 * qi / max(1, real):.0f}% of real)** | **{real - qi}** |")
    with (OUT / "report.md").open("a", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
