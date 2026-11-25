"""Run manifest: which models, settings and prompt versions produced a results directory.

Deterministic on purpose (no timestamps), so replaying the study from the cache reproduces it byte for byte
and a changed prompt or model shows up as a diff.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def prompt_hash(*texts: str) -> str:
    """Short SHA-256 of one or more prompt templates."""
    return hashlib.sha256("\x00".join(texts).encode("utf-8")).hexdigest()[:12]


def update_manifest(path: Path, section: str, data: dict) -> None:
    """Write `data` under `section`, keeping the other sections."""
    cur = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    cur[section] = data
    path.write_text(json.dumps(cur, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
