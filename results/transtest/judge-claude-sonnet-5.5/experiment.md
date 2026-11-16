# Leaflet experiment: document unit tests vs segment-level QE

Calibration on source: {'tests': 22, 'passed': 17, 'failed': 0, 'errors': 0, 'skipped': 5, 'pass_rate': 1.0, 'penalty': 0, 'critical_failures': 0, 'verdict': 'PASS'}

## Suite results

| target | verdict | passed | failed | critical fails |
|---|---|---|---|---|
| good | PASS | 22 | 0 | 0 |
| flawed | FAIL | 8 | 14 | 7 |
| mt_sentence | PASS | 22 | 0 | 0 |
| mt_document | PASS | 22 | 0 | 0 |

## Injected-error detection (target_flawed)

| error | doc-level? | transtest | LaBSE seg-QE (<0.80) | LLM seg-QE GEMBA (<75) |
|---|---|---|---|---|
| E1 | no | ✅ weight-limit | — | ✅ |
| E2 | no | ✅ kidney-and-age, kidney-and-age-neg | — | ✅ |
| E3 | yes | ✅ qa-interaction, warfarin-direction, warfarin-direction-neg | — | ✅ |
| E4 | no | —  | — | ✅ |
| E5 | yes | ✅ glossary, tablet-consistency | — | — |
| E6 | yes | ✅ coverage | ✅ | ✅ |
| E7 | no | ✅ numbers, qa-liver-max | ✅ | ✅ |
| E8 | yes | ✅ tu-markers, usted-register | — | — |
| E9 | no | ✅ overdose-even-if-well | — | ✅ |
| **total** | | **8/9** | **2/9** | **7/9** |

## False positives on the good translation

```
{
  "transtest_failed_tests_on_good": [],
  "labse_flags_on_good": 1,
  "gemba_flags_on_good": 2,
  "n_segments": 31
}
```

Models: endpoint=https://openrouter.ai/api/v1  judge=anthropic/claude-sonnet-5.5  mt=openai/gpt-5.4-mini

Mean segment-QE scores (good vs flawed): {"good": {"labse": 0.9293548387096773, "gemba": 93.48387096774194}, "flawed": {"labse": 0.9103548387096773, "gemba": 80.7741935483871}}