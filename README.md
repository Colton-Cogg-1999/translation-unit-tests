# What Segment-Level QE Can't See

*An exploratory study of document-level translation errors, measured with AI-generated unit tests for
MT/LLM engines (English → Spanish).*

## Summary

Localization pipelines translate and quality-check text **one segment at a time**. Segment-level quality
estimation (QE) asks one question: *is this target a good translation of this source?* This study shows a
class of errors where the answer is "yes" for every segment, and the document is still wrong:

* A pronoun takes the wrong gender because its noun is in the previous segment.
* One sentence addresses the reader as *usted* while the rest of the text uses *tú*.
* A list item is a fine sentence alone but doesn't grammatically complete its lead-in.

QE can't catch these, however good the QE model is, because the information needed is in a segment it never
sees. They need checks over the whole document. This project writes those checks as **unit tests**: explicit
assertions about the translated document, such as "pronouns agree with their referents", "register is
consistent", "list items complete the lead-in" and "the maximum daily dose is preserved". It then measures
what they catch.

**Main findings**

1. **Segment QE missed every gender-agreement and list error.** In 14 cases a pronoun had the wrong gender
   for a noun in an earlier segment (e.g. *devuélvelo* referring to *la crema*). In 17 cases a list item
   didn't fit its lead-in. QE identified **0 of 14** and **0 of 17**.
2. **Segment QE judges formality against its own default, not against the document.** It flagged *tú* as "too
   informal" in formal text, always at minor severity. It never noticed when an informal (*tú*) text slipped
   into *usted* (0 of 6), because a formal sentence looks fine in isolation.
3. **Segment-by-segment translation causes these errors.** Pooled over three engines, cross-segment tests
   passed 89% of the time with whole-document translation and 69% segment by segment (paired sign test
   p ≈ 1×10⁻⁶). Segment-local capabilities, the control group, were unchanged (92% vs 91%). The direction was
   the same in all three engines.
4. **Overall, QE gave a major/critical flag to only 14% of the real errors the tests found** (14 of 102).
5. **Unit tests are cheap to generate.** An LLM-written suite of 92 cases cost about $10 to run, and 77% of
   its failures were confirmed real errors. The other 23% were over-specific assertions, so failures need a
   second review.

## Correct segments, wrong document

All examples are real outputs from this study (segment-by-segment translation). Segment QE reported **no
errors** on every segment shown.

**Gender agreement across segments** (GPT-5.4 mini)

| # | source | translation | problem |
|---|---|---|---|
| 1 | Try our new moisturizing cream for 30 days. | Prueba nuestra nueva **crema** hidratante durante 30 días. | |
| 2 | If you don't love it, send it back. | Si no te encanta, **devuélvelo**. | *crema* is feminine → *devuélvela* |

| # | source | translation | problem |
|---|---|---|---|
| 1 | Our new sneakers are lightweight and breathable. | Nuestras nuevas **zapatillas** son ligeras y transpirables. | |
| 2 | Order them today, and they arrive tomorrow. | **Pídelos** hoy y te llegarán mañana. | *zapatillas* is feminine → *pídelas* |

Read alone, *Si no te encanta, devuélvelo* is a correct translation of *If you don't love it, send it back*.
The English source has no gender, so nothing in the segment tells QE that the pronoun is wrong.

**Formality drift** (Llama 4 Scout)

| # | source | translation | register |
|---|---|---|---|
| 1 | To change your language, open Settings. | Para cambiar tu idioma, **abre** Ajustes. | tú |
| 2 | Select Language and choose an option from the list. | **Seleccione** el idioma y **elija** una opción de la lista. | usted |
| 3 | If you need help, contact our support team. | Si **necesitas** ayuda, **ponte** en contacto con nuestro equipo de soporte. | tú |

**List items that don't complete the lead-in** (GPT-5.4 mini)

| # | source | translation | problem |
|---|---|---|---|
| 1 | Do not use the device if you: | No utilice el dispositivo si: | singular *usted* |
| 2 | are pregnant | **están embarazadas** | 3rd-person plural |
| 3 | have a pacemaker | tiene un marcapasos | ✓ |
| 4 | are allergic to nickel | **son alérgicos** al níquel | 3rd-person plural |

