"""Send uncached requests through the OpenAI Batch API (50% of standard price, results within 24 hours).

Usage, in a pipeline whose steps can be re-run cheaply because every answered request is cached:

    with batch.mode():
        while True:
            result = pipeline()          # uncached requests raise llm.Deferred and are queued
            if not batch.flush():        # nothing was queued: every request was answered from the cache
                break

flush() submits the queued requests (one batch per model), waits for them, and stores each answer and its
token usage in the cache. Usage rows are tagged "<model>@batch" so spend can be priced at the batch rate.
"""

from __future__ import annotations

import contextlib
import io
import json
import time

from . import llm

POLL_SECONDS = 20
before_submit = None   # optional callable(list of request bodies), e.g. a spending check


@contextlib.contextmanager
def mode():
    llm.BATCH = True
    try:
        yield
    finally:
        llm.BATCH = False
        llm.pending.clear()


def flush(log=print, max_requests: int | None = None) -> int:
    """Submit what is queued (at most max_requests; the rest is queued again by the next pass), wait, and store
    the answers. Returns the number of requests submitted."""
    with llm._lock:
        keys = sorted(llm.pending)[:max_requests] if max_requests else sorted(llm.pending)
        queued = {k: llm.pending[k] for k in keys}
        llm.pending.clear()
    if not queued:
        return 0
    if before_submit is not None:
        before_submit(list(queued.values()))
    client = llm._get_client()
    by_model: dict[str, dict] = {}
    for key, body in queued.items():
        by_model.setdefault(body["model"], {})[key] = body
    jobs = []
    for model, reqs in by_model.items():
        lines = "".join(json.dumps({"custom_id": k, "method": "POST", "url": "/v1/chat/completions", "body": b},
                                   ensure_ascii=False) + "\n" for k, b in reqs.items())
        f = client.files.create(file=("batch.jsonl", io.BytesIO(lines.encode("utf-8"))), purpose="batch")
        b = client.batches.create(input_file_id=f.id, endpoint="/v1/chat/completions", completion_window="24h")
        log(f"  batch {b.id}: {len(reqs)} requests to {model}")
        jobs.append((b.id, model))
    for batch_id, model in jobs:
        _wait_and_store(client, batch_id, model, log)
    return len(queued)


def _wait_and_store(client, batch_id: str, model: str, log) -> None:
    while True:
        b = client.batches.retrieve(batch_id)
        if b.status in ("completed", "failed", "expired", "cancelled"):
            break
        rc = b.request_counts
        log(f"  {batch_id} {b.status}: {rc.completed}/{rc.total} done" if rc else f"  {batch_id} {b.status}")
        time.sleep(POLL_SECONDS)
    if b.status != "completed" or not b.output_file_id:
        raise RuntimeError(f"batch {batch_id} ended {b.status}: {getattr(b, 'errors', None)}")
    ok = failed = 0
    db = llm._get_db()
    with llm._lock:
        for line in client.files.content(b.output_file_id).text.splitlines():
            r = json.loads(line)
            body = (r.get("response") or {}).get("body") or {}
            choices = body.get("choices") or []
            text = ((choices[0].get("message") or {}).get("content") or "").strip() if choices else ""
            if r.get("error") or not text:
                failed += 1   # left uncached: the next round queues it again
                continue
            u = body.get("usage") or {}
            db.execute("INSERT OR REPLACE INTO cache VALUES (?, ?)", (r["custom_id"], text))
            db.execute("INSERT OR REPLACE INTO usage VALUES (?, ?, ?, ?, ?, ?)", (
                r["custom_id"], f"{model}@batch", u.get("prompt_tokens", 0),
                (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0) or 0, u.get("completion_tokens", 0),
                (u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0) or 0))
            ok += 1
        db.commit()
    log(f"  {batch_id} completed: {ok} stored, {failed} failed (will be retried)")
