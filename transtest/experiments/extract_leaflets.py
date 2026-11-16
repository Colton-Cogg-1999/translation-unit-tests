"""Extract real patient leaflets (EN source + human ES reference) from OPUS EMEA.

  uv run python -m transtest.experiments.extract_leaflets [--n 6]

Each leaflet = sections 1–5 ("WHAT X IS AND WHAT IT IS USED FOR" … up to "FURTHER INFORMATION"),
one CAT segment per line, cleaned of page-number debris, and kept only if every line pair
is a plausible translation (LaBSE ≥ 0.6) so the human reference is trustworthy.
Writes data/leaflets/<product>/{source.en.md, reference.es.md}.
"""

from __future__ import annotations

import argparse
import random
import re
from pathlib import Path

import numpy as np
from rapidfuzz import fuzz

from common.embed import ALIGN_MODEL, embed

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "EMEA"
OUT = ROOT / "data" / "leaflets"

START = re.compile(r"^WHAT (.+?) IS AND WHAT (?:IT|THEY) (?:IS|ARE) USED FOR$")
END = re.compile(r"^(FURTHER INFORMATION|6\.\s*FURTHER INFORMATION)$")
PAGE_NUM = re.compile(r"^\d{1,3}\s+(?=[A-ZÁÉÍÓÚÑ¿¡•])")
SECTION_NUM = re.compile(r"^\d{1,3}\s*\d?\.?$")


def clean(line: str) -> str:
    return PAGE_NUM.sub("", line.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--min-lines", type=int, default=30)
    ap.add_argument("--max-lines", type=int, default=60)
    ap.add_argument("--seed", type=int, default=3)
    a = ap.parse_args()

    en = (RAW / "EMEA.en-es.en").read_text(encoding="utf-8").splitlines()
    es = (RAW / "EMEA.en-es.es").read_text(encoding="utf-8").splitlines()

    cands, seen = [], set()
    for i, line in enumerate(en):
        m = START.match(line.strip())
        if not m or m.group(1) in seen:
            continue
        j = i + 1
        while j < len(en) and j - i < 150 and not END.match(en[j].strip()):
            j += 1
        if j - i >= 150 or j >= len(en):
            continue
        pairs = [(clean(e), clean(s)) for e, s in zip(en[i:j], es[i:j])]
        pairs = [(e, s) for e, s in pairs if e and s and not SECTION_NUM.match(e)]
        if a.min_lines <= len(pairs) <= a.max_lines and sum(any(c.isdigit() for c in e) for e, _ in pairs) >= 3:
            seen.add(m.group(1))
            cands.append((m.group(1), pairs))
    print(f"{len(cands)} candidate leaflets")

    rng = random.Random(a.seed)
    rng.shuffle(cands)
    kept, kept_texts = 0, []
    OUT.mkdir(parents=True, exist_ok=True)
    for name, pairs in cands:
        # skip re-branded duplicates (e.g. Aerius vs Azomyr: same leaflet, different brand name)
        masked = "\n".join(e for e, _ in pairs).replace(name, "X").replace(name.title(), "X").lower()
        for w in name.lower().split():
            masked = masked.replace(w, "x")
        if any(fuzz.ratio(masked, t) > 80 for t in kept_texts):
            continue
        e_v = embed([e for e, _ in pairs], ALIGN_MODEL)
        s_v = embed([s for _, s in pairs], ALIGN_MODEL)
        sims = np.sum(e_v * s_v, axis=1)
        if sims.min() < 0.6:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        d = OUT / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "source.en.md").write_text("\n".join(e for e, _ in pairs) + "\n", encoding="utf-8")
        (d / "reference.es.md").write_text("\n".join(s for _, s in pairs) + "\n", encoding="utf-8")
        kept_texts.append(masked)
        print(f"  {slug:30} {len(pairs)} segments, min align sim {sims.min():.2f}")
        kept += 1
        if kept >= a.n:
            break


if __name__ == "__main__":
    main()