In this medical-device warning, items 2 and 4 address a different, plural subject. Each is grammatical on
its own.

## Unit tests vs. segment QE

The two methods answer different questions.

| | segment-level QE | document unit tests |
|---|---|---|
| question | Is this segment a good translation of its source? | Does the translated document meet these requirements? |
| input | one (source, target) pair ([`transtest/segqe.py`](transtest/segqe.py)) | the whole document, plus the requirements |
| output | error annotations and a score | pass/fail per requirement (JUnit XML, so it can run in CI) |
| can see | mistranslations, omissions and fluency problems inside a segment | agreement, consistency and coverage across segments; explicit requirements |
| cannot see | anything that depends on another segment | anything nobody wrote a test for |

Unit tests also let you state the **requirements that matter for a given text**, instead of relying on a
general quality score. The pilot study's patient-leaflet suite, for example, includes:

* *"You must not take more than 8 tablets (4,000 mg) in 24 hours"* (a critical meaning assertion)
* every number in the source appears correctly in the target (deterministic check)
* *tablet* is translated as *comprimido*, never *tableta/pastilla*, throughout the document (glossary and
  consistency)
* the reader is addressed with *usted* everywhere (register)
* *"What is the maximum daily dose for someone with liver problems?"* is answered correctly from the
  translation alone (a QA probe that combines information across sentences)

These are not alternatives to QE. Segment QE is good at what it can see, and it caught some meaning errors in
the pilot that the tests missed. The point is that some properties of a translation only exist at the document
level, and they need a check that looks at the document.

## Research questions

* **RQ1.** Compared with whole-document translation, does segment-by-segment translation lower pass rates on
  capabilities that need context beyond the segment, and leave segment-local capabilities unchanged?
* **RQ2.** When those failures occur, does segment-level QE detect them?
* **RQ3.** Can an LLM produce a usable capability test suite for translation, and how often are its
  assertions wrong?
* **Pilot.** Can a requirement-based test suite for one document act as a QA check on its translation, and
  can mutation testing measure how good that suite is?

## Method

