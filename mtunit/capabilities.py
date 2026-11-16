"""Capability taxonomy: the 'units' an MT/LLM translation engine is tested on.

cross_segment=True  → the correct output depends on information in ANOTHER segment, so a
                      segment-by-segment pipeline (and segment-level QE) can't see the whole picture.
"""

CAPABILITIES = {
    # ---- segment-local capabilities
    "negation": dict(cross_segment=False, desc=(
        "Negation and polarity must survive: 'not', 'never', 'no longer', 'unless', 'without', double negatives, "
        "'cannot' vs 'can'. Include sentences where dropping or adding a negation still reads fluently.")),
    "numbers_locale": dict(cross_segment=False, desc=(
        "Numbers, units, decimals, thousands separators, dates, times, currencies and percentages must keep their "
        "value, and be formatted for Spain (decimal comma, 24h time, day-month order, € after the number).")),
    "placeholders_tags": dict(cross_segment=False, desc=(
        "Software strings with placeholders ({name}, {0}, %s, %d, {{count}}), inline tags (<b>, <a href>, <br/>), "
        "and markdown must be preserved exactly and stay grammatically placed.")),
    "dnt": dict(cross_segment=False, desc=(
        "Do-not-translate items stay verbatim: product and brand names, feature names in quotes, code, file paths, "
        "keyboard shortcuts, URLs, error codes.")),
    "condition_scope": dict(cross_segment=False, desc=(
        "Logical scope: 'and' vs 'or', 'only if', 'either…or', 'all/some/none', 'at least/at most', 'before/after', "
        "exceptions ('except when'). The translation must keep exactly the same logic.")),
    # ---- cross-segment capabilities
    "coreference_agreement": dict(cross_segment=True, desc=(
        "A person/thing is introduced in an earlier segment and referred to later by a pronoun or with no explicit "
        "subject; Spanish needs the right gender/number agreement or explicit referent (e.g. 'The nurse checked the "
        "chart.' / 'She was tired.' → 'cansada'; 'the app' (feminine 'la aplicación') vs 'the file' (masculine)).")),
    "term_consistency": dict(cross_segment=True, desc=(
        "A key term (product concept, legal defined term, UI concept) appears in several segments and must be "
        "rendered with ONE consistent Spanish term throughout, even though several synonyms would be correct "
        "in isolation (e.g. 'workspace', 'account holder', 'dosage form', 'subscription').")),
    "register_consistency": dict(cross_segment=True, desc=(
        "The text addresses the reader in several segments; the Spanish must use ONE form of address (tú or usted) "
        "consistently across all segments, including imperatives and possessives.")),
    "implicit_subject_ellipsis": dict(cross_segment=True, desc=(
        "Later segments omit information supplied earlier: ellipsis, 'Then close it.', 'Do the same for the other "
        "one.', 'This also applies to…'. Translations must resolve 'it/this/the same' correctly.")),
    "list_inheritance": dict(cross_segment=True, desc=(
        "A lead-in segment ('Do not use the device:', 'You may cancel only if:', 'Contact your doctor if you:') is "
        "followed by list-item segments that inherit its condition/negation/verb. Each item's translation must fit "
        "the lead-in grammatically and keep its meaning.")),
    "context_disambiguation": dict(cross_segment=True, desc=(
        "An ambiguous word ('charge', 'scale', 'release', 'plate', 'bank', 'run', 'tablet', 'record') is "
        "disambiguated only by an EARLIER segment. The translation must choose the sense implied by context.")),
    "ui_reference_consistency": dict(cross_segment=True, desc=(
        "A UI label is given in one segment (e.g. a button string 'Export' or menu 'Settings') and referenced in "
        "instructions in later segments ('Click Export'); the referenced label must match the label's translation "
        "exactly.")),
}

DOMAINS = {
    "software_ui_help": "software UI strings and help-center articles",
    "marketing": "marketing and e-commerce copy",
    "legal_terms": "terms of service, contracts and privacy policies",
    "medical_patient": "medical device and patient-information texts",
}
