# Results

EN→ES, all models via OpenRouter. Raw outputs are in `results/`; numbers below are reproducible from the
cached runs.

## Engine unit tests (`mtunit/`, `results/mtunit/`)

**Setup**
* Test suite written by an LLM (Claude Sonnet 5.5): **12 capabilities × 8 cases** across software/UI, marketing,
  legal and medical content. Each case: 1–6 source segments + 1–3 assertions about the Spanish output.
* Validation against a careful whole-document gold translation (GPT-5.4): **92/96 cases, 194/207 assertions kept**.
* Engines: Llama 4 Scout, GPT-5.4 nano, GPT-5.4 mini; each run segment-by-segment (no context, TMS-style) and
  whole-document (all segments in one request).
* Baseline: segment-level MQM QE by the same judge model, one segment at a time, on the same outputs.
* Every failure independently adjudicated by GPT-5.4 (neither generator nor judge): real error? did QE identify it?

**Case pass rate**

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

(Denominators vary slightly where a judge verdict was ungrounded and excluded.)

**Findings**
1. **Segmenting the workload breaks cross-segment capabilities, and only those.** Paired by engine and case:
   cross-segment cases failed only in segment mode **33×** vs only in document mode **4×** (sign test **p ≈ 1×10⁻⁶**);
   segment-local capabilities 3× vs 2× (no effect). Same direction for all three engines.
2. **Segment-level QE does not see most of these failures.** 133 assertion failures; **102 (77%)** adjudicated as
   real errors. Of those, segment QE flagged the relevant segment major/critical in **14 (14%)**, and any QE comment
   (any severity) described the actual problem in **47 (46%)**.

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

3. **AI-generated tests need a second check.** 23% of failures were test artifacts: over-specific assertions that a
   single gold translation didn't expose (e.g. demanding *Iniciar* where *Inicio* is equally correct). Adjudication
   (or a light human review of failures) is part of the method.

**Caveats:** one language pair; LLM engines only (classic NMT engines such as DeepL/Google need their own keys);
92 cases; judge and adjudicator are LLMs. `results/mtunit/qe_misses.md` lists failures QE missed for spot-checking.

## Exploratory: document-level QA gates (`transtest/`, `results/transtest/`)

* **Fictional patient leaflet** with 9 planted errors (`transtest/examples/leaflet/`): a hand-written suite caught 8/9
  with 0 false alarms on the correct translation; LLM segment QE caught 7/9 but missed both document-level errors
  (terminology inconsistency, *usted*→*tú* drift); LaBSE similarity caught 2/9. Single document, illustrative only.
* **Mutation testing** (`transtest mutate`): 14 single-edit mutants of a correct translation. The hand-written suite
  scored 0.71 and let "*No tome más de 8 comprimidos*" → "*Tome más de 8 comprimidos*" survive; adding three tests
  raised it to 0.86, with only meaning-equivalent mutants surviving.
* **Real MT**: translated sentence by sentence, a small local model (Qwen3-4B) mixed *comprimidos / tabletas /
  pastillas* and switched to *tú* in 6 sentences; the suite flagged both. GPT-5.4 mini produced clean output in both modes.
