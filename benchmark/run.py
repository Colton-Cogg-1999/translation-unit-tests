"""Run every detector on the clean documents and on every planted-error variant, then check each detection.

  uv run python -m benchmark.run [--pilot]

Clean documents give false-alarm rates and token cost per document; variants give recall. A detection counts
only if a detector flags the edited segment AND an independent model confirms the flag describes the planted
change (not some other problem in that segment).

Writes results/benchmark/detections.jsonl, diagnosis.jsonl and manifest.json.
"""

from __future__ import annotations

import argparse
import json
import random
from concurrent.futures import ThreadPoolExecutor

from common import llm
from common.llm import chat_json
from common.manifest import prompt_hash, update_manifest

from . import budget, config, plant
from . import detectors as D
from .corpus import load_all
from .plant import OUT
from .taxonomy import ERROR_TYPES

DIAGNOSIS_PROMPT = """A translation checker reported a problem in segment {n} of a Spanish translation. Does its report
describe this specific error?

The error: segment {n} was changed from
  "{original}"
to
  "{edited}"
({description})

The checker's report on segment {n}:
{report}

Answer true only if the report identifies this change (the same words and the same problem), not a different issue.
Reply with JSON only: {{"matches": true|false}}"""


def jobs_for(doc, model, variant=None, case=None):
    """(detector, check, segment, fn) for one document; variants only need the edited segment for per-segment QE."""
    if variant:
        segs = [variant["segment"]]
    elif doc.corpus == "leaflet":
        rng = random.Random(f"{config.SEED}:{doc.id}")
        segs = sorted(rng.sample(range(1, len(doc.tgt) + 1), min(config.CLEAN_SEGMENTS_PER_LEAFLET, len(doc.tgt))))
    else:
        segs = range(1, len(doc.tgt) + 1)
    out = [("segment_qe", None, n, lambda n=n: D.segment_qe(doc, n, model)) for n in segs]
    out += [("context_qe", None, n, lambda n=n: D.context_qe(doc, n, model)) for n in segs]
    out.append(("document_qe", None, None, lambda: D.document_qe(doc, model)))
    out += [("checklist", c, None, lambda c=c: D.checklist(doc, c, model)) for c in D.CHECKS]
    if case is not None:
        out.append(("case_tests", None, None, lambda: D.case_tests(doc, case, model)))
    return out


