"""Plant realistic translation errors into a (human) reference translation, with known ground truth.

A separate model (not the judge) performs the edits so the judge isn't grading its own errors.
"""

from __future__ import annotations

import os

from common.llm import chat_json

INJECT_MODEL = os.environ.get("L10N_INJECT_MODEL", "openai/gpt-5.4")

ERROR_TYPES = {
    # name: (doc_level, instruction)
    "polarity": (False, "Flip the polarity of ONE important instruction or statement (e.g. remove a negation, "
                        "'must not'→'may', 'do not'→'do'). Keep it fluent."),
    "number": (False, "Change ONE number, dose, unit, age or time span to a different plausible value."),
    "condition_scope": (False, "Change the logic of ONE condition: 'and'↔'or', 'all'↔'some', 'only if'→'if', "
                               "'before'↔'after', 'more than'↔'less than'."),
    "coreference": (True, "Pick ONE line whose ENGLISH source uses a pronoun or implicit subject ('It', 'They', "
                          "'This', 'these', or no explicit subject) whose referent is in an EARLIER line. Edit the "
                          "Spanish so it resolves that reference to the WRONG entity (explicitly naming another entity "
                          "from earlier lines, or using agreement/possessives that point to it). The line must be a "
                          "plausible translation of its English line read in isolation; the error should only be "
                          "visible with the surrounding context."),
    "term_inconsistency": (True, "Find a key term that the translation uses several times. In ONE or TWO later "
                                 "occurrences, replace it with a different but plausible synonym (correct in "
                                 "isolation), so the document becomes terminologically inconsistent."),
    "register_drift": (True, "Rewrite TWO or THREE consecutive lines that address the reader so they switch from "
                             "the document's formal address ('usted' forms) to informal 'tú' forms. Same meaning."),
    "omission": (False, "In ONE line, delete an important clause, condition or list item (NOT the whole line). "
                        "The result must remain fluent and grammatical."),
    "addition": (False, "In ONE line, add a short qualifier that weakens or changes the instruction "
                        "(e.g. 'si es posible', 'en exceso', 'normalmente', 'solo')."),
}

PROMPT = """You are building a test set for translation quality checking. Below is a source document
(English) and its correct Spanish translation, aligned line by line (same line numbers).

Task: introduce exactly ONE error of this type into the SPANISH translation:
{instruction}

Rules: the edited Spanish must be fluent and look like a plausible translator/MT mistake; do not
touch any other lines; prefer an edit that would matter to a reader.

Reply with JSON only:
{{"edits": [{{"line": <line number>, "new_text": "<the full edited Spanish line>"}}],
  "description": "<one sentence, in English: what changed and why it is wrong>"}}

SOURCE (en):
{src}

TRANSLATION (es):
{tgt}"""


def numbered(lines: list[str]) -> str:
    return "\n".join(f"{i + 1}: {l}" for i, l in enumerate(lines))


def plant(src_lines: list[str], tgt_lines: list[str], error_type: str) -> dict | None:
    doc_level, instruction = ERROR_TYPES[error_type]
    out = chat_json(PROMPT.format(instruction=instruction, src=numbered(src_lines), tgt=numbered(tgt_lines)),
                    max_tokens=1500, model=INJECT_MODEL)
    new = list(tgt_lines)
    edited = []
    for e in out.get("edits", [])[:4]:
        i = int(e.get("line", 0)) - 1
        txt = str(e.get("new_text", "")).strip()
        if 0 <= i < len(new) and txt and txt != new[i]:
            new[i] = txt
            edited.append(i)
    if not edited:
        return None
    return {"type": error_type, "doc_level": doc_level, "lines": edited,
            "before": [tgt_lines[i] for i in edited], "after": [new[i] for i in edited],
            "description": out.get("description", ""), "text_lines": new}
