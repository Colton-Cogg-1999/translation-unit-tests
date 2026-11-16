# Cross-Segment Errors in Segment-Level Translation Pipelines

*An exploratory study using AI-generated capability tests for MT/LLM translation engines (English → Spanish).*

## Summary

Localization pipelines usually translate and quality-check text **one segment at a time**. Some
translation errors, however, depend on context outside the segment. Examples are a pronoun whose referent
is two lines earlier, a list item that has to agree grammatically with its lead-in, and *tú/usted* register
that drifts across a document. This project asks how often segmented translation causes such errors, and
whether segment-level quality estimation (QE), the usual safeguard, detects them.

To measure this, an LLM wrote a suite of behavioural test cases, in the style of
[CheckList](https://aclanthology.org/2020.acl-main.442/), covering 12 translation capabilities. The suite
was validated against a gold translation. Three LLM translation engines were then run against it twice:
once segment by segment, as a TMS sends text, and once with the whole document in one request.

Main observations:

1. **Segmentation hurts the cross-segment capabilities and leaves the others unaffected.** Pooled over three
   engines, cross-segment cases passed 69% of the time in segment mode and 89% in document mode.
   Segment-local cases passed 91% vs 92%. In paired comparisons, cross-segment cases failed only in segment
   mode 33 times and only in document mode 4 times (sign test p ≈ 1×10⁻⁶). The effect points the same way
   in all three engines.
2. **Segment-level QE rarely flags these errors as serious.** Of 102 failures confirmed as real errors,
   MQM-style segment QE marked the relevant segment major or critical in 14%, and mentioned the problem
   at any severity in 46%. For list items that don't fit their lead-in, it identified none of 17.
3. **LLM-generated tests are useful but imprecise.** 23% of test failures were artifacts of the tests
   (over-specific assertions), not translation errors. An independent adjudication step was needed to
   interpret the results.

These findings come from one language pair, 92 test cases and LLM judges throughout (see
[Limitations](#limitations)). They should be treated as an exploratory signal, not a benchmark.

## Research questions

* **RQ1.** Compared with whole-document translation, does segment-by-segment translation lower pass rates on
  capabilities that need context beyond the segment, and leave segment-local capabilities unchanged?
* **RQ2.** When those failures occur, does segment-level QE detect them?
* **RQ3.** Can an LLM produce a usable capability test suite for translation, and how often are its
  assertions wrong?
* **Pilot (exploratory).** Can per-document test suites act as a QA check on a finished translation, and can
  mutation testing measure how good such a suite is?

## Method

**Capabilities.** Twelve capabilities were defined in two groups:

| segment-local | cross-segment |
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
at a time), which shows what a typical segment-level quality check would catch.

**Adjudication.** Every assertion failure was reviewed by GPT-5.4, which neither generated nor judged the
tests. It answered two questions: is this a real error a reviewer would fix, and did any segment-QE comment,
at any severity, describe the same problem?

## Results

### RQ1: Pass rates by capability and mode

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

**Observations**
* Most of the gap comes from **list inheritance** (12/24 → 24/24 pooled), **register consistency** and
  **implicit subjects**. These are the capabilities where Spanish grammar depends directly on an earlier
  segment.
* Not every cross-segment capability was affected. *Terminology consistency* never failed in either mode,
  which suggests the generated cases were too easy. *UI-label references* scored the same in both modes, so
  their failures have some other cause.
* The weakest engine (Scout) lost the most from segmentation (−24 points). The strongest (mini) lost the
  least (−15).

### RQ2: Detection by segment-level QE

133 assertion failures in total; 102 (77%) adjudicated as real errors.

| capability | real errors | QE identified (any severity) |
|---|---|---|
| list_inheritance | 17 | **0** |
| coreference_agreement | 11 | 2 |
| implicit_subject_ellipsis | 11 | 4 |
| register_consistency | 22 | 13 |
| ui_reference_consistency | 17 | 12 |
| context_disambiguation | 5 | 5 |
| numbers_locale | 8 | 4 |
| dnt | 9 | 5 |
| negation | 2 | 2 |
| **cross-segment** | **83** | **36 (43%)** |
| **segment-local** | **19** | **11 (58%)** |

**Observations**
* At the severity that would normally stop a translation (major/critical), QE caught only 14 of the 102 real
  errors. This low catch rate also applies to segment-local errors such as locale formatting and
  do-not-translate terms. Segment QE was not a strong check on these tests in general.
* The blind spot is clearest where the error is only visible with the earlier segment in view. For list items
  and pronoun agreement, the segment is a fluent, grammatical sentence when read alone:

  | # | source | segment-by-segment output | segment QE |
  |---|---|---|---|
  | 1 | To reset your password, you must: | Para restablecer tu contraseña, debes: | ok |
  | 2 | open the Settings menu | abrir el menú Configuración | ok |
  | 3 | select Security | seleccionar Seguridad | ok |
  | 4 | click Reset | **haz clic** en Restablecer *(imperative; does not continue "debes: …")* | ok |

* In the other direction, QE flagged at least one segment in 10 of 464 cases that passed every test. These
  flags are either QE noise or issues outside the tested capabilities.

### RQ3: Reliability of generated tests

* The validation step removed 4 of 96 cases and 13 of 207 assertions that failed even on the gold translation.
* Of the 133 failures that remained, **31 (23%)** were test artifacts. They were mostly assertions narrower
  than the space of correct translations, for example requiring *Iniciar* where *Inicio* is equally correct.
  A single gold translation does not reveal these.
* The artifact rate differed by capability. Word-sense (4/9), UI-label (10/27) and do-not-translate (5/14)
  assertions were the least reliable, and list-inheritance assertions had no artifacts (17/17 real).
* In practice, generated suites are cheap to produce, but their failures need a second review by a model or
  a person before they mean anything.

Full dashboard: `results/mtunit/report.md` · failures QE missed: `results/mtunit/qe_misses.md` · raw runs and
JUnit XML: `results/mtunit/runs/`, `results/mtunit/junit/`.

## Pilot study: Document-level QA tests and mutation testing (`transtest/`)

An earlier, smaller exploration preceded the main study. It looked at test suites written *for one source
document* and run against its delivered translation.

* **Planted errors.** A fictional patient leaflet was given 9 planted errors. A hand-written suite caught
  8/9 with no false alarms on the correct translation. LLM segment QE (GEMBA-style) caught 7/9 but missed both
  document-level errors, a terminology inconsistency and *usted → tú* drift. LaBSE similarity caught 2/9.
* **Mutation testing.** 14 single-edit mutants of a correct translation were created to measure suite
  quality. The initial suite scored 0.71 and let *"No tome más de 8 comprimidos"* → *"Tome más de 8
  comprimidos"* survive. Three added tests raised the score to 0.86. The only surviving mutants then preserved
  the meaning.
* **Real MT.** Translating sentence by sentence, a small local model (Qwen3-4B) mixed *comprimidos /
  tabletas / pastillas* and switched to *tú* in 6 sentences, and the suite flagged both. GPT-5.4 mini
  produced clean output in both modes.

This is a single document and serves only as an illustration. It motivated the larger generated-suite design
above.

## Limitations

* **One language pair** (EN→ES). Spanish agreement and register make cross-segment effects visible. Other
  pairs may show more or less effect.
* **LLM engines only.** Classic NMT engines (DeepL, Google) were not tested.
* **Small suite.** 92 cases, with 6–8 per capability, so per-capability numbers are noisy.
* **LLMs throughout.** The test generator, assertion judge and QE model are the same model family (Claude
  Sonnet 5.5). The gold translator and adjudicator are both GPT-5.4. No human annotation was done, so the 77%
  "real error" rate is itself an LLM judgment.
* **Single gold translation** for validation, which is why over-specific assertions got through.
* **Segment-mode baseline is strict.** Production TMS pipelines sometimes pass neighbouring segments or
  document context to the engine. This setup measures the case with no context at all.

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
             examples/leaflet (fictional leaflet with good + flawed Spanish), experiments/
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
