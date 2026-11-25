"""mtunit assertion evaluation and report helpers, with the LLM judge faked (no network)."""

import xml.etree.ElementTree as ET

import pytest

from common.llm import CacheMiss
from mtunit import assertions
from mtunit.assertions import evaluate_assertion
from mtunit.run import case_status, junit, qe_caught

SRC = ["Try our new cream.", "If you don't love it, send it back."]
TGT = ["Prueba nuestra nueva crema.", "Si no te encanta, devuélvelo."]


def test_preserve_requires_exact_substrings():
    assert evaluate_assertion({"kind": "preserve", "strings": ["crema"]}, SRC, TGT)["status"] == "pass"
    r = evaluate_assertion({"kind": "preserve", "strings": ["{count}"]}, SRC, TGT)
    assert r["status"] == "fail" and "{count}" in r["detail"]


def test_contains_is_case_insensitive_and_segment_scoped():
    a = {"kind": "contains", "segment": 2, "any_of": ["DEVUÉLVELA", "devuélvelo"]}
    assert evaluate_assertion(a, SRC, TGT)["status"] == "pass"
    # "crema" is in segment 1 only
    assert evaluate_assertion({"kind": "contains", "segment": 2, "any_of": ["crema"]}, SRC, TGT)["status"] == "fail"
    assert evaluate_assertion({"kind": "contains", "segment": None, "any_of": ["crema"]}, SRC, TGT)["status"] == "pass"


def test_not_contains_and_out_of_range_segment():
    assert evaluate_assertion({"kind": "not_contains", "segment": 2, "any_of": ["devuélvelo"]}, SRC, TGT)["status"] == "fail"
    assert evaluate_assertion({"kind": "not_contains", "segment": 9, "any_of": ["x"]}, SRC, TGT)["status"] == "pass"


def test_unknown_kind_is_an_error_not_a_pass():
    assert evaluate_assertion({"kind": "regex"}, SRC, TGT)["status"] == "error"


def test_judge_verdict_needs_a_quote_from_the_translation(monkeypatch):
    prop = {"kind": "judge", "segment": 2, "property": "the pronoun is feminine"}
    monkeypatch.setattr(assertions, "chat_json",
                        lambda *a, **k: {"evidence": "devuélvelo", "reason": "masculine", "holds": False})
    assert evaluate_assertion(prop, SRC, TGT)["status"] == "fail"
    monkeypatch.setattr(assertions, "chat_json",
                        lambda *a, **k: {"evidence": "devuélvela", "reason": "feminine", "holds": True})
    assert evaluate_assertion(prop, SRC, TGT)["status"] == "pass"   # close enough to the output (fuzzy ≥ 85)
    monkeypatch.setattr(assertions, "chat_json",
                        lambda *a, **k: {"evidence": "texto que no aparece en ninguna parte", "holds": True})
    assert evaluate_assertion(prop, SRC, TGT)["status"] == "unverified"


def test_cache_miss_is_not_swallowed(monkeypatch):
    def miss(*a, **k):
        raise CacheMiss("offline")
    monkeypatch.setattr(assertions, "chat_json", miss)
    with pytest.raises(CacheMiss):
        evaluate_assertion({"kind": "judge", "segment": 1, "property": "x"}, SRC, TGT)


def test_case_status():
    assert case_status({"results": [{"status": "pass"}, {"status": "fail"}]}) == "fail"
    assert case_status({"results": [{"status": "pass"}, {"status": "unverified"}]}) == "unverified"
    assert case_status({"results": [{"status": "pass"}]}) == "pass"


def test_qe_caught_uses_the_asserted_segment():
    r = {"qe_flagged": [True, False]}
    assert qe_caught(r, {"kind": "judge", "segment": 1})
    assert not qe_caught(r, {"kind": "judge", "segment": 2})
    assert qe_caught(r, {"kind": "judge", "segment": None})       # whole-output assertion: any segment
    assert qe_caught(r, {"kind": "preserve", "segment": 2})       # preserve is document-wide


def test_junit_is_well_formed_with_awkward_characters():
    rows = [{"id": "c-01", "capability": "negation", "tgt": ['Dijo "no" & <b>sí</b>'], "assertions": [{"kind": "judge"}],
             "results": [{"status": "fail", "detail": 'quote " & <tag>'}]},
            {"id": "c-02", "capability": "negation", "tgt": ["ok"], "assertions": [{"kind": "judge"}],
             "results": [{"status": "unverified", "detail": ""}]}]
    root = ET.fromstring(junit(rows, "eng__segment"))
    assert root.get("tests") == "2" and root.get("failures") == "1"
    assert root.find("testcase/failure").get("message") == 'judge: quote " & <tag>'
    assert root.findall("testcase")[1].find("skipped") is not None
