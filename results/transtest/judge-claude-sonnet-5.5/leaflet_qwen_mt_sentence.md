# transtest report — Feverol leaflet — EN→ES document tests

- target: `results/transtest/mt/leaflet_mt_sentence__local-qwen3-4b.es.md`  
- mode: target
- **verdict: WARN** — 18 passed, 4 failed (0 critical), 0 errors, 0 skipped; penalty 16

| | id | type | severity | message |
|---|---|---|---|---|
| ✅ | numbers | numbers | critical | 22 numbers preserved |
| ✅ | placeholders | placeholders | minor | placeholders/tags intact |
| ✅ | dnt | dnt | minor | 1 DNT terms preserved |
| ❌ | glossary | glossary | major | forbidden 'tabletas' used 1× (approved: ['comprimido', 'comprimidos']); forbidden 'pastillas' used 1× (approved: ['comprimido', 'comprimidos']); 'package leaflet' occurs 1× in source but approved ['prospecto'] never used |
| ❌ | tablet-consistency | term_consistency | major | 'tablet(s)' rendered inconsistently: {'comprimido': 3, 'tableta': 1, 'pastilla': 1} |
| ✅ | coverage | coverage | major | all 31 source sentences aligned (min sim 0.87) |
| ❌ | usted-register | register | major | 6 sentence(s) break register: formal address to the reader with 'usted' forms (e.g. 'tome', 'consulte', 'su médico') |
| ❌ | tu-markers | forbidden_patterns | minor | 1 forbidden pattern hit(s) |
| ✅ | weight-limit | assert | critical | [MUST state] Adolescents can use the medicine only if they weigh more than 50 kg. → judge: supported (The document says it is used in adults and adolescents weighing over 50 kg, which implies that adolescents are included only when they weigh over 50 kg; the claim's 'only' is a reasonable reading of this restriction, though the document does not explicitly say lighter adolescents cannot use it.) |
| ✅ | kidney-and-age | assert | major | [MUST state] The advice to talk to a doctor first applies to people who have kidney problems AND are over 65 at the same time. → judge: supported (The sentence joins the two conditions with 'y' (and), so the advice to talk to a doctor applies when both kidney problems and age over 65 are present, matching the claim.) |
| ✅ | kidney-and-age-neg | assert | major | [must NOT state] Anyone over 65 should talk to their doctor before taking it, even without kidney problems. → judge: not_stated (The document's advice applies only to people who have both kidney problems and are over 65, so it does not say that everyone over 65 without kidney problems should talk to their doctor; the claim extends the condition beyond what is stated.) |
| ✅ | warfarin-direction | assert | critical | [MUST state] Feverol (the medicine described) can increase the effect of warfarin. → judge: supported (The sentence follows the warfarin sentence about Feverol and says it (Feverol) can increase warfarin's effect when taken regularly for over a week, which matches the claim, though with a condition.) |
| ✅ | warfarin-direction-neg | assert | critical | [must NOT state] Warfarin can increase the effect of Feverol. → judge: contradicted (The document says Feverol (paracetamol) may increase warfarin's effect, which is the reverse of the claim that warfarin increases Feverol's effect.) |
| ✅ | alcohol-neg | assert | major | [must NOT state] Drinking moderate amounts of alcohol is acceptable while taking the medicine. → judge: contradicted (The document tells users to avoid alcohol entirely with no exception for moderate amounts, which is incompatible with the claim that moderate drinking is acceptable.) |
| ✅ | overdose-even-if-well | assert | critical | [MUST state] After taking too much, you must get medical help immediately even if you feel well. → judge: supported (The section is titled for taking more Feverol than should be taken, and the sentence instructs immediate medical contact even when feeling well, matching the claim.) |
| ✅ | overdose-neg | assert | critical | [must NOT state] After taking too much, you only need medical help if you feel unwell. → judge: contradicted (The document says to seek medical help immediately even when feeling well, which is incompatible with the claim that help is only needed if you feel unwell.) |
| ✅ | children-under-12 | assert | critical | [MUST state] The medicine must not be given to children under 12 years old. → judge: supported (The sentence prohibits giving the medicine to children under 12, which is exactly what the claim states.) |
| ✅ | pregnancy | assert | major | [MUST state] It may be used in pregnancy if clinically needed, at the lowest dose for the shortest time. → judge: supported (The sentence says exactly what the claim says: use in pregnancy if clinically needed, at the lowest dose for the shortest time.) |
| ✅ | qa-liver-max | qa | critical | Q: What is the maximum daily dose for someone with liver problems? / expected: 6 tablets (3,000 mg) per day / got: 6 tablets (3,000 mg) per day |
| ✅ | qa-gap | qa | major | Q: What is the minimum time to leave between two doses? / expected: At least 4 hours / got: At least 4 hours between doses. |
| ✅ | qa-interaction | qa | critical | Q: Which medicine's effect is increased in the warfarin interaction, and what causes the increase? / expected: The effect of warfarin is increased, caused by Feverol/paracetamol taken regularly for more than a week / got: The effect of warfarin is increased (the text says it 'may' increase), and this happens when Feverol (paracetamol) is taken regularly for more than a week. |
| ✅ | qa-fever-days | qa | major | Q: After how many days of fever should the patient talk to a doctor? / expected: If the fever lasts more than 3 days / got: If the fever lasts more than 3 days. |

## Evidence for failures

**glossary**
> Tabletas de Feverol de 500 mg recubiertas con película
> Trague las pastillas enteras con un vaso de agua.

**tablet-consistency**
> La dosis recomendada es de 1 o 2 comprimidos cada 4 a 6 horas según sea necesario.
> Tabletas de Feverol de 500 mg recubiertas con película
> Trague las pastillas enteras con un vaso de agua.

**usted-register**
> Lee atentamente este folleto antes de comenzar a tomar esta medicación.
> Mantén este folleto.
> Puede que necesites leerlo de nuevo.
> Lo que debes saber antes de tomar Feverol
> Si tu fiebre dura más de 3 días o tu dolor dura más de 5 días, habla con tu médico.
> Mantén este medicamento fuera del alcance y visión de los niños.

**tu-markers**
> /\btus?\b/ in: Si tu fiebre dura más de 3 días o tu dolor dura más de 5 días, habla con tu médico.