**Capabilities.** Twelve capabilities were tested, in the style of
[CheckList](https://aclanthology.org/2020.acl-main.442/) behavioural testing, in two groups:

| segment-local (control) | cross-segment |
|---|---|
| negation · numbers & locale formats · placeholders/tags · do-not-translate terms · logical/condition scope | pronoun & gender agreement · terminology consistency · register consistency · implicit subjects/ellipsis · list items inheriting a lead-in · context-dependent word sense · UI-label references |

**Test generation and validation.**
* Claude Sonnet 5.5 generated 8 cases per capability, spread across software/UI, marketing, legal and medical
  text. Each case has 1–6 source segments and 1–3 assertions about the Spanish output. Assertions are either
  deterministic (`preserve`, `contains`, `not_contains`) or grounded LLM judgments.
* Each case was translated whole-document by GPT-5.4 to produce a gold translation. Assertions that failed
  on the gold translation were dropped as wrong or too strict. **92/96 cases and 194/207 assertions** were kept.

**Engines and conditions.** Llama 4 Scout, GPT-5.4 nano and GPT-5.4 mini, each run in two modes:
* *segment*: one request per segment with no surrounding context, as a TMS sends text;
* *document*: all segments of a case in one request.

**Baseline QE.** Every output was also scored by MQM-style segment-level QE (Claude Sonnet 5.5, one segment
at a time). A segment counts as *flagged* if QE reports a major or critical error.

**Adjudication.** Every assertion failure was reviewed by GPT-5.4, which neither generated nor judged the
tests. It answered two questions: is this a real error a reviewer would fix, and did any segment-QE comment,
at any severity, describe the same problem?

## Results

### RQ1: Segmentation causes cross-segment failures

| capability | cross-segment | scout seg | scout doc | nano seg | nano doc | mini seg | mini doc |
|---|---|---|---|---|---|---|---|
| negation | | 7/8 | 8/8 | 8/8 | 8/8 | 8/8 | 7/8 |
| numbers_locale | | 5/8 | 5/8 | 7/8 | 7/8 | 8/8 | 8/8 |
| placeholders_tags | | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| dnt | | 5/7 | 5/7 | 6/7 | 7/7 | 5/7 | 5/7 |
| condition_scope | | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| coreference_agreement | yes | 6/8 | 7/8 | 4/8 | 6/8 | 7/8 | 8/8 |
| term_consistency | yes | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 |
| register_consistency | yes | 1/7 | 5/7 | 4/7 | 7/8 | 6/8 | 6/7 |
| implicit_subject_ellipsis | yes | 5/8 | 7/8 | 4/8 | 7/8 | 6/8 | 8/8 |
| list_inheritance | yes | 3/8 | 8/8 | 5/8 | 8/8 | 4/8 | 8/8 |
| context_disambiguation | yes | 6/8 | 6/8 | 7/8 | 8/8 | 8/8 | 8/8 |
| ui_reference_consistency | yes | 5/6 | 5/6 | 3/6 | 3/6 | 4/6 | 4/6 |
| **segment-local** | | **85%** | **87%** | **95%** | **97%** | **95%** | **92%** |
| **cross-segment** | | **63%** | **87%** | **65%** | **87%** | **79%** | **94%** |

Denominators vary slightly where a judge verdict was ungrounded and excluded.

| paired by engine × case | failed only in segment mode | failed only in document mode | sign test |
|---|---|---|---|
| cross-segment capabilities | 33 | 4 | p ≈ 1×10⁻⁶ |
| segment-local capabilities | 3 | 2 | n.s. |

* The largest effects were in **list inheritance** (pooled 12/24 → 24/24 with document context), **register**
  and **implicit subjects**. These are the capabilities where Spanish grammar depends on an earlier segment.
* The weakest engine lost the most from segmentation (Scout −24 points); the strongest lost the least
  (mini −15).
* Two cross-segment capabilities showed no effect. *Terminology consistency* never failed, which suggests the
  generated cases were too easy. *UI-label references* scored the same in both modes.

### RQ2: Segment QE misses what it can't see

133 assertion failures; **102 (77%)** adjudicated as real errors. QE flagged 14 of the 102 (14%) as
major/critical.

| capability | real errors | QE identified (any severity) |
|---|---|---|
| list_inheritance | 17 | **0** |
| coreference_agreement | 11 | 2 |
| implicit_subject_ellipsis | 11 | 4 |
| register_consistency | 22 | 13 *(all minor)* |
| ui_reference_consistency | 17 | 12 |
| context_disambiguation | 5 | 5 |
| numbers_locale | 8 | 4 |
| dnt | 9 | 5 |
| negation | 2 | 2 |

Hand-classifying the adjudicator's notes (`results/mtunit/adjudication.json`) shows a clear split. QE identified
an error when a symptom was visible *inside* the segment, and missed it when the evidence was in another
segment:

* **Pronoun agreement.** Of the 22 coreference and implicit-subject errors, 14 were a pronoun with the wrong
  gender for a noun in an earlier segment, and QE identified **none** of them. The 6 errors QE did identify
  were visible inside the segment: a mistranslated sentence, an added pronoun, plural *them* rendered as
  singular, and an awkward neuter *lo último*.
* **Register.** All 13 register identifications were QE remarking that *tú* is informal for legal or patient
  text. Five of them were document-mode translations that used *tú* consistently, which is a style preference
  rather than an inconsistency. None was rated major. In the 6 failures where an informal text slipped into
  *usted*, QE identified nothing.
* **List inheritance.** 0 of 17 identified, because each item is a well-formed fragment on its own.

QE also flagged at least one segment in 10 of the 464 cases that passed every test (QE noise, or issues
outside the tested capabilities).

### RQ3: Reliability of generated tests

* Validation removed 4 of 96 cases and 13 of 207 assertions that failed even on the gold translation.
* Of the 133 failures that remained, **31 (23%)** were test artifacts. They were mostly assertions narrower than
  the range of correct translations, for example requiring *Iniciar* where *Inicio* is equally correct.
* Reliability varied by capability. Word-sense (4/9), UI-label (10/27) and do-not-translate (5/14) assertions
  produced the most artifacts. List-inheritance assertions produced none (17/17 real).
* Generated suites are cheap and catch real errors, but their failures need a second review (here an
  independent model; in production, a quick human look) before they are acted on.

Full dashboard: `results/mtunit/report.md` · failures QE missed: `results/mtunit/qe_misses.md` · raw runs and
JUnit XML: `results/mtunit/runs/`, `results/mtunit/junit/`.

## Pilot study: Requirement tests for one document (`transtest/`)

Before the main study, a smaller exploration used a hand-written suite of requirement tests for a single
document (a fictional patient leaflet) and ran it against its Spanish translation.

* **Planted errors.** The leaflet was given 9 planted errors, each in fluent, grammatical Spanish. The suite
  caught **8/9** with no false alarms on the correct translation. LLM segment QE caught 7/9. The two it missed were
  the errors that are invisible one sentence at a time: *tablet* translated three different ways, and a
  switch from *usted* to *tú* midway through. LaBSE similarity caught 2/9. QE caught one meaning error the suite missed: "avoid alcohol"
  softened to "avoid alcohol *in excess*".
* **Mutation testing.** To measure how good the suite was, 14 single-edit mutants of a correct translation
  were created. The first version of the suite scored 0.71 and let *"No tome más de 8 comprimidos"* →
  *"Tome más de 8 comprimidos"* survive, deleting the "not" from a dosing limit. Three added tests raised the
  score to 0.86. The only surviving mutants then preserved the meaning.
* **Real MT.** Translating sentence by sentence, a small local model (Qwen3-4B) mixed *comprimidos /
  tabletas / pastillas* and switched to *tú* in 6 sentences, and the suite flagged both. GPT-5.4 mini produced
  clean output in both modes.

This was a single document, used for illustration. It motivated the larger generated-suite design above.

## Limitations

* **One language pair** (EN→ES). Spanish gender and register make cross-segment effects easy to see. The
  structural argument applies to any language with agreement or formality distinctions, but the rates will
  differ.
* **LLM engines only.** Classic NMT engines (DeepL, Google) were not tested.
* **Small suite.** 92 cases, with 6–8 per capability, so per-capability numbers are noisy.
* **LLMs throughout.** The test generator, assertion judge and QE model are the same model family (Claude
  Sonnet 5.5). The gold translator and adjudicator are both GPT-5.4. No human annotation was done, and the
  error-type breakdown in RQ2 is a hand classification of the adjudicator's notes.
* **Single gold translation** for validation, which is why over-specific assertions got through.
* **Segment-mode baseline is strict.** Production TMS pipelines sometimes pass neighbouring segments to the
  engine or the QE step. This setup measures the case with no context at all.

## Reproducing

```bash
uv sync
cp .env.example .env            # OpenRouter key, or any OpenAI-compatible endpoint
uv run python -m common.check   # one small call per configured model

uv run python -m mtunit.run --per-cap 8      # generate → validate → run engines → QE → report
uv run python -m mtunit.adjudicate           # independent review of every failure
```

Engines are configurable (`--engines openai/gpt-5.4-mini,meta-llama/llama-4-scout`, any OpenRouter model id).
All LLM calls are cached in `.cache/`, so the reported numbers can be recomputed without new calls. A full
fresh run costs about $10.

Pilot study:

```bash
uv run python -m transtest calibrate transtest/examples/leaflet/suite.yaml
uv run python -m transtest run transtest/examples/leaflet/suite.yaml transtest/examples/leaflet/target_flawed.es.md
uv run python -m transtest mutate transtest/examples/leaflet/suite.yaml transtest/examples/leaflet/target_good.es.md
uv run pytest                                # unit tests for the deterministic checks
```

## Repository layout

```
mtunit/      main study: capabilities, test generation + validation, engines, assertions, run, adjudicate
transtest/   pilot study: per-document checks, runner/CLI, mutation testing, segment QE,
             examples/leaflet (fictional leaflet with good + flawed Spanish, suite.yaml), experiments/
common/      OpenAI-compatible client with disk cache, embeddings, .env loader
results/     mtunit/ (main study), transtest/ (pilot)
tests/       unit tests for the deterministic checks
```

## References

* Ribeiro et al., *Beyond Accuracy: Behavioral Testing of NLP Models with CheckList*, ACL 2020.
* Lommel et al., *Multidimensional Quality Metrics (MQM)*, 2014.
* Kocmi & Federmann, *Large Language Models Are State-of-the-Art Evaluators of Translation Quality* (GEMBA), EAMT 2023.

## License

MIT
