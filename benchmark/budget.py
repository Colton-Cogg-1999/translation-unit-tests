"""Stop calling the API once the benchmark's recorded spend reaches config.BUDGET_USD."""

from __future__ import annotations

import threading
import time

from common import batch, llm

from . import config


class BudgetExceeded(RuntimeError):
    pass


_lock = threading.Lock()
_last = [0.0, 0.0]   # (checked at, spent)
_inflight = [0]
RESERVE_PER_CALL = 0.05   # USD held back per request in flight (a long gpt-5.5 call costs a few cents)


def price(model: str, prompt: int, cached: int, completion: int) -> float:
    """USD for one request's usage; "<model>@batch" rows are billed at the batch discount."""
    base, _, tier = model.partition("@")
    if base not in config.PRICES:
        return 0.0
    pin, pc, pout = config.PRICES[base]
    usd = ((prompt - cached) * pin + cached * pc + completion * pout) / 1e6
    return usd * (config.BATCH_DISCOUNT if tier == "batch" else 1.0)


def spent() -> float:
    with llm._lock:
        rows = llm._get_db().execute("SELECT model, SUM(prompt), SUM(cached), SUM(completion) FROM usage "
                                     "GROUP BY model").fetchall()
    return sum(price(m, p, c, o) for m, p, c, o in rows)


def _completion_allowance(model: str, default: int = 1500) -> int:
    """Twice the mean output length this model has actually produced (reasoning included), or a default."""
    with llm._lock:
        n, mean = llm._get_db().execute("SELECT COUNT(*), AVG(completion) FROM usage WHERE model IN (?, ?)",
                                        (model, f"{model}@batch")).fetchone()
    return int(2 * mean) if n and n >= 20 else default


def estimate_batch(bodies: list[dict]) -> float:
    """Estimate for a batch: ~3.5 characters per input token, output at twice the model's observed mean."""
    usd, allowance = 0.0, {}
    for b in bodies:
        m = b["model"]
        if m not in allowance:
            allowance[m] = _completion_allowance(m)
        chars = sum(len(x.get("content", "")) for x in b.get("messages", []))
        usd += price(f"{m}@batch", int(chars / 3.5), 0, allowance[m])
    return usd


def check_batch(bodies: list[dict]) -> None:
    est, now = estimate_batch(bodies), spent()
    if now + est >= config.BUDGET_USD:
        raise BudgetExceeded(f"batch of {len(bodies)} requests estimated at ${est:.2f}; spent ${now:.2f} of "
                             f"${config.BUDGET_USD:.2f}")
    print(f"  submitting {len(bodies)} requests, estimated ${est:.2f} (spent so far ${now:.2f})", flush=True)


def check() -> None:
    """Raise if recorded spend plus a reserve for requests in flight would pass the budget; else count this call."""
    with _lock:
        if time.time() - _last[0] > 1.0:
            _last[:] = [time.time(), spent()]
        if _last[1] + (_inflight[0] + 1) * RESERVE_PER_CALL >= config.BUDGET_USD:
            raise BudgetExceeded(f"spent ${_last[1]:.2f} (+{_inflight[0]} calls in flight) of the "
                                 f"${config.BUDGET_USD:.2f} budget")
        _inflight[0] += 1


def done() -> None:
    with _lock:
        _inflight[0] -= 1
        _last[0] = 0.0   # re-read spend on the next check


def install() -> None:
    """Check the budget before every request that would reach the API (cache hits are free)."""
    llm.before_api_call, llm.after_api_call = check, done
    batch.before_submit = check_batch
