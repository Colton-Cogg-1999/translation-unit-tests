"""Tests for transtest's rule-based checks (no LLM / embeddings needed)."""
from transtest.checks import Context, run_check
from transtest.checks.deterministic import _normalise_number, extract_numbers
from transtest.model import Document, Suite, TestSpec, split_sentences


def ctx(src: str, tgt: str, glossary=None) -> Context:
    s = Document(src, "en")
    suite = Suite("t", s, "es", [], glossary=glossary or [])
    return Context(suite, s, Document(tgt, "es"))


def test_number_normalisation_is_locale_agnostic():
    assert _normalise_number("4,000") == _normalise_number("4.000") == "4000"
    assert _normalise_number("0,5") == _normalise_number("0.5") == "0.5"
    assert _normalise_number("1.000.000") == "1000000"
    assert _normalise_number("4,000.25") == _normalise_number("4.000,25") == "4000.25"


def test_numbers_check_flags_changed_dose():
    c = ctx("Do not take more than 8 tablets (4,000 mg).", "No tome más de 8 comprimidos (3.000 mg).")
    r = run_check(TestSpec("numbers", "n"), c)
    assert r.status == "fail" and "4000" in r.message


def test_numbers_check_passes_on_locale_formatting():
    c = ctx("Take 2 tablets (1,000 mg) every 4 hours.", "Tome 2 comprimidos (1.000 mg) cada 4 horas.")
    assert run_check(TestSpec("numbers", "n"), c).status == "pass"


def test_term_consistency_detects_mixed_variants():
    g = [{"source": "tablet", "target": ["comprimidos"], "forbidden": ["tabletas"]}]
    c = ctx("Take 2 tablets. Swallow the tablets.", "Tome 2 comprimidos. Trague las tabletas.", g)
    spec = TestSpec("term_consistency", "tc", params={"terms": [
        {"source": "tablet", "variants": ["comprimido|comprimidos", "tableta|tabletas"]}]})
    assert run_check(spec, c).status == "fail"


def test_sentence_splitter_keeps_abbreviations():
    assert split_sentences("Ask Dr. Smith. Then rest.") == ["Ask Dr. Smith.", "Then rest."]
    assert split_sentences("# Title\n- item one. ¿Qué es?") == ["Title", "item one.", "¿Qué es?"]


def test_unknown_check_type_is_an_error_not_a_crash():
    r = run_check(TestSpec("nope", "x"), ctx("a", "b"))
    assert r.status == "error"
