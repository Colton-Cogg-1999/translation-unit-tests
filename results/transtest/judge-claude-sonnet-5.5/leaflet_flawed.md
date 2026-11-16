# transtest report — Feverol leaflet — EN→ES document tests

- target: `transtest/examples/leaflet/target_flawed.es.md`  
- mode: target
- **verdict: FAIL** — 8 passed, 14 failed (7 critical), 0 errors, 0 skipped; penalty 206

| | id | type | severity | message |
|---|---|---|---|---|
| ❌ | numbers | numbers | critical | missing in target: 4×1, 6×1, 3000×1; unexpected in target: 8×1, 4000×1 |
| ✅ | placeholders | placeholders | minor | placeholders/tags intact |
| ✅ | dnt | dnt | minor | 1 DNT terms preserved |
| ❌ | glossary | glossary | major | forbidden 'tabletas' used 2× (approved: ['comprimido', 'comprimidos']); forbidden 'pastillas' used 1× (approved: ['comprimido', 'comprimidos']) |
| ❌ | tablet-consistency | term_consistency | major | 'tablet(s)' rendered inconsistently: {'comprimido': 2, 'tableta': 2, 'pastilla': 1} |
| ❌ | coverage | coverage | major | 1 source sentence(s) without a counterpart (possible omission) |
| ❌ | usted-register | register | major | 2 sentence(s) break register: formal address to the reader with 'usted' forms (e.g. 'tome', 'consulte', 'su médico') |
| ❌ | tu-markers | forbidden_patterns | minor | 3 forbidden pattern hit(s) |
| ❌ | weight-limit | assert | critical | [MUST state] Adolescents can use the medicine only if they weigh more than 50 kg. → judge: contradicted (The document says adolescents who weigh less than 50 kg, whereas the claim says adolescents can use it only if they weigh more than 50 kg, which is the opposite weight condition.) |
| ❌ | kidney-and-age | assert | major | [MUST state] The advice to talk to a doctor first applies to people who have kidney problems AND are over 65 at the same time. → judge: contradicted (The document uses 'or' (either condition triggers the advice), whereas the claim requires both conditions at once ('AND'), which is incompatible.) |
| ❌ | kidney-and-age-neg | assert | major | [must NOT state] Anyone over 65 should talk to their doctor before taking it, even without kidney problems. → judge: supported (The 'or' condition means being over 65 alone is enough to trigger consulting the doctor, regardless of kidney problems, which matches the claim.) |
| ❌ | warfarin-direction | assert | critical | [MUST state] Feverol (the medicine described) can increase the effect of warfarin. → judge: not_stated (The document says warfarin may increase Feverol's effect, which is the reverse direction of the claim that Feverol increases warfarin's effect; the document only says that the doctor may need to monitor blood more often, without stating Feverol increases warfarin's effect.) |
| ❌ | warfarin-direction-neg | assert | critical | [must NOT state] Warfarin can increase the effect of Feverol. → judge: supported (The sentence says warfarin can increase the effect of this medicine (Feverol), conditional on regular use for over a week; the claim states the same without the condition, which is a general statement the document supports.) |
| ✅ | alcohol-neg | assert | major | [must NOT state] Drinking moderate amounts of alcohol is acceptable while taking the medicine. → judge: not_stated (The document only warns against excessive alcohol and says nothing explicit about moderate drinking being acceptable or not, so the claim is neither stated nor contradicted (it is merely a possible inference).) |
| ❌ | overdose-even-if-well | assert | critical | [MUST state] After taking too much, you must get medical help immediately even if you feel well. → judge: not_stated (The document makes seeking immediate help conditional on not feeling well, while the claim says to get help even if you feel well; the following sentence about delayed liver damage does not state that help is needed when feeling well, so the document does not say this and the condition differs.) |
| ✅ | overdose-neg | assert | critical | [must NOT state] After taking too much, you only need medical help if you feel unwell. → judge: contradicted (The sentence says to seek medical help immediately if you feel unwell after taking more than you should, and the next sentence says excess paracetamol can cause serious, delayed liver damage; it does not say help is needed ONLY if unwell, but the conditional 'if you don't feel well' matches the claim's condition, though the 'only' is not stated and the delayed-damage explanation suggests otherwise.) |
| ✅ | children-under-12 | assert | critical | [MUST state] The medicine must not be given to children under 12 years old. → judge: supported (The sentence directly prohibits giving the medicine to children younger than 12, which is exactly what the claim says, even though other parts of the document are inconsistent (e.g., adolescents under 50 kg).) |
| ✅ | pregnancy | assert | major | [MUST state] It may be used in pregnancy if clinically needed, at the lowest dose for the shortest time. → judge: supported (The sentence states the same conditions as the claim: use in pregnancy if clinically needed, at the lowest possible dose for the shortest possible time.) |
| ❌ | qa-liver-max | qa | critical | Q: What is the maximum daily dose for someone with liver problems? / expected: 6 tablets (3,000 mg) per day / got: 8 tablets (4,000 mg) per day |
| ✅ | qa-gap | qa | major | Q: What is the minimum time to leave between two doses? / expected: At least 4 hours / got: 4 hours (doses are recommended every 4 to 6 hours) |
| ❌ | qa-interaction | qa | critical | Q: Which medicine's effect is increased in the warfarin interaction, and what causes the increase? / expected: The effect of warfarin is increased, caused by Feverol/paracetamol taken regularly for more than a week / got: The effect of this medicine (Feverol, paracetamol) is increased, and the cause is warfarin, when taken regularly for more than a week. |
| ✅ | qa-fever-days | qa | major | Q: After how many days of fever should the patient talk to a doctor? / expected: If the fever lasts more than 3 days / got: If the fever lasts more than 3 days (i.e., after 3 days). |

## Evidence for failures

**glossary**
> La dosis recomendada es de 1 o 2 tabletas cada 4 a 6 horas, según sea necesario.
> No tome más de 8 tabletas (4.000 mg) en 24 horas.
> Trágate las pastillas enteras con un vaso de agua.

**tablet-consistency**
> Feverol 500 mg comprimidos recubiertos con película
> La dosis recomendada es de 1 o 2 tabletas cada 4 a 6 horas, según sea necesario.
> Trágate las pastillas enteras con un vaso de agua.

**coverage**
> [omitted? sim=0.62] Leave at least 4 hours between doses.

**usted-register**
> Trágate las pastillas enteras con un vaso de agua.
> Si la fiebre te dura más de 3 días o el dolor más de 5 días, habla con tu médico.

**tu-markers**
> /\b(?!\w*mente\b)\w*[áéíó]\w*te\b/ in: Trágate las pastillas enteras con un vaso de agua.
> /\btus?\b/ in: Si la fiebre te dura más de 3 días o el dolor más de 5 días, habla con tu médico.
> /\bte\b/ in: Si la fiebre te dura más de 3 días o el dolor más de 5 días, habla con tu médico.

**weight-limit**
> Se utiliza para tratar el dolor leve o moderado y la fiebre en adultos y adolescentes que pesen menos de 50 kg.

**kidney-and-age**
> Consulte a su médico antes de tomar Feverol si tiene problemas de riñón o es mayor de 65 años.

**kidney-and-age-neg**
> Consulte a su médico antes de tomar Feverol si tiene problemas de riñón o es mayor de 65 años.

**warfarin-direction**
> La warfarina puede aumentar el efecto de este medicamento si se toma de forma regular durante más de una semana.

**warfarin-direction-neg**
> La warfarina puede aumentar el efecto de este medicamento si se toma de forma regular durante más de una semana.

**overdose-even-if-well**
> Consulte inmediatamente a su médico o acuda al hospital más cercano si no se encuentra bien.

**qa-liver-max**
> Si tiene problemas de hígado, la dosis máxima diaria es de 8 comprimidos (4.000 mg).

**qa-interaction**
> La warfarina puede aumentar el efecto de este medicamento si se toma de forma regular durante más de una semana.
