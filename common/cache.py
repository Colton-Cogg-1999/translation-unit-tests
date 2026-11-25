"""Ship and restore the LLM response cache, so the study can be replayed without API calls.

The study's responses live in results/cache/llm_cache.jsonl.gz (one {"k": key, "v": response} per line).

  uv run python -m common.cache restore            # load them into .cache/llm_cache.sqlite
  uv run python -m common.cache export KEYS.txt    # write the entries listed in KEYS.txt (one key per line)
"""

from __future__ import annotations

import argparse
import gzip
import json
import sqlite3
from pathlib import Path

from . import llm

SHIPPED = Path(__file__).resolve().parent.parent / "results" / "cache" / "llm_cache.jsonl.gz"


def restore(src: Path = SHIPPED, db_path: Path | None = None) -> int:
    """Insert the shipped entries into the local cache (existing entries are kept). Returns rows read."""
    db_path = Path(db_path or llm._CACHE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path)
    db.execute("CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v TEXT)")
    n = 0
    with gzip.open(src, "rt", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            db.execute("INSERT OR IGNORE INTO cache VALUES (?, ?)", (row["k"], row["v"]))
            n += 1
    db.commit()
    db.close()
    return n


def export(keys: list[str], dst: Path = SHIPPED, db_path: Path | None = None) -> int:
    db = sqlite3.connect(Path(db_path or llm._CACHE_PATH))
    dst.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    # mtime=0 keeps the gzip byte-identical across exports of the same entries
    with open(dst, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
        for k in sorted(set(keys)):
            row = db.execute("SELECT v FROM cache WHERE k=?", (k,)).fetchone()
            if row:
                gz.write((json.dumps({"k": k, "v": row[0]}, ensure_ascii=False) + "\n").encode())
                n += 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("restore")
    e = sub.add_parser("export")
    e.add_argument("keys", type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "restore":
        print(f"restored {restore()} cached responses into {llm._CACHE_PATH}")
    else:
        keys = [k.strip() for k in a.keys.read_text().splitlines() if k.strip()]
        print(f"exported {export(keys)} of {len(set(keys))} keys to {SHIPPED}")


if __name__ == "__main__":
    main()
