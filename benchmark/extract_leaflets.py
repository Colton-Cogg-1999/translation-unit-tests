"""Extract real patient leaflets (English source + professional Spanish translation) from OPUS EMEA.

  curl -sSL -o EMEA.zip https://object.pouta.csc.fi/OPUS-EMEA/v3/moses/en-es.txt.zip && unzip EMEA.zip -d EMEA
  uv run python -m benchmark.extract_leaflets --raw EMEA [--n 24]

A leaflet = sections 1–5 ("WHAT X IS AND WHAT IT IS USED FOR" up to "FURTHER INFORMATION"), one segment per
line, page-number debris removed. A leaflet is kept only if
  * it has 30–60 segments and at least 3 segments with numbers,
  * it isn't a re-branded copy of one already kept (same text under another product name), and
  * every line pair is a plausible translation (cosine >= MIN_SIM with OpenAI text-embedding-3-large),
    so the sentence alignment, and therefore the professional translation, can be trusted.
Writes benchmark/leaflets/<product>/{source.en.md, reference.es.md}.

Corpus: J. Tiedemann, "Parallel Data, Tools and Interfaces in OPUS", LREC 2012. Source documents © European
Medicines Agency, reproduced for research under the EMA's reuse terms.
"""

from __future__ import annotations

import argparse
import random
import re
from pathlib import Path

import numpy as np
from openai import OpenAI
from rapidfuzz import fuzz

from common import env  # noqa: F401  (loads .env)

OUT = Path(__file__).resolve().parent / "leaflets"
EMBED_MODEL = "text-embedding-3-large"
MIN_SIM = 0.45   # calibrated: aligned pairs in 6 hand-checked leaflets have min 0.47; shifted pairs median 0.37

START = re.compile(r"^WHAT (.+?) IS AND WHAT (?:IT|THEY) (?:IS|ARE) USED FOR$")
END = re.compile(r"^(FURTHER INFORMATION|6\.\s*FURTHER INFORMATION)$")
PAGE_NUM = re.compile(r"^\d{1,3}\s+(?=[A-ZÁÉÍÓÚÑ¿¡•])")
SECTION_NUM = re.compile(r"^\d{1,3}\s*\d?\.?$")


def clean(line: str) -> str:
    return PAGE_NUM.sub("", line.strip())


def candidates(raw: Path, min_lines: int, max_lines: int) -> list[tuple[str, list[tuple[str, str]]]]:
    en = (raw / "EMEA.en-es.en").read_text(encoding="utf-8").splitlines()
    es = (raw / "EMEA.en-es.es").read_text(encoding="utf-8").splitlines()
    out, seen = [], set()
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
        if min_lines <= len(pairs) <= max_lines and sum(any(c.isdigit() for c in e) for e, _ in pairs) >= 3:
            seen.add(m.group(1))
            out.append((m.group(1), pairs))
    return out


def embed(client: OpenAI, texts: list[str]) -> np.ndarray:
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    v = np.array([d.embedding for d in sorted(resp.data, key=lambda d: d.index)], dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True, help="directory with EMEA.en-es.{en,es}")
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--min-lines", type=int, default=30)
    ap.add_argument("--max-lines", type=int, default=60)
    ap.add_argument("--seed", type=int, default=3)
    a = ap.parse_args()

    cands = candidates(a.raw, a.min_lines, a.max_lines)
    print(f"{len(cands)} candidate leaflets")
    random.Random(a.seed).shuffle(cands)
    client = OpenAI()
    kept_texts: list[str] = []
    OUT.mkdir(parents=True, exist_ok=True)
    for name, pairs in cands:
        # skip re-branded duplicates (e.g. Aerius vs Azomyr: same leaflet, different brand name)
        masked = "\n".join(e for e, _ in pairs).replace(name, "X").replace(name.title(), "X").lower()
        for w in name.lower().split():
            masked = masked.replace(w, "x")
        if any(fuzz.ratio(masked, t) > 80 for t in kept_texts):
            continue
        sims = np.sum(embed(client, [e for e, _ in pairs]) * embed(client, [s for _, s in pairs]), axis=1)
        if sims.min() < MIN_SIM:
            print(f"  skip {name}: misaligned line (min sim {sims.min():.2f})")
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        d = OUT / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "source.en.md").write_text("\n".join(e for e, _ in pairs) + "\n", encoding="utf-8")
        (d / "reference.es.md").write_text("\n".join(s for _, s in pairs) + "\n", encoding="utf-8")
        kept_texts.append(masked)
        print(f"  {slug:36} {len(pairs)} segments, min align sim {sims.min():.2f}")
        if len(kept_texts) >= a.n:
            break


if __name__ == "__main__":
    main()
