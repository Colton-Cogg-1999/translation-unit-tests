"""Check registry. A check is `fn(spec, ctx) -> Result`."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..model import Document, Result, Suite, TestSpec

REGISTRY: dict[str, Callable[["TestSpec", "Context"], Result]] = {}


def check(name: str):
    def deco(fn):
        REGISTRY[name] = fn
        return fn

    return deco


@dataclass
class Context:
    suite: Suite
    source: Document
    target: Document
    # "target" mode = testing a translation; "source" mode = calibrating the suite on the source itself
    mode: str = "target"
    cache: dict = field(default_factory=dict)

    @property
    def doc_under_test(self) -> Document:
        return self.source if self.mode == "source" else self.target


def run_check(spec: TestSpec, ctx: Context) -> Result:
    fn = REGISTRY.get(spec.type)
    if fn is None:
        return Result(spec.id, spec.type, "error", spec.severity, f"unknown check type {spec.type!r}")
    try:
        return fn(spec, ctx)
    except Exception as e:  # a broken test must never crash the suite
        return Result(spec.id, spec.type, "error", spec.severity, f"{type(e).__name__}: {e}")


# register built-in checks
from . import deterministic, alignment, semantic  # noqa: E402,F401
