# transtest report — Feverol leaflet — EN→ES document tests

- target: `results/transtest/mt/leaflet_mt_document__gpt-5.4-mini.es.md`  
- mode: target
- **verdict: PASS** — 22 passed, 0 failed (0 critical), 0 errors, 0 skipped; penalty 0

| | id | type | severity | message |
|---|---|---|---|---|
| ✅ | numbers | numbers | critical | 22 numbers preserved |
| ✅ | placeholders | placeholders | minor | placeholders/tags intact |
| ✅ | dnt | dnt | minor | 1 DNT terms preserved |
| ✅ | glossary | glossary | major | glossary respected |
| ✅ | tablet-consistency | term_consistency | major | terms rendered consistently |
| ✅ | coverage | coverage | major | all 31 source sentences aligned (min sim 0.79) |
| ✅ | usted-register | register | major | register consistent (formal address to the reader with 'usted' forms (e.g. 'tome', 'consulte', 'su médico')) |
| ✅ | tu-markers | forbidden_patterns | minor | no forbidden patterns |
| ✅ | weight-limit | assert | critical | [MUST state] Adolescents can use the medicine only if they weigh more than 50 kg. → judge: supported (The document states the indication for adolescents who weigh more than 50 kg, which implies adolescents are covered only under that weight condition, matching the claim; no other text allows lighter adolescents (only a separate ban for children under 12).) |
| ✅ | kidney-and-age | assert | major | [MUST state] The advice to talk to a doctor first applies to people who have kidney problems AND are over 65 at the same time. → judge: supported (The sentence links the two conditions with 'y' (and), so the advice to consult a doctor first applies when both kidney problems and age over 65 are present, which matches the claim.) |
| ✅ | kidney-and-age-neg | assert | major | [must NOT state] Anyone over 65 should talk to their doctor before taking it, even without kidney problems. → judge: not_stated (The document requires both kidney problems and age over 65 for the advice to consult a doctor, so it does not say that anyone over 65 without kidney problems should consult; the claim extends beyond the stated condition and the document does not address that case directly.) |
| ✅ | warfarin-direction | assert | critical | [MUST state] Feverol (the medicine described) can increase the effect of warfarin. → judge: supported (The sentence follows the warfarin sentence about Feverol (paracetamol) and says it can increase warfarin's effect with regular use over a week, which matches the claim (with the added condition of regular use for more than a week).) |
| ✅ | warfarin-direction-neg | assert | critical | [must NOT state] Warfarin can increase the effect of Feverol. → judge: not_stated (The document says Feverol may increase warfarin's effect, which is the reverse direction of the claim that warfarin increases Feverol's effect; the document does not state the claimed direction.) |
| ✅ | alcohol-neg | assert | major | [must NOT state] Drinking moderate amounts of alcohol is acceptable while taking the medicine. → judge: contradicted (The document tells the reader to avoid alcohol with no exception for moderate amounts, which is incompatible with the claim that moderate drinking is acceptable.) |
| ✅ | overdose-even-if-well | assert | critical | [MUST state] After taking too much, you must get medical help immediately even if you feel well. → judge: supported (The section is headed 'If you take more Feverol than you should' and instructs contacting a doctor or going immediately to hospital even if feeling well, which matches the claim of getting medical help immediately even if well.) |
| ✅ | overdose-neg | assert | critical | [must NOT state] After taking too much, you only need medical help if you feel unwell. → judge: contradicted (The document says to seek medical help even when feeling well, which is incompatible with the claim that help is needed only if you feel unwell.) |
| ✅ | children-under-12 | assert | critical | [MUST state] The medicine must not be given to children under 12 years old. → judge: supported (The sentence prohibits giving the medicine to children under 12, which is exactly what the claim states.) |
| ✅ | pregnancy | assert | major | [MUST state] It may be used in pregnancy if clinically needed, at the lowest dose for the shortest time. → judge: supported (The sentence says the same as the claim: use in pregnancy if clinically needed, at the lowest dose for the shortest time.) |
| ✅ | qa-liver-max | qa | critical | Q: What is the maximum daily dose for someone with liver problems? / expected: 6 tablets (3,000 mg) per day / got: 6 tablets (3,000 mg) per day |
| ✅ | qa-gap | qa | major | Q: What is the minimum time to leave between two doses? / expected: At least 4 hours / got: At least 4 hours. |
| ✅ | qa-interaction | qa | critical | Q: Which medicine's effect is increased in the warfarin interaction, and what causes the increase? / expected: The effect of warfarin is increased, caused by Feverol/paracetamol taken regularly for more than a week / got: The effect of warfarin is increased (not Feverol's); the document says this can happen when Feverol (paracetamol) is taken regularly for more than a week. |
| ✅ | qa-fever-days | qa | major | Q: After how many days of fever should the patient talk to a doctor? / expected: If the fever lasts more than 3 days / got: If the fever lasts more than 3 days (i.e., after 3 days), the patient should consult a doctor. |