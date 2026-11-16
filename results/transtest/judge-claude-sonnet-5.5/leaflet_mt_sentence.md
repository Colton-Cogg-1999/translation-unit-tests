# transtest report — Feverol leaflet — EN→ES document tests

- target: `results/transtest/mt/leaflet_mt_sentence__gpt-5.4-mini.es.md`  
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
| ✅ | weight-limit | assert | critical | [MUST state] Adolescents can use the medicine only if they weigh more than 50 kg. → judge: supported (The document states the indication for adolescents who weigh more than 50 kg, which implies use in that group, but it does not explicitly say adolescents may use it ONLY if they weigh over 50 kg; the other sentence only says not to give to children under 12, so exclusivity is an inference from the indication wording and is reasonably entailed.) |
| ✅ | kidney-and-age | assert | major | [MUST state] The advice to talk to a doctor first applies to people who have kidney problems AND are over 65 at the same time. → judge: supported (The sentence joins the two conditions with 'y' (and), so the advice applies to people with both kidney problems and age over 65, which matches the claim.) |
| ✅ | kidney-and-age-neg | assert | major | [must NOT state] Anyone over 65 should talk to their doctor before taking it, even without kidney problems. → judge: not_stated (The document's advice applies only to people who have both kidney problems and are over 65, so it does not say that anyone over 65 without kidney problems should talk to their doctor; the claim extends beyond the condition stated.) |
| ✅ | warfarin-direction | assert | critical | [MUST state] Feverol (the medicine described) can increase the effect of warfarin. → judge: supported (The sentence, following the one about warfarin and Feverol, says it (Feverol) can increase warfarin's effect when taken regularly for over a week, which matches the claim (the condition of regular use is an added detail but the claim is entailed).) |
| ✅ | warfarin-direction-neg | assert | critical | [must NOT state] Warfarin can increase the effect of Feverol. → judge: contradicted (The document says Feverol may increase warfarin's effect, whereas the claim reverses the direction (warfarin increasing Feverol's effect), which is not stated and is the opposite of what the document says.) |
| ✅ | alcohol-neg | assert | major | [must NOT state] Drinking moderate amounts of alcohol is acceptable while taking the medicine. → judge: contradicted (The document advises avoiding alcohol entirely during treatment, with no exception for moderate amounts, which is incompatible with saying moderate drinking is acceptable.) |
| ✅ | overdose-even-if-well | assert | critical | [MUST state] After taking too much, you must get medical help immediately even if you feel well. → judge: supported (The section is about taking more Feverol than should be taken, and it says to contact a doctor or go immediately to hospital even if feeling well, which matches the claim of getting medical help immediately even if well.) |
| ✅ | overdose-neg | assert | critical | [must NOT state] After taking too much, you only need medical help if you feel unwell. → judge: contradicted (The document says to seek medical help even if you feel well, which is incompatible with the claim that help is needed only if you feel unwell.) |
| ✅ | children-under-12 | assert | critical | [MUST state] The medicine must not be given to children under 12 years old. → judge: supported (The sentence prohibits giving Feverol to children under 12, which is exactly what the claim states.) |
| ✅ | pregnancy | assert | major | [MUST state] It may be used in pregnancy if clinically needed, at the lowest dose for the shortest time. → judge: supported (The sentence says the same as the claim: use in pregnancy if clinically needed, at the lowest dose for the shortest time.) |
| ✅ | qa-liver-max | qa | critical | Q: What is the maximum daily dose for someone with liver problems? / expected: 6 tablets (3,000 mg) per day / got: 6 tablets (3,000 mg) per day |
| ✅ | qa-gap | qa | major | Q: What is the minimum time to leave between two doses? / expected: At least 4 hours / got: At least 4 hours between doses. |
| ✅ | qa-interaction | qa | critical | Q: Which medicine's effect is increased in the warfarin interaction, and what causes the increase? / expected: The effect of warfarin is increased, caused by Feverol/paracetamol taken regularly for more than a week / got: The effect of warfarin is increased; the document says this happens when Feverol (paracetamol) is taken regularly for more than a week (the subject of "Puede aumentar" is implied, not stated explicitly). |
| ✅ | qa-fever-days | qa | major | Q: After how many days of fever should the patient talk to a doctor? / expected: If the fever lasts more than 3 days / got: If the fever lasts more than 3 days (i.e., after 3 days), consult a doctor. |