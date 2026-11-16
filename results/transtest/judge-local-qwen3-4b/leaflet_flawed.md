# transtest report — Feverol leaflet — EN→ES document tests

- target: `transtest/examples/leaflet/target_flawed.es.md`  
- mode: target
- **verdict: FAIL** — 9 passed, 13 failed (7 critical), 0 errors, 0 skipped; penalty 201

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
| ❌ | weight-limit | assert | critical | [MUST state] Adolescents can use the medicine only if they weigh more than 50 kg. → judge: contradicted (The evidence states that adolescents can use the medicine if they weigh less than 50 kg, not more than 50 kg. Therefore, it directly contradicts the claim that adolescents can use the medicine only if they weigh more than 50 kg.) |
| ❌ | kidney-and-age | assert | major | [MUST state] The advice to talk to a doctor first applies to people who have kidney problems AND are over 65 at the same time. → judge: contradicted (The evidence states that consultation with a doctor is required if a person has kidney problems OR is over 65 years old. The claim specifies that the advice applies only when both conditions are true (kidney problems AND over 65). The document does not state that both conditions must be present simultaneously; it uses 'or', meaning either condition alone triggers the need to consult a doctor. Therefore, the rendering does not support the specific claim that the advice applies only when both conditions are met at the same time.) |
| ✅ | kidney-and-age-neg | assert | major | [must NOT state] Anyone over 65 should talk to their doctor before taking it, even without kidney problems. → judge: not_stated (The evidence states that consultation with a doctor is required if someone has kidney problems or is over 65, but it does not state that anyone over 65 should consult a doctor regardless of kidney problems. The claim generalizes to all people over 65 without kidney issues, which is not mentioned or implied in the document.) |
| ✅ | warfarin-direction | assert | critical | [MUST state] Feverol (the medicine described) can increase the effect of warfarin. → judge: supported (The evidence states that warfarin can increase the effect of this medication (Feverol) if taken regularly for more than one week. This directly matches the claim that 'Feverol can increase the effect of warfarin', though the condition is specified (regular use for more than one week). The claim does not specify conditions, but the document explicitly states that warfarin increases the effect of Feverol under those conditions, which is a literal statement of the claim's core idea.) |
| ❌ | warfarin-direction-neg | assert | critical | [must NOT state] Warfarin can increase the effect of Feverol. → judge: supported (The evidence states that warfarin can increase the effect of Feverol if taken regularly for more than one week, which directly matches the claim that 'Warfarin can increase the effect of Feverol'. The condition (regular use for more than one week) is specified, but the core claim — that warfarin increases the effect — is explicitly stated.) |
| ✅ | alcohol-neg | assert | major | [must NOT state] Drinking moderate amounts of alcohol is acceptable while taking the medicine. → judge: contradicted (The evidence states that excessive alcohol consumption should be avoided while taking Feverol, but it does not mention or support drinking moderate amounts of alcohol. The claim about moderate alcohol consumption being acceptable is not stated or implied; instead, the document only warns against excessive drinking. Therefore, the claim is not supported by the text.) |
| ❌ | overdose-even-if-well | assert | critical | [MUST state] After taking too much, you must get medical help immediately even if you feel well. → judge: not_stated (The evidence states that medical help is required if the person is not feeling well after taking too much Feverol, but it does not state that help is required even if they feel well. The claim specifies a situation where the person feels well, which is not mentioned or implied in the document.) |
| ❌ | overdose-neg | assert | critical | [must NOT state] After taking too much, you only need medical help if you feel unwell. → judge: supported (The evidence states that medical help is required if the person is not feeling well, which directly matches the claim that 'you only need medical help if you feel unwell'. The claim implies that medical help is only needed when unwell, and the document says exactly that: seek help if not feeling well. This is consistent with the claim in terms of condition and action.) |
| ✅ | children-under-12 | assert | critical | [MUST state] The medicine must not be given to children under 12 years old. → judge: supported (The evidence states that Feverol must not be administered to children under 12 years old, which directly matches the claim.) |
| ✅ | pregnancy | assert | major | [MUST state] It may be used in pregnancy if clinically needed, at the lowest dose for the shortest time. → judge: supported (The evidence states that Feverol can be used during pregnancy if clinically necessary, and that the lowest possible dose should be used for the shortest possible time. This matches exactly with the claim that 'it may be used in pregnancy if clinically needed, at the lowest dose for the shortest time.' The wording, including the condition 'if clinically necessary,' the use of 'lowest dose,' and 'shortest time,' is preserved and directly aligns with the claim.) |
| ❌ | qa-liver-max | qa | critical | Q: What is the maximum daily dose for someone with liver problems? / expected: 6 tablets (3,000 mg) per day / got: 8 comprimidos (4.000 mg) |
| ✅ | qa-gap | qa | major | Q: What is the minimum time to leave between two doses? / expected: At least 4 hours / got: 4 to 6 hours |
| ❌ | qa-interaction | qa | critical | Q: Which medicine's effect is increased in the warfarin interaction, and what causes the increase? / expected: The effect of warfarin is increased, caused by Feverol/paracetamol taken regularly for more than a week / got: The effect of Feverol is increased, caused by warfarina taking it regularly for more than a week. |
| ✅ | qa-fever-days | qa | major | Q: After how many days of fever should the patient talk to a doctor? / expected: If the fever lasts more than 3 days / got: 3 days |

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

**warfarin-direction-neg**
> La warfarina puede aumentar el efecto de este medicamento si se toma de forma regular durante más de una semana.

**overdose-even-if-well**
> Consulte inmediatamente a su médico o acuda al hospital más cercano si no se encuentra bien. Esto se debe a que una cantidad excesiva de paracetamol puede causar daños graves y tardíos en el hígado.

**overdose-neg**
> Consulte inmediatamente a su médico o acuda al hospital más cercano si no se encuentra bien.

**qa-liver-max**
> Si tiene problemas de hígado, la dosis máxima diaria es de 8 comprimidos (4.000 mg).

**qa-interaction**
> Si está tomando warfarina, es posible que su médico tenga que controlar su sangre con más frecuencia. La warfarina puede aumentar el efecto de este medicamento si se toma de forma regular durante más de una semana.
