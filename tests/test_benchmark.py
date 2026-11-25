"""Planted-error benchmark logic that doesn't need the API: sampling, budget guard, scoring, flag parsing."""

import pytest

from analysis import benchmark as AB
from benchmark import budget, config, detectors, plant
from benchmark.corpus import Doc


def _cand(doc, seg, etype, edited="x"):
    return {"doc": doc, "corpus": "leaflet", "type": etype, "segment": seg, "edited": edited}


def test_queues_dedupe_across_types_and_alternate_documents():
    cands = [_cand("a", 1, "mistranslation", "posteriores"), _cand("a", 1, "condition", "posteriores"),
             _cand("a", 2, "condition", "y"), _cand("b", 3, "condition", "o"), _cand("a", 4, "condition", "u")]
    q = plant.queues(cands, seed=1)
    assert [c["segment"] for c in q[("leaflet", "mistranslation")]] == [1]
    cond = q[("leaflet", "condition")]
    assert 1 not in [c["segment"] for c in cond]            # duplicate edit kept under the first type only
    assert {cond[0]["doc"], cond[1]["doc"]} == {"a", "b"}    # round-robin: both documents before a second from "a"
    assert plant.queues(cands, seed=1) == q                  # seeded


def test_budget_guard_reserves_for_requests_in_flight(monkeypatch):
    monkeypatch.setattr(config, "BUDGET_USD", 1.0)
    monkeypatch.setattr(budget, "spent", lambda: 0.88)
    monkeypatch.setattr(budget, "_last", [0.0, 0.0])
    monkeypatch.setattr(budget, "_inflight", [0])
    budget.check()                                            # 0.88 + 1 x 0.05 < 1.0
    budget.check()                                            # 0.88 + 2 x 0.05 < 1.0
    with pytest.raises(budget.BudgetExceeded):
        budget.check()                                        # 0.88 + 3 x 0.05 >= 1.0
    budget.done()
    budget.check()                                            # one finished: room again


def test_detection_needs_the_edited_segment_and_a_matching_diagnosis():
    variants = {"v1": {"doc": "d", "corpus": "leaflet", "type": "register", "family": "cross", "segment": 3}}
    rows = [{"variant": "v1", "detector": "segment_qe", "model": "m",
             "flags": [{"segments": [3], "severity": "minor"}]},
            {"variant": "v1", "detector": "checklist", "model": "m", "flags": [{"segments": [2], "severity": "major"}]},
            {"variant": "v1", "detector": "checklist", "model": "m", "flags": []},
            {"variant": "v1", "detector": "document_qe", "model": "m",
             "flags": [{"segments": [3, 5], "severity": "major"}]}]
    diag = {("v1", "segment_qe", "m"): True, ("v1", "document_qe", "m"): False}
    out = {o["detector"]: o for o in AB.outcomes(variants, rows, diag)}
    assert out["segment_qe"]["detected"] and not out["segment_qe"]["detected_major"]
    assert not out["checklist"]["flagged"]                    # flags elsewhere don't count
    assert out["document_qe"]["flagged"] and not out["document_qe"]["detected"]   # flagged for another reason


def test_bootstrap_rate_resamples_documents():
    items = [{"corpus": "leaflet", "doc": d, "hit": h} for d, h in
             [("a", True), ("a", True), ("b", False), ("b", False), ("c", True), ("c", False)]]
    r = AB._boot_rate(items, "hit", b=2000)
    assert (r["k"], r["n"]) == (3, 6) and r["ci_low"] < 0.5 < r["ci_high"]


def test_checklist_flags_need_a_verbatim_quote(monkeypatch):
    doc = Doc("d", "leaflet", "leaflet", ("Take one tablet.", "Then rest."), ("Tome un comprimido.", "Luego descansa."))
    monkeypatch.setattr(detectors, "chat_json", lambda *a, **k: {"violations": [
        {"segments": [2], "evidence": "Luego descansa", "explanation": "tú"},
        {"segments": [9], "evidence": "texto inventado que no está", "explanation": "invented"}]})
    monkeypatch.setattr(detectors.llm, "cache_key", lambda *a, **k: "k")
    out = detectors.checklist(doc, "register", "m")
    assert [f["segments"] for f in out["flags"]] == [[2]]


def test_mqm_flag_parsing_is_defensive():
    flags = detectors._mqm_flags([{"segments": ["2", 99, "x"], "severity": "MAJOR"}, "junk", {"severity": "odd"}],
                                 None, 3)
    assert flags[0]["segments"] == [2] and flags[0]["severity"] == "major"
    assert flags[1]["severity"] == "minor" and flags[1]["segments"] == []
