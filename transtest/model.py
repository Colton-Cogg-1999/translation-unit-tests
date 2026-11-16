"""Core data model: documents, test specs, results."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SEVERITY_WEIGHT = {"critical": 25, "major": 5, "minor": 1}

_HEADING_RE = re.compile(r"^\s*#+\s*")
_BULLET_RE = re.compile(r"^\s*([-*•]|\d+[.)])\s+")
# split on sentence-final punctuation followed by whitespace + uppercase/¿/¡/digit/quote
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+(?=[\"'«¿¡(\[]?[A-ZÁÉÍÓÚÑÜÄÖ0-9])")


def split_sentences(text: str) -> list[str]:
    """Line-aware sentence splitter. Markdown headings / bullets stay as their own unit."""
    out: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line = _HEADING_RE.sub("", line)
        line = _BULLET_RE.sub("", line)
        parts = [s.strip() for s in _SENT_SPLIT_RE.split(line) if s.strip()]
        merged: list[str] = []
        for s in parts:  # re-join splits after abbreviations ("Dr. Smith", "máx. 8")
            if merged and _ABBREV_RE.search(merged[-1]):
                merged[-1] += " " + s
            else:
                merged.append(s)
        out.extend(merged)
    return out


_ABBREV_RE = re.compile(r"(?:^|\s)(Dr|Dra|Mr|Mrs|Ms|Sr|Sra|St|e\.g|i\.e|etc|approx|aprox|máx|mín|max|min|No|Nr|vs|cf|p|pp|Fig)\.$",
                        re.IGNORECASE)


@dataclass
class Document:
    text: str
    lang: str
    path: str | None = None

    @property
    def sentences(self) -> list[str]:
        return split_sentences(self.text)

    @classmethod
    def load(cls, path: str | Path, lang: str) -> "Document":
        p = Path(path)
        return cls(text=p.read_text(encoding="utf-8"), lang=lang, path=str(p))


@dataclass
class TestSpec:
    type: str
    id: str
    severity: str = "major"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Result:
    test_id: str
    type: str
    status: str  # pass | fail | error | skip
    severity: str
    message: str = ""
    evidence: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def penalty(self) -> int:
        return SEVERITY_WEIGHT.get(self.severity, 1) if self.status == "fail" else 0


@dataclass
class Suite:
    name: str
    source: Document
    target_lang: str
    tests: list[TestSpec]
    glossary: list[dict] = field(default_factory=list)
    dnt: list[str] = field(default_factory=list)
    path: str | None = None

    @classmethod
    def load(cls, path: str | Path) -> "Suite":
        p = Path(path)
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
        src_path = (p.parent / raw["source"]).resolve()
        source = Document.load(src_path, raw.get("source_lang", "en"))
        default_sev = raw.get("defaults", {}).get("severity", "major")
        tests: list[TestSpec] = []
        counters: dict[str, int] = {}
        for t in raw.get("tests", []):
            t = dict(t)
            ttype = t.pop("type")
            counters[ttype] = counters.get(ttype, 0) + 1
            tid = t.pop("id", None) or (ttype if counters[ttype] == 1 else f"{ttype}-{counters[ttype]}")
            sev = t.pop("severity", default_sev)
            tests.append(TestSpec(type=ttype, id=tid, severity=sev, params=t))
        return cls(
            name=raw.get("suite", p.stem),
            source=source,
            target_lang=raw["target_lang"],
            tests=tests,
            glossary=raw.get("glossary", []) or [],
            dnt=raw.get("dnt", []) or [],
            path=str(p),
        )
