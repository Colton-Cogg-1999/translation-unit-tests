"""Statistics helpers, and the analysis run against the committed results."""

import numpy as np
import pytest

from analysis import stats
from analysis.__main__ import README, claims, compute, render_readme


def test_sign_test_matches_exact_binomial():
    assert stats.sign_test(0, 0) == 1.0
    assert stats.sign_test(5, 0) == pytest.approx(2 * 0.5**5)
    assert stats.sign_test(3, 2) == pytest.approx(1.0)


def test_holm_is_monotone_and_capped():
    adj = stats.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj["a"] == pytest.approx(0.03)
    assert adj["c"] == pytest.approx(0.06)
    assert adj["b"] == pytest.approx(0.06)          # max(0.04 * 1, previous 0.06)
    assert max(stats.holm({"x": 0.9, "y": 0.8}).values()) <= 1.0


def _rows(pass_seg, pass_doc, cross, n=10, cap="c"):
    rows = []
    for i in range(n):
        for mode, k in (("segment", pass_seg), ("document", pass_doc)):
            rows.append({"case": f"{cap}-{i}", "capability": cap, "cross_segment": cross, "engine": "e",
                         "mode": mode, "status": "pass" if i < k else "fail"})
    return rows


def test_bootstrap_recovers_a_known_difference():
    rows = _rows(5, 10, True, cap="x") + _rows(8, 8, False, cap="y")
    boot = stats.bootstrap_mode_effects(rows, {"cross": ["x"], "local": ["y"]}, b=500)
    assert boot["cross"]["delta_pp"] == pytest.approx(50)
    assert boot["local"]["delta_pp"] == pytest.approx(0)
    assert boot["cross"]["ci_low"] > 0 and boot["local"]["ci_low"] == boot["local"]["ci_high"] == 0
    did = stats.did_from_replicates(boot, "cross", "local")
    assert did["delta_pp"] == pytest.approx(50)
    again = stats.bootstrap_mode_effects(rows, {"cross": ["x"], "local": ["y"]}, b=500)
    assert np.array_equal(boot["_replicates"]["cross"], again["_replicates"]["cross"])   # seeded


@pytest.fixture(scope="module")
def summary():
    return compute()


def test_committed_results_reproduce_headline_numbers(summary):
    s = summary
    assert (s["paired"]["cross"]["seg_only_fail"], s["paired"]["cross"]["doc_only_fail"]) == (33, 4)
    assert (s["failures"]["real"], s["failures"]["n"]) == (102, 133)
    assert s["error_types"]["gender_agreement_cross_segment"] == {"n": 14, "qe_identified": 0}
    assert s["by_cap"]["list_inheritance"]["real"] == 17 and s["by_cap"]["list_inheritance"]["qe_identified"] == 0
    assert s["validation"]["valid_cases"] == 92
    assert s["gee"]["document:cross_segment"]["ci_low"] > 1


def test_readme_matches_results(summary):
    text = README.read_text(encoding="utf-8")
    assert render_readme(text, summary) == text, "run `uv run python -m analysis`"
    missing = [c for c in claims(summary) if c not in text]
    assert not missing, missing
