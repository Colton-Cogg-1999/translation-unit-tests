"""Statistics for the study: exact sign tests, Holm correction, case-clustered bootstrap, GEE logistic regression.

Every engine runs the same 92 cases, so rows that share a case are not independent. Intervals resample whole
cases (all 6 engine x mode rows together), and the regression uses GEE with errors clustered by case.
"""

from __future__ import annotations

import warnings

import numpy as np
from scipy.stats import binomtest, fisher_exact

SEED = 20261115
B = 10_000


def sign_test(n_pos: int, n_neg: int) -> float:
    """Two-sided exact sign test on discordant pairs."""
    n = n_pos + n_neg
    return 1.0 if n == 0 else float(binomtest(n_pos, n, 0.5).pvalue)


def holm(pvals: dict[str, float]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values (monotone)."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def fisher(a: int, n_a: int, b: int, n_b: int) -> float:
    """Two-sided Fisher exact test: a/n_a vs b/n_b."""
    return float(fisher_exact([[a, n_a - a], [b, n_b - b]]).pvalue)


def _pass_matrix(rows: list[dict]) -> tuple[list[str], dict[str, bool], np.ndarray, list[tuple[str, str]]]:
    """cases x (engine, mode) matrix: 1 pass, 0 fail, nan unverified/missing."""
    cases = sorted({r["case"] for r in rows})
    cols = sorted({(r["engine"], r["mode"]) for r in rows})
    ci, cj = {c: i for i, c in enumerate(cases)}, {c: j for j, c in enumerate(cols)}
    M = np.full((len(cases), len(cols)), np.nan)
    cross = {}
    for r in rows:
        cross[r["case"]] = r["cross_segment"]
        if r["status"] != "unverified":
            M[ci[r["case"]], cj[(r["engine"], r["mode"])]] = r["status"] == "pass"
    return cases, cross, M, cols


def mode_delta(rows: list[dict]) -> float:
    """Pass rate in document mode minus segment mode (percentage points), unverified excluded."""
    def rate(mode):
        d = [r["status"] == "pass" for r in rows if r["mode"] == mode and r["status"] != "unverified"]
        return 100 * np.mean(d) if d else np.nan
    return rate("document") - rate("segment")


def bootstrap_mode_effects(rows: list[dict], groups: dict[str, list[str]], b: int = B, seed: int = SEED) -> dict:
    """Case-clustered bootstrap of the document-minus-segment pass-rate difference for each group of capabilities,
    plus the difference-in-differences (cross-segment minus segment-local).

    Cases are resampled within each capability, so every replicate keeps the design's 6-8 cases per capability.
    """
    cases, cross, M, cols = _pass_matrix(rows)
    doc_cols = np.array([m == "document" for _, m in cols])
    cap_of = {r["case"]: r["capability"] for r in rows}
    idx_by_cap: dict[str, np.ndarray] = {}
    for i, c in enumerate(cases):
        idx_by_cap.setdefault(cap_of[c], []).append(i)
    idx_by_cap = {k: np.array(v) for k, v in idx_by_cap.items()}

    def delta(sel: np.ndarray) -> float:
        sub = M[sel]
        return 100 * (np.nanmean(sub[:, doc_cols]) - np.nanmean(sub[:, ~doc_cols]))

    def stat(index_map) -> dict:
        out = {}
        for name, caps in groups.items():
            out[name] = delta(np.concatenate([index_map[c] for c in caps]))
        return out

    point = stat(idx_by_cap)
    rng = np.random.default_rng(seed)
    reps = {k: np.empty(b) for k in groups}
    for t in range(b):
        sampled = {c: rng.choice(ix, size=len(ix), replace=True) for c, ix in idx_by_cap.items()}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)   # a resample can have an all-nan column
            s = stat(sampled)
        for k in groups:
            reps[k][t] = s[k]
    return {k: {"delta_pp": point[k], "ci_low": float(np.nanpercentile(reps[k], 2.5)),
                "ci_high": float(np.nanpercentile(reps[k], 97.5))} for k in groups} | {
        "_replicates": reps}


def did_from_replicates(boot: dict, a: str, b_: str) -> dict:
    d = boot["_replicates"][a] - boot["_replicates"][b_]
    return {"delta_pp": boot[a]["delta_pp"] - boot[b_]["delta_pp"],
            "ci_low": float(np.nanpercentile(d, 2.5)), "ci_high": float(np.nanpercentile(d, 97.5))}


def gee_logit(rows: list[dict]) -> dict:
    """logit P(pass) = engine + document + cross_segment + document x cross_segment, GEE (exchangeable
    working correlation) clustered by case. Returns odds ratios with robust 95% CIs.

    The interaction is the test of RQ1: does document context help cross-segment capabilities more than
    segment-local ones? `document_within_cross` is the document effect for cross-segment capabilities
    (document + interaction)."""
    import statsmodels.api as sm

    d = [r for r in rows if r["status"] != "unverified"]
    engines = sorted({r["engine"] for r in d})
    base = engines[0]
    names = ["const"] + [f"engine[{e}]" for e in engines if e != base] + ["document", "cross_segment",
                                                                         "document:cross_segment"]
    X = np.array([[1.0] + [float(r["engine"] == e) for e in engines if e != base]
                  + [float(r["mode"] == "document"), float(r["cross_segment"]),
                     float(r["mode"] == "document" and r["cross_segment"])] for r in d])
    y = np.array([float(r["status"] == "pass") for r in d])
    groups = np.array([r["case"] for r in d])
    model = sm.GEE(y, X, groups=groups, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable())
    res = model.fit()
    params, cov = np.asarray(res.params), np.asarray(res.cov_params())
    out = {}
    for i, n in enumerate(names):
        se = float(np.sqrt(cov[i, i]))
        out[n] = _or(params[i], se, float(res.pvalues[i]))
    # linear contrast: document + document:cross_segment
    i, j = names.index("document"), names.index("document:cross_segment")
    est = params[i] + params[j]
    se = float(np.sqrt(cov[i, i] + cov[j, j] + 2 * cov[i, j]))
    from scipy.stats import norm
    out["document_within_cross"] = _or(est, se, float(2 * norm.sf(abs(est / se))))
    out["_n_obs"], out["_n_cases"] = len(y), len(set(groups))
    return out


def _or(b: float, se: float, p: float) -> dict:
    return {"odds_ratio": float(np.exp(b)), "ci_low": float(np.exp(b - 1.96 * se)),
            "ci_high": float(np.exp(b + 1.96 * se)), "p": p}
