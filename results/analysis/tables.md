## rq1_table

| capability | cross-segment | scout seg | scout doc | nano seg | nano doc | mini seg | mini doc |
|---|---|---|---|---|---|---|---|
| negation |  | 7/8 | 8/8 | 8/8 | 8/8 | 8/8 | 7/8 |
| numbers & locale formats |  | 5/8 | 5/8 | 7/8 | 7/8 | 8/8 | 8/8 |
| placeholders/tags |  | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| do-not-translate terms |  | 5/7 | 5/7 | 6/7 | 7/7 | 5/7 | 5/7 |
| logical/condition scope |  | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| pronoun & gender agreement | yes | 6/8 | 7/8 | 4/8 | 6/8 | 7/8 | 8/8 |
| terminology consistency | yes | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 |
| register consistency | yes | 1/7 | 5/7 | 4/7 | 7/8 | 6/8 | 6/7 |
| implicit subjects/ellipsis | yes | 5/8 | 7/8 | 4/8 | 7/8 | 6/8 | 8/8 |
| list items inheriting a lead-in | yes | 3/8 | 8/8 | 5/8 | 8/8 | 4/8 | 8/8 |
| context-dependent word sense | yes | 6/8 | 6/8 | 7/8 | 8/8 | 8/8 | 8/8 |
| UI-label references | yes | 5/6 | 5/6 | 3/6 | 3/6 | 4/6 | 4/6 |
| **segment-local** | | **85%** | **87%** | **95%** | **97%** | **95%** | **92%** |
| **cross-segment** | | **63%** | **87%** | **65%** | **87%** | **79%** | **94%** |

## rq1_tests

| | document − segment pass rate, 95% CI | failed only in segment mode | failed only in document mode | sign test |
|---|---|---|---|---|
| cross-segment capabilities | +20 pp [+11, +28] | 33 | 4 | p = 1×10⁻⁶ |
| segment-local capabilities | +1 pp [-3, +4] | 3 | 2 | p = 1.00 |
| **difference (cross − local)** | **+19 pp [+10, +28]** | | | |

GEE logistic regression on all 548 decided engine × mode × case rows, clustered by case (92 cases), with engine as a covariate:

| term | odds ratio [95% CI] | p |
|---|---|---|
| document mode (segment-local capabilities) | 1.1 [0.7, 1.8] | 0.64 |
| document mode (cross-segment capabilities) | 3.7 [1.9, 7.1] | 1×10⁻⁴ |
| **document × cross-segment interaction** | **3.3 [1.4, 7.4]** | **0.005** |

## rq1_caps

| capability | document − segment, 95% CI | failed only seg / only doc | sign test p (Holm) |
|---|---|---|---|
| pronoun & gender agreement | +17 pp [-4, +38] | 5 / 1 | 1.00 |
| terminology consistency | +0 pp [+0, +0] | 0 / 0 | 1.00 |
| register consistency | +32 pp [+5, +60] | 6 / 1 | 1.00 |
| implicit subjects/ellipsis | +29 pp [+0, +58] | 8 / 1 | 0.43 |
| list items inheriting a lead-in | +50 pp [+21, +79] | 12 / 0 | 0.006 |
| context-dependent word sense | +4 pp [-12, +25] | 2 / 1 | 1.00 |
| UI-label references | +0 pp [+0, +0] | 0 / 0 | 1.00 |
| negation *(control)* | +0 pp [-12, +12] | 1 / 1 | 1.00 |
| numbers & locale formats *(control)* | +0 pp [-12, +12] | 1 / 1 | 1.00 |
| placeholders/tags *(control)* | +0 pp [+0, +0] | 0 / 0 | 1.00 |
| do-not-translate terms *(control)* | +5 pp [+0, +14] | 1 / 0 | 1.00 |
| logical/condition scope *(control)* | +0 pp [+0, +0] | 0 / 0 | 1.00 |

## rq2_table

| capability | real errors | QE identified (any severity) | QE major/critical flag in the case |
|---|---|---|---|
| pronoun & gender agreement | 11 | 2 | 1 |
| register consistency | 22 | 13 | 1 |
| implicit subjects/ellipsis | 11 | 4 | 2 |
| list items inheriting a lead-in | 17 | 0 | 1 |
| context-dependent word sense | 5 | 5 | 3 |
| UI-label references | 17 | 12 | 4 |
| negation *(control)* | 2 | 2 | 2 |
| numbers & locale formats *(control)* | 8 | 4 | 0 |
| do-not-translate terms *(control)* | 9 | 5 | 0 |
| **cross-segment total** | **83** | **36 (43%)** | **12 (14%)** |
| **segment-local total** | **19** | **11 (58%)** | **2 (11%)** |

## rq2_types

| error type | evidence is… | real errors | QE identified |
|---|---|---|---|
| Pronoun gender set by a noun in an earlier segment | another segment | 14 | **0** |
| List item doesn't complete its lead-in | another segment | 17 | **0** |
| Informal (tú) text slips into usted | another segment | 7 | **0** |
| Formal (usted) text slips into tú | inside the segment | 8 | **8** |
| tú used consistently in formal text (document mode) | inside the segment | 5 | **5** |
| Pronoun/reference error visible inside the segment | inside the segment | 6 | **6** |
| Segment-local capabilities (negation, numbers, DNT) | inside the segment | 19 | **11** |

## rq3_table

