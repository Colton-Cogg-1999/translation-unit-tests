"""The two document collections the benchmark plants errors into.

  synthetic  the main study's validated test cases with 2+ segments, translated by the gold model (GPT-5.4,
             whole-document): short software, marketing, legal and medical texts
  leaflet    real EU patient leaflets with their professional Spanish translations (OPUS EMEA), 39–60 segments
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Doc:
    id: str
    corpus: str
    domain: str
    src: tuple[str, ...]
    tgt: tuple[str, ...]

    def numbered(self, side: str = "both") -> str:
        if side == "src":
            return "\n".join(f"{i + 1}. {s}" for i, s in enumerate(self.src))
        if side == "tgt":
            return "\n".join(f"{i + 1}. {t}" for i, t in enumerate(self.tgt))
        return "\n".join(f"{i + 1}. EN: {s}\n   ES: {t}" for i, (s, t) in enumerate(zip(self.src, self.tgt)))

    def with_target(self, i: int, text: str) -> Doc:
        tgt = list(self.tgt)
        tgt[i] = text
        return Doc(self.id, self.corpus, self.domain, self.src, tuple(tgt))


DOMAINS = {"software_ui_help": "software UI and help text", "marketing": "marketing and e-commerce copy",
           "legal_terms": "terms of service and legal text", "medical_patient": "medical patient information",
           "leaflet": "an EU patient information leaflet for a medicine"}


def load_synthetic() -> list[Doc]:
    suite = json.loads((ROOT / "results" / "mtunit" / "suite.json").read_text(encoding="utf-8"))
    return [Doc(c["id"], "synthetic", c["domain"], tuple(c["segments"]), tuple(c["gold"]))
            for c in suite if len(c["segments"]) >= 2]


def load_leaflets() -> list[Doc]:
    docs = []
    for d in sorted((ROOT / "benchmark" / "leaflets").iterdir()):
        src = (d / "source.en.md").read_text(encoding="utf-8").splitlines()
        tgt = (d / "reference.es.md").read_text(encoding="utf-8").splitlines()
        assert len(src) == len(tgt), d
        docs.append(Doc(d.name, "leaflet", "leaflet", tuple(src), tuple(tgt)))
    return docs


def load_all() -> list[Doc]:
    return load_synthetic() + load_leaflets()
