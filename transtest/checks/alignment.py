"""Cross-lingual alignment checks (LaBSE). Catch omissions / additions at document level.

Note what this can and cannot see: LaBSE is excellent at "is this a translation of
that?" but nearly blind to polarity/number flips ("take" vs "do not take" score ~0.9).
Meaning shifts are the job of the semantic (LLM) checks.
"""

from __future__ import annotations

import numpy as np

from common.embed import ALIGN_MODEL, embed

from ..model import Result, TestSpec
from . import Context, check


def _windows(sents: list[str], max_w: int = 2) -> tuple[list[str], list[tuple[int, int]]]:
    texts, spans = [], []
    for w in range(1, max_w + 1):
        for i in range(len(sents) - w + 1):
            texts.append(" ".join(sents[i:i + w]))
            spans.append((i, i + w))
    return texts, spans


def coverage_scores(src: list[str], tgt: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """best-match similarity for every source sentence (vs target windows) and vice versa.

    A sentence is only 'covered' by a window that contains it, so a 1:2 split
    translation still scores high, but a dropped sentence has nowhere to go.
    """
    s_emb = embed(src, ALIGN_MODEL)
    t_emb = embed(tgt, ALIGN_MODEL)
    tw_txt, _ = _windows(tgt)
    sw_txt, _ = _windows(src)
    tw_emb = embed(tw_txt, ALIGN_MODEL)
    sw_emb = embed(sw_txt, ALIGN_MODEL)
    src_best = np.max(s_emb @ tw_emb.T, axis=1)
    tgt_best = np.max(t_emb @ sw_emb.T, axis=1)
    return src_best, tgt_best


@check("coverage")
def coverage(spec: TestSpec, ctx: Context) -> Result:
    if ctx.mode == "source":
        return Result(spec.id, spec.type, "skip", spec.severity, "trivially true on source")
    thr = spec.params.get("min_similarity", 0.62)
    src, tgt = ctx.source.sentences, ctx.target.sentences
    src_best, tgt_best = coverage_scores(src, tgt)
    omitted = [(src[i], float(s)) for i, s in enumerate(src_best) if s < thr]
    added = [(tgt[j], float(s)) for j, s in enumerate(tgt_best) if s < thr]
    msg = []
    if omitted:
        msg.append(f"{len(omitted)} source sentence(s) without a counterpart (possible omission)")
    if added:
        msg.append(f"{len(added)} target sentence(s) without a source (possible addition)")
    ev = [f"[omitted? sim={s:.2f}] {t}" for t, s in omitted] + [f"[added? sim={s:.2f}] {t}" for t, s in added]
    return Result(spec.id, spec.type, "fail" if msg else "pass", spec.severity,
                  "; ".join(msg) or f"all {len(src)} source sentences aligned (min sim {src_best.min():.2f})",
                  evidence=ev,
                  details={"src_min": float(src_best.min()), "tgt_min": float(tgt_best.min())})


def segment_similarity(src_segs: list[str], tgt_segs: list[str]) -> np.ndarray:
    """Pairwise LaBSE cosine for pre-aligned segment pairs (segment-level QE proxy)."""
    a = embed(src_segs, ALIGN_MODEL)
    b = embed(tgt_segs, ALIGN_MODEL)
    return np.sum(a * b, axis=1)
