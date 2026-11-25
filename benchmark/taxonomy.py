"""Planted-error taxonomy.

Each planted error is ONE edit to ONE target segment of a correct translation. Every edited segment must still
read as fluent, grammatical Spanish on its own. What differs is where the evidence of the error is:

  cross   the error can only be identified using ANOTHER segment (the edited segment, read with its own source
          segment, still looks like an acceptable translation)
  local   the error can be identified from the edited segment and its own source segment alone
"""

ERROR_TYPES: dict[str, dict] = {
    # ------------------------------------------------------------------ cross-segment
    "agreement": dict(family="cross", definition=(
        "Change the gender or number of ONE pronoun, clitic, determiner or adjective in the target segment so that "
        "it no longer agrees with the noun it refers to, where that noun is ONLY in a different segment. The English "
        "source segment must not reveal the gender/number on its own (e.g. 'it', 'them', 'they'). Example: segment 1 "
        "'Prueba nuestra nueva crema…', segment 2 'Si no te encanta, devuélvela' → 'devuélvelo'.")),
    "register": dict(family="cross", definition=(
        "Rewrite the form of address in ONE segment that addresses the reader to the other register (usted ↔ tú: "
        "verb forms, imperatives, possessives, object pronouns), while the other segments that address the reader keep "
        "the document's register. The edited segment must be a correct translation in its new register. Example: "
        "'Informe a su médico' → 'Informa a tu médico' in a document that otherwise uses usted.")),
    "terminology": dict(family="cross", definition=(
        "Pick a key term (technical, medical, product or UI term) that the translation renders the SAME way in at "
        "least one OTHER segment, and replace it in ONE segment with a different but valid translation of the same "
        "source term, so the document becomes inconsistent. Example: 'comprimido' used throughout, one segment "
        "changed to 'tableta'.")),
    "list_fit": dict(family="cross", definition=(
        "Pick a segment that grammatically continues a lead-in found in ANOTHER segment (a list item after 'No tome X "
        "si:', a step after 'Para ello, debe:', an item after a colon). Change its person, number, mood or verb form "
        "so it no longer completes the lead-in, while it stays a grammatical, faithful translation if read alone. "
        "Example: lead-in 'No utilice el dispositivo si:', item 'está embarazada' → 'están embarazadas'.")),
    # ------------------------------------------------------------------ segment-local (controls)
    "negation": dict(family="local", definition=(
        "Remove, add or flip ONE negation or polarity word so the meaning reverses ('no debe' → 'debe', 'nunca' → "
        "'siempre', 'sin' → 'con'). Keep the sentence fluent.")),
    "number": dict(family="local", definition=(
        "Change ONE number, dose, unit, frequency, duration or age to a different plausible value ('40 mg' → '80 mg', "
        "'3 horas' → '6 horas', 'menores de 18 años' → 'menores de 12 años').")),
    "omission": dict(family="local", definition=(
        "Delete ONE clause or phrase that carries information present in the source segment (a condition, a "
        "qualifier, an instruction), keeping the rest of the segment fluent and grammatical.")),
    "mistranslation": dict(family="local", definition=(
        "Replace ONE content word or phrase with a fluent but wrong meaning that a monolingual reader could not "
        "notice ('hígado' → 'riñón', 'mareo' → 'cansancio', 'aumentar' → 'reducir').")),
    "condition": dict(family="local", definition=(
        "Change the logic of ONE condition, quantifier or time relation: 'y' ↔ 'o', 'a menos que' → 'si', 'todos' → "
        "'algunos', 'al menos' → 'como máximo', 'antes de' → 'después de'.")),
}

CROSS = [k for k, v in ERROR_TYPES.items() if v["family"] == "cross"]
LOCAL = [k for k, v in ERROR_TYPES.items() if v["family"] == "local"]