def diagnose(variant: dict, flags: list[dict]) -> bool:
    report = "\n".join(f"- [{f['severity']}] {f['category']}: {f['explanation']}"
                       + (f" (span: {f['span']})" if f.get("span") else "") for f in flags)
    out = chat_json(DIAGNOSIS_PROMPT.format(n=variant["segment"], original=variant["original"],
                                            edited=variant["edited"], description=variant["description"],
                                            report=report),
                    model=config.DIAGNOSIS_MODEL, reasoning_effort=config.DETECT_EFFORT, max_tokens=300)
    return bool(isinstance(out, dict) and out.get("matches"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true", help="use variants.pilot.jsonl")
    ap.add_argument("--models", default=",".join(config.DETECT_MODELS))
    a = ap.parse_args(argv)
    llm.use_openai(config.DETECT_EFFORT)
    budget.install()
    print(f"spent so far: ${budget.spent():.2f} of ${config.BUDGET_USD:.2f}", flush=True)
    sfx = ".pilot" if a.pilot else ""
    variants = [json.loads(line) for line in (OUT / f"variants{sfx}.jsonl").read_text(encoding="utf-8").splitlines()]
    docs = {d.id: d for d in load_all() if d.corpus in config.CORPORA}
    if a.pilot:
        docs = {k: v for k, v in docs.items() if k in {x["doc"] for x in variants}}
    cases = {c["id"]: c for c in json.loads((OUT.parent / "mtunit" / "suite.json").read_text(encoding="utf-8"))}
    models = [m.strip() for m in a.models.split(",") if m.strip()]

    jobs = []
    for model in models:
        for doc in docs.values():
            for det, check, seg, fn in jobs_for(doc, model, case=cases.get(doc.id)):
                jobs.append(({"detector": det, "check": check, "model": model, "doc": doc.id, "variant": None,
                              "segment": seg}, fn))
        for v in variants:
            vdoc = docs[v["doc"]].with_target(v["segment"] - 1, v["edited"])
            for det, check, seg, fn in jobs_for(vdoc, model, variant=v, case=cases.get(v["doc"])):
                jobs.append(({"detector": det, "check": check, "model": model, "doc": v["doc"], "variant": v["id"],
                              "segment": seg}, fn))
    print(f"{llm.describe()}\n{len(jobs)} detector calls over {len(docs)} clean documents and {len(variants)} "
          f"variants x {len(models)} models", flush=True)

    done = [0]

    def run(job):
        meta, fn = job
        r = {**meta, **fn()}
        done[0] += 1
        if done[0] % 500 == 0:
            print(f"  {done[0]}/{len(jobs)}", flush=True)
        return r

    with ThreadPoolExecutor(config.WORKERS) as ex:
        rows = list(ex.map(run, jobs))

    # diagnosis: one call per (variant, detector, model) whose flags touch the edited segment
    vby = {v["id"]: v for v in variants}
    groups: dict[tuple, list] = {}
    for r in rows:
        if r["variant"]:
            seg = vby[r["variant"]]["segment"]
            hit = [f for f in r["flags"] if seg in f["segments"]]
            if hit:
                groups.setdefault((r["variant"], r["detector"], r["model"]), []).extend(hit)
    print(f"diagnosing {len(groups)} detections", flush=True)
    keys = sorted(groups)
    with ThreadPoolExecutor(config.WORKERS) as ex:
        verdicts = list(ex.map(lambda k: diagnose(vby[k[0]], groups[k]), keys))
    diag = [{"variant": k[0], "detector": k[1], "model": k[2], "matches": m} for k, m in zip(keys, verdicts)]

    order = lambda r: (r["model"], r["variant"] or "", r["doc"], r["detector"], r["check"] or "", r["segment"] or 0)  # noqa: E731
    (OUT / f"detections{sfx}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in sorted(rows, key=order)), encoding="utf-8")
    (OUT / f"diagnosis{sfx}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in diag), encoding="utf-8")
    update_manifest(OUT / f"manifest{sfx}.json", "run", {
        "endpoint": llm.BASE_URL, "plant_model": config.PLANT_MODEL, "plant_effort": config.PLANT_EFFORT,
        "detect_models": models, "detect_effort": config.DETECT_EFFORT, "diagnosis_model": config.DIAGNOSIS_MODEL,
        "candidates_per_doc": config.CANDIDATES_PER_DOC, "clean_segments_per_leaflet": config.CLEAN_SEGMENTS_PER_LEAFLET, "max_per_cell": config.MAX_PER_CELL, "seed": config.SEED,
        "documents": len(docs), "variants": len(variants), "detector_calls": len(jobs),
        "prompt_hashes": {
            "plant": prompt_hash(plant.PLANT_PROMPT, *plant.FAMILY_RULE.values()),
            "verify": prompt_hash(plant.VERIFY_PROMPT),
            "taxonomy": prompt_hash(*(t["definition"] for t in ERROR_TYPES.values())),
            "segment_qe": prompt_hash(D.SEGMENT_QE_PROMPT), "context_qe": prompt_hash(D.CONTEXT_QE_PROMPT),
            "document_qe": prompt_hash(D.DOCUMENT_QE_PROMPT), "checklist": prompt_hash(D.CHECK_PROMPT, *D.CHECKS.values()),
            "diagnosis": prompt_hash(DIAGNOSIS_PROMPT)}})
    print(f"wrote {len(rows)} detector results and {len(diag)} diagnoses", flush=True)


if __name__ == "__main__":
    main()