| capability | failures | test artifacts | real errors |
|---|---|---|---|
| pronoun & gender agreement | 15 | 4 | 11 |
| register consistency | 24 | 2 | 22 |
| implicit subjects/ellipsis | 15 | 4 | 11 |
| list items inheriting a lead-in | 17 | 0 | 17 |
| context-dependent word sense | 9 | 4 | 5 |
| UI-label references | 27 | 10 | 17 |
| negation | 2 | 0 | 2 |
| numbers & locale formats | 10 | 2 | 8 |
| do-not-translate terms | 14 | 5 | 9 |
| **total** | **133** | **31 (23%)** | **102 (77%)** |

## bench_stacks

| model | checks run | cross-segment errors, any flag | cross-segment errors, major/critical flag | segment-local errors, major/critical flag | clean segments flagged major/critical | cost per 100 segments |
|---|---|---|---|---|---|---|
| gpt-5.4-mini | segment QE alone | 17% [6–32] | **2% [0–6]** | 98% [95–100] | 15% | $0.10 |
| gpt-5.4-mini | segment QE + checklist | 65% [50–78] | **62% [49–76]** | 98% [95–100] | 18% | $0.15 |
| gpt-5.4-mini | context QE alone | 62% [52–73] | **8% [0–18]** | 90% [80–98] | 10% | $0.22 |
| gpt-5.4-mini | context QE + checklist | 69% [56–81] | **62% [49–76]** | 93% [85–100] | 12% | $0.28 |
| gpt-5.6-luna | segment QE alone | 17% [6–29] | **0% [0–0]** | 100% [100–100] | 16% | $0.03 |
| gpt-5.6-luna | segment QE + checklist | 71% [60–82] | **65% [52–76]** | 100% [100–100] | 22% | $0.05 |
| gpt-5.6-luna | context QE alone | 71% [60–82] | **2% [0–6]** | 97% [92–100] | 7% | $0.08 |
| gpt-5.6-luna | context QE + checklist | 81% [71–91] | **65% [52–76]** | 98% [95–100] | 14% | $0.10 |

## bench_recall

| detector | model | cross-segment errors | segment-local errors |
|---|---|---|---|
| segment QE | gpt-5.4-mini | 17% [6–32] | 98% [95–100] |
| segment QE | gpt-5.6-luna | 17% [6–29] | 100% [100–100] |
| segment QE + document context | gpt-5.4-mini | 62% [52–73] | 97% [91–100] |
| segment QE + document context | gpt-5.6-luna | 71% [60–82] | 98% [95–100] |
| whole-document QE | gpt-5.4-mini | 40% [27–52] | 88% [79–96] |
| whole-document QE | gpt-5.6-luna | 58% [49–69] | 95% [87–100] |
| document checklist (7 unit tests) | gpt-5.4-mini | 62% [49–76] | 83% [73–92] |
| document checklist (7 unit tests) | gpt-5.6-luna | 65% [52–76] | 97% [92–100] |

## bench_types

| error type | evidence | n | segment QE | segment QE + document context | whole-document QE | document checklist (7 unit tests) |
|---|---|---|---|---|---|---|
| agreement | other segment | 12 | 17% / 17% | 33% / 25% | 17% / 25% | 33% / 50% |
| register | other segment | 12 | 33% / 0% | 100% / 100% | 92% / 100% | 100% / 100% |
| terminology | other segment | 12 | 0% / 8% | 17% / 58% | 0% / 25% | 17% / 17% |
| list_fit | other segment | 12 | 17% / 42% | 100% / 100% | 50% / 83% | 100% / 92% |
| negation | same segment | 12 | 100% / 100% | 100% / 100% | 100% / 100% | 100% / 100% |
| number | same segment | 12 | 100% / 100% | 100% / 100% | 100% / 100% | 100% / 100% |
| omission | same segment | 12 | 100% / 100% | 100% / 100% | 75% / 92% | 58% / 92% |
| mistranslation | same segment | 12 | 100% / 100% | 100% / 100% | 100% / 100% | 92% / 100% |
| condition | same segment | 12 | 92% / 100% | 83% / 92% | 67% / 83% | 67% / 92% |

Each cell: gpt-5.4-mini / gpt-5.6-luna.

## bench_false_alarms

| detector | model | clean segments flagged, any severity | major/critical | cost per 100 segments (leaflets) |
|---|---|---|---|---|
| segment QE | gpt-5.4-mini | 32% | 15% | $0.10 |
| segment QE | gpt-5.6-luna | 36% | 16% | $0.03 |
| segment QE + document context | gpt-5.4-mini | 26% | 10% | $0.22 |
| segment QE + document context | gpt-5.6-luna | 30% | 7% | $0.08 |
| whole-document QE | gpt-5.4-mini | 9% | 4% | $0.01 |
| whole-document QE | gpt-5.6-luna | 18% | 6% | $0.005 |
| document checklist (7 unit tests) | gpt-5.4-mini | 11% | 11% | $0.05 |
| document checklist (7 unit tests) | gpt-5.6-luna | 15% | 15% | $0.02 |

## bench_pilot

| detector | gpt-5.4: any flag | gpt-5.4: major/critical | gpt-5.4-mini: any flag | gpt-5.4-mini: major/critical |
|---|---|---|---|---|
| segment QE | 4/13 | 0/13 | 2/13 | 0/13 |
| segment QE + document context | 11/13 | 1/13 | 7/13 | 0/13 |
| whole-document QE | 10/13 | 3/13 | 6/13 | 0/13 |
| document checklist (7 unit tests) | 6/13 | 6/13 | 7/13 | 7/13 |
