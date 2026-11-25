"""Stop calling the API once the benchmark's recorded spend reaches config.BUDGET_USD."""

from __future__ import annotations

import threading
import time

from common import llm

from . import config


class BudgetExceeded(RuntimeError):
    pass


_lock = threading.Lock()
_last = [0.0, 0.0]   # (checked at, spent)
_inflight = [0]
RESERVE_PER_CALL = 0.05   # USD held back per request in flight (a long gpt-5.5 call costs a few cents)


def spent() -> float:
    with llm._lock:
        rows = llm._get_db().execute("SELECT model, SUM(prompt), SUM(cached), SUM(completion) FROM usage "
                                     "GROUP BY model").fetchall()
    total = 0.0
    for model, p, c, o in rows:
        if model in config.PRICES:
            pin, pc, pout = config.PRICES[model]
            total += ((p - c) * pin + c * pc + o * pout) / 1e6
    return total


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
