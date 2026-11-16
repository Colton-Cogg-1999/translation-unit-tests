# Failures that segment-level QE missed (sample)

### context_disambiguation-07 · llama-4-scout__segment · context_disambiguation

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Take one tablet twice daily with food. | Tomar una tableta dos veces al día con alimentos. | ok |
| 2 | Do not crush the tablet before swallowing it. | No machaque la tableta antes de tragársela. | ok |

**Failed assertion** (contains, segment 2): ['comprimido', 'pastilla']  
→ none of ['comprimido', 'pastilla'] found

### context_disambiguation-07 · llama-4-scout__segment · context_disambiguation

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Take one tablet twice daily with food. | Tomar una tableta dos veces al día con alimentos. | ok |
| 2 | Do not crush the tablet before swallowing it. | No machaque la tableta antes de tragársela. | ok |

**Failed assertion** (not_contains, segment 2): ['tableta']  
→ found ['tableta']

### context_disambiguation-07 · llama-4-scout__document · context_disambiguation

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Take one tablet twice daily with food. | Tomar una tableta dos veces al día con alimentos. | ok |
| 2 | Do not crush the tablet before swallowing it. | No triturar la tableta antes de tragarse. | ok |

**Failed assertion** (contains, segment 2): ['comprimido', 'pastilla']  
→ none of ['comprimido', 'pastilla'] found

### context_disambiguation-07 · llama-4-scout__document · context_disambiguation

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Take one tablet twice daily with food. | Tomar una tableta dos veces al día con alimentos. | ok |
| 2 | Do not crush the tablet before swallowing it. | No triturar la tableta antes de tragarse. | ok |

**Failed assertion** (not_contains, segment 2): ['tableta']  
→ found ['tableta']

### context_disambiguation-04 · gpt-5.4-nano__segment · context_disambiguation

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Join the legendary vinyl collectors' club. | Únete al legendario club de coleccionistas de vinilo. | ok |
| 2 | Every record in our catalog is pressed on 180-gram vinyl. | Cada registro de nuestro catálogo se edita en vinilo de 180 gramos. | ok |

**Failed assertion** (contains, segment 2): ['disco', 'discos', 'álbum', 'álbumes', 'LP']  
→ none of ['disco', 'discos', 'álbum', 'álbumes', 'LP'] found

### context_disambiguation-04 · gpt-5.4-nano__segment · context_disambiguation

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Join the legendary vinyl collectors' club. | Únete al legendario club de coleccionistas de vinilo. | ok |
| 2 | Every record in our catalog is pressed on 180-gram vinyl. | Cada registro de nuestro catálogo se edita en vinilo de 180 gramos. | ok |

**Failed assertion** (not_contains, segment 2): ['registro', 'récord', 'marca']  
→ found ['registro']

### coreference_agreement-01 · llama-4-scout__segment · coreference_agreement

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Open the Settings app. | Abre la aplicación Configuración. | ok |
| 2 | Then tap the icon to launch it. | Luego pulsa el icono para iniciarlo. | ok |

**Failed assertion** (contains, segment 2): ['iniciarla', 'abrirla', 'lanzarla', 'ejecutarla', 'iniciarla.', 'abrirla.']  
→ none of ['iniciarla', 'abrirla', 'lanzarla', 'ejecutarla', 'iniciarla.', 'abrirla.'] found

### coreference_agreement-01 · llama-4-scout__segment · coreference_agreement

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Open the Settings app. | Abre la aplicación Configuración. | ok |
| 2 | Then tap the icon to launch it. | Luego pulsa el icono para iniciarlo. | ok |

**Failed assertion** (not_contains, segment 2): ['iniciarlo', 'abrirlo', 'lanzarlo', 'ejecutarlo']  
→ found ['iniciarlo']

### coreference_agreement-04 · llama-4-scout__segment · coreference_agreement

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Our new sneakers are lightweight and breathable. | Nuestros nuevos zapatillas son ligeras y transpirables. | ok |
| 2 | Order them today, and they arrive tomorrow. | ¡Pídelos hoy y llegan mañana! | ok |

**Failed assertion** (contains, segment 2): ['pídelas', 'pídalas', 'encárgalas', 'cómpralas', 'solicítalas', 'pedirlas', 'pídelas hoy', 'haz tu pedido']  
→ none of ['pídelas', 'pídalas', 'encárgalas', 'cómpralas', 'solicítalas', 'pedirlas', 'pídelas hoy', 'haz tu pedido'] found

### coreference_agreement-04 · llama-4-scout__segment · coreference_agreement

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Our new sneakers are lightweight and breathable. | Nuestros nuevos zapatillas son ligeras y transpirables. | ok |
| 2 | Order them today, and they arrive tomorrow. | ¡Pídelos hoy y llegan mañana! | ok |

**Failed assertion** (not_contains, segment 2): ['pídelos', 'pídalos', 'cómpralos', 'encárgalos', 'solicítalos']  
→ found ['pídelos']

### coreference_agreement-04 · llama-4-scout__document · coreference_agreement

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Our new sneakers are lightweight and breathable. | Nuestros nuevos sneakers son ligeros y transpirables. | ok |
| 2 | Order them today, and they arrive tomorrow. | Ordena los tuyos hoy mismo y llegan mañana. | ok |

**Failed assertion** (contains, segment 2): ['pídelas', 'pídalas', 'encárgalas', 'cómpralas', 'solicítalas', 'pedirlas', 'pídelas hoy', 'haz tu pedido']  
→ none of ['pídelas', 'pídalas', 'encárgalas', 'cómpralas', 'solicítalas', 'pedirlas', 'pídelas hoy', 'haz tu pedido'] found

### coreference_agreement-01 · gpt-5.4-nano__segment · coreference_agreement

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Open the Settings app. | Abre la aplicación Ajustes. | ok |
| 2 | Then tap the icon to launch it. | A continuación, toca el icono para iniciarlo. | ok |

**Failed assertion** (contains, segment 2): ['iniciarla', 'abrirla', 'lanzarla', 'ejecutarla', 'iniciarla.', 'abrirla.']  
→ none of ['iniciarla', 'abrirla', 'lanzarla', 'ejecutarla', 'iniciarla.', 'abrirla.'] found

### coreference_agreement-01 · gpt-5.4-nano__segment · coreference_agreement

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Open the Settings app. | Abre la aplicación Ajustes. | ok |
| 2 | Then tap the icon to launch it. | A continuación, toca el icono para iniciarlo. | ok |

**Failed assertion** (not_contains, segment 2): ['iniciarlo', 'abrirlo', 'lanzarlo', 'ejecutarlo']  
→ found ['iniciarlo']

### coreference_agreement-03 · gpt-5.4-nano__segment · coreference_agreement

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Meet Clara, our new brand ambassador. | Conoce a Clara, nuestra nueva embajadora de marca. | ok |
| 2 | She is known for her energy and she is thrilled to join us. | Es conocida por su energía y le hace mucha ilusión unirse a nosotros. | ok |

**Failed assertion** (contains, segment 2): ['encantada', 'emocionada', 'entusiasmada', 'ilusionada', 'feliz']  
→ none of ['encantada', 'emocionada', 'entusiasmada', 'ilusionada', 'feliz'] found

### coreference_agreement-04 · gpt-5.4-nano__segment · coreference_agreement

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Our new sneakers are lightweight and breathable. | Nuestras nuevas zapatillas son ligeras y transpirables. | ok |
| 2 | Order them today, and they arrive tomorrow. | Pídelo hoy y te llegará mañana. | ok |

**Failed assertion** (contains, segment 2): ['pídelas', 'pídalas', 'encárgalas', 'cómpralas', 'solicítalas', 'pedirlas', 'pídelas hoy', 'haz tu pedido']  
→ none of ['pídelas', 'pídalas', 'encárgalas', 'cómpralas', 'solicítalas', 'pedirlas', 'pídelas hoy', 'haz tu pedido'] found

### coreference_agreement-08 · gpt-5.4-nano__segment · coreference_agreement

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | The nurse will place the sensor on your arm. | La enfermera colocará el sensor en su brazo. | ok |
| 2 | She will then check that it is secure. | A continuación, comprobará que esté bien asegurado. | ok |

**Failed assertion** (contains, segment 2): ['seguro', 'bien colocado', 'fijo', 'sujeto', 'firme']  
→ none of ['seguro', 'bien colocado', 'fijo', 'sujeto', 'firme'] found

### coreference_agreement-08 · gpt-5.4-nano__segment · coreference_agreement

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | The nurse will place the sensor on your arm. | La enfermera colocará el sensor en su brazo. | ok |
| 2 | She will then check that it is secure. | A continuación, comprobará que esté bien asegurado. | ok |

**Failed assertion** (not_contains, segment 2): ['segura', 'colocada', 'fija', 'sujeta']  
→ found ['segura']

### coreference_agreement-02 · gpt-5.4-nano__document · coreference_agreement

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Select the file you want to share. | 1. Selecciona el archivo que quieres compartir. | ok |
| 2 | Once it is uploaded, it will appear in your library. | 2. Cuando se cargue, aparecerá en tu biblioteca. | ok |

**Failed assertion** (contains, segment 2): ['subido', 'cargado', 'guardado']  
→ none of ['subido', 'cargado', 'guardado'] found

### coreference_agreement-04 · gpt-5.4-mini__segment · coreference_agreement

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Our new sneakers are lightweight and breathable. | Nuestras nuevas zapatillas son ligeras y transpirables. | ok |
| 2 | Order them today, and they arrive tomorrow. | Pídelos hoy y te llegarán mañana. | ok |

**Failed assertion** (contains, segment 2): ['pídelas', 'pídalas', 'encárgalas', 'cómpralas', 'solicítalas', 'pedirlas', 'pídelas hoy', 'haz tu pedido']  
→ none of ['pídelas', 'pídalas', 'encárgalas', 'cómpralas', 'solicítalas', 'pedirlas', 'pídelas hoy', 'haz tu pedido'] found

### coreference_agreement-04 · gpt-5.4-mini__segment · coreference_agreement

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Our new sneakers are lightweight and breathable. | Nuestras nuevas zapatillas son ligeras y transpirables. | ok |
| 2 | Order them today, and they arrive tomorrow. | Pídelos hoy y te llegarán mañana. | ok |

**Failed assertion** (not_contains, segment 2): ['pídelos', 'pídalos', 'cómpralos', 'encárgalos', 'solicítalos']  
→ found ['pídelos']

### implicit_subject_ellipsis-03 · llama-4-scout__segment · implicit_subject_ellipsis

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Try our new moisturizing cream for 30 days. | Prueba nuestra nueva crema hidratante durante 30 días. | ok |
| 2 | If you don't love it, send it back. | Si no te gusta, devuélvelo. | ok |
| 3 | This also applies to the travel size. | Esto también se aplica al tamaño de viaje. | ok |

**Failed assertion** (judge, segment 2): Any pronoun referring to the cream is feminine (la), e.g. 'devuélvela' or 'la', not masculine 'lo'.  
→ The pronoun 'lo' in 'devuélvelo' refers to the cream (crema, feminine), so it should be 'devuélvela'; the masculine form violates the property.

### implicit_subject_ellipsis-06 · llama-4-scout__segment · implicit_subject_ellipsis

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | We collect your email address and phone number. | Recopilamos tu dirección de correo electrónico y tu número de teléfono. | ok |
| 2 | We do not share the latter with third parties. | No compartimos esta última información con terceros. | ok |

**Failed assertion** (contains, segment 2): ['este último', 'el último', 'el segundo', 'número de teléfono', 'teléfono']  
→ none of ['este último', 'el último', 'el segundo', 'número de teléfono', 'teléfono'] found

### implicit_subject_ellipsis-06 · llama-4-scout__segment · implicit_subject_ellipsis

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | We collect your email address and phone number. | Recopilamos tu dirección de correo electrónico y tu número de teléfono. | ok |
| 2 | We do not share the latter with third parties. | No compartimos esta última información con terceros. | ok |

**Failed assertion** (judge, segment 2): The Spanish refers to the phone number (the second item) and uses a masculine singular form consistent with 'número', e.g. 'este último'.  
→ The translation uses the feminine 'esta última información', which agrees with 'información' rather than the masculine 'número', so it is not the masculine singular form like 'este último' and it does not point specifically to the phone number.

### implicit_subject_ellipsis-07 · llama-4-scout__segment · implicit_subject_ellipsis

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Remove the cap from the insulin pen. | Retire la tapa del bolígrafo de insulina. | ok |
| 2 | Attach a new needle. | Coloca una aguja nueva. | ok |
| 3 | Then replace it after use. | Luego reemplázalo después de su uso. | ok |

**Failed assertion** (judge, segment 3): The pronoun for 'it' is feminine singular ('la', e.g. 'Colóquela', 'vuelva a ponerla') matching tapa or aguja, and not masculine 'lo'.  
→ The pronoun used is masculine 'lo' (reemplázalo) rather than feminine 'la', so it does not match tapa or aguja as the property requires.

### implicit_subject_ellipsis-02 · llama-4-scout__document · implicit_subject_ellipsis

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Open the Settings panel. | 1. Abra el panel de Configuración. | ok |
| 2 | Scroll to the bottom and close it when you are done. | 2. Desplácese hasta la parte inferior y ciérrela cuando haya terminado. | ok |

**Failed assertion** (contains, segment 2): ['cierre', 'cierra', 'cerrarlo', 'ciérrelo', 'ciérralo', 'cerrar el panel']  
→ none of ['cierre', 'cierra', 'cerrarlo', 'ciérrelo', 'ciérralo', 'cerrar el panel'] found

### implicit_subject_ellipsis-02 · llama-4-scout__document · implicit_subject_ellipsis

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Open the Settings panel. | 1. Abra el panel de Configuración. | ok |
| 2 | Scroll to the bottom and close it when you are done. | 2. Desplácese hasta la parte inferior y ciérrela cuando haya terminado. | ok |

**Failed assertion** (not_contains, segment 2): ['cerrarla', 'ciérrala', 'ciérrela', 'cierre la', 'cierra la']  
→ found ['ciérrela']

### implicit_subject_ellipsis-03 · gpt-5.4-nano__segment · implicit_subject_ellipsis

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Try our new moisturizing cream for 30 days. | Prueba nuestra nueva crema hidratante durante 30 días. | ok |
| 2 | If you don't love it, send it back. | Si no te encanta, devuélvelo. | ok |
| 3 | This also applies to the travel size. | Esto también se aplica al tamaño de viaje. | ok |

**Failed assertion** (judge, segment 2): Any pronoun referring to the cream is feminine (la), e.g. 'devuélvela' or 'la', not masculine 'lo'.  
→ The pronoun 'lo' in 'devuélvelo' refers to the cream (crema, feminine), so it should be 'devuélvela'; the masculine form violates the property.

### implicit_subject_ellipsis-06 · gpt-5.4-nano__segment · implicit_subject_ellipsis

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | We collect your email address and phone number. | Recogemos su dirección de correo electrónico y su número de teléfono. | ok |
| 2 | We do not share the latter with third parties. | No compartimos lo último con terceros. | ok |

**Failed assertion** (contains, segment 2): ['este último', 'el último', 'el segundo', 'número de teléfono', 'teléfono']  
→ none of ['este último', 'el último', 'el segundo', 'número de teléfono', 'teléfono'] found

### implicit_subject_ellipsis-06 · gpt-5.4-nano__segment · implicit_subject_ellipsis

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | We collect your email address and phone number. | Recogemos su dirección de correo electrónico y su número de teléfono. | ok |
| 2 | We do not share the latter with third parties. | No compartimos lo último con terceros. | ok |

**Failed assertion** (judge, segment 2): The Spanish refers to the phone number (the second item) and uses a masculine singular form consistent with 'número', e.g. 'este último'.  
→ 'lo último' is a neuter, generic form that does not clearly refer to the phone number and is not a masculine singular form agreeing with 'número' (such as 'este último'), so the specific referent and agreement are not expressed.

### implicit_subject_ellipsis-07 · gpt-5.4-nano__segment · implicit_subject_ellipsis

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Remove the cap from the insulin pen. | Retire la tapa de la pluma de insulina. | ok |
| 2 | Attach a new needle. | Coloque una aguja nueva. | ok |
| 3 | Then replace it after use. | Luego sustitúyalo después de usarlo. | ok |

**Failed assertion** (judge, segment 3): The pronoun for 'it' is feminine singular ('la', e.g. 'Colóquela', 'vuelva a ponerla') matching tapa or aguja, and not masculine 'lo'.  
→ The translation uses masculine 'lo' in 'sustitúyalo' and 'usarlo' instead of feminine 'la' (e.g. 'sustitúyala', 'usarla') to match 'tapa' or 'aguja'.

### implicit_subject_ellipsis-07 · gpt-5.4-nano__document · implicit_subject_ellipsis

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Remove the cap from the insulin pen. | 1. Retire el capuchón de la pluma de insulina. | ok |
| 2 | Attach a new needle. | 2. Coloque una aguja nueva. | ok |
| 3 | Then replace it after use. | 3. A continuación, vuelva a colocar el capuchón después de usarla. | ok |

**Failed assertion** (judge, segment 3): The pronoun for 'it' is feminine singular ('la', e.g. 'Colóquela', 'vuelva a ponerla') matching tapa or aguja, and not masculine 'lo'.  
→ The translation does not use a feminine pronoun for 'it' as the object of replacing; it repeats the masculine noun 'el capuchón' and only has 'usarla' (feminine, likely referring to the needle), so the pronoun 'la' appears but is inconsistent with its masculine antecedent 'capuchón' and the required clitic pairing with the replacing verb is absent.

### implicit_subject_ellipsis-03 · gpt-5.4-mini__segment · implicit_subject_ellipsis

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Try our new moisturizing cream for 30 days. | Prueba nuestra nueva crema hidratante durante 30 días. | ok |
| 2 | If you don't love it, send it back. | Si no te encanta, devuélvelo. | ok |
| 3 | This also applies to the travel size. | Esto también se aplica al formato de viaje. | ok |

**Failed assertion** (judge, segment 2): Any pronoun referring to the cream is feminine (la), e.g. 'devuélvela' or 'la', not masculine 'lo'.  
→ The pronoun in 'devuélvelo' refers to the cream (crema, feminine) but is masculine 'lo' instead of feminine 'la' ('devuélvela'), so the property is violated.

### implicit_subject_ellipsis-07 · gpt-5.4-mini__segment · implicit_subject_ellipsis

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Remove the cap from the insulin pen. | Retire el capuchón de la pluma de insulina. | ok |
| 2 | Attach a new needle. | Coloque una aguja nueva. | ok |
| 3 | Then replace it after use. | Luego, sustitúyalo tras su uso. | ok |

**Failed assertion** (judge, segment 3): The pronoun for 'it' is feminine singular ('la', e.g. 'Colóquela', 'vuelva a ponerla') matching tapa or aguja, and not masculine 'lo'.  
→ The segment uses the masculine singular clitic 'lo' in 'sustitúyalo' rather than the feminine 'la' (as in 'sustitúyala'), so it does not match the feminine antecedents tapa/aguja.

### list_inheritance-02 · llama-4-scout__segment · list_inheritance

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Do not use the device if you: | No utilice el dispositivo si: | ok |
| 2 | are pregnant | están embarazadas | ok |
| 3 | have a pacemaker | tener un marcapasos | ok |
| 4 | are allergic to nickel | son alérgicos al níquel | ok |

**Failed assertion** (contains, segment 2): ['está embarazada', 'estás embarazada', 'esté embarazada', 'estéis embarazadas', 'se encuentra embarazada', 'está embarazada o', 'esté embarazada o']  
→ none of ['está embarazada', 'estás embarazada', 'esté embarazada', 'estéis embarazadas', 'se encuentra embarazada', 'está embarazada o', 'esté embarazada o'] found

### list_inheritance-02 · llama-4-scout__segment · list_inheritance

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Do not use the device if you: | No utilice el dispositivo si: | ok |
| 2 | are pregnant | están embarazadas | ok |
| 3 | have a pacemaker | tener un marcapasos | ok |
| 4 | are allergic to nickel | son alérgicos al níquel | ok |

**Failed assertion** (judge, segment None): Segments 2-4 use the same grammatical person and mood as the lead-in in segment 1 (e.g. if the lead-in is 'si usted...', items use 'está/tiene/es alérgico' consistently), so each item completes the sentence grammatically.  
→ Segment 3 uses the infinitive 'tener' while segments 2 and 4 use third-person plural forms ('están', 'son'), so the items are inconsistent with each other and with the usted lead-in, and 'tener un marcapasos' does not grammatically complete 'si:'.

### list_inheritance-03 · llama-4-scout__segment · list_inheritance

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | You may terminate this Agreement only if: | Puedes rescindir este Acuerdo únicamente si: | ok |
| 2 | the other party materially breaches it; | la otra parte incumple sustancialmente sus obligaciones; | ok |
| 3 | the other party becomes insolvent; or | la otra parte se vuelve insolvente; o | ok |
| 4 | a force majeure event lasts more than 90 days. | un evento de fuerza mayor dure más de 90 días. | ok |

**Failed assertion** (judge, segment None): Segments 2-4 are grammatical continuations of segment 1 as alternative conditions (consistent mood, e.g. subjunctive 'incumpla', 'sea declarada insolvente' or indicative consistently after the lead-in), preserving the list punctuation and the 'o' connector at the end of segment 3.  
→ Segments 2 and 3 use the indicative ('incumple', 'se vuelve') while segment 4 uses the subjunctive ('dure'), so the mood is inconsistent after the lead-in 'si:', even though the punctuation and the 'o' connector are preserved.

### list_inheritance-05 · llama-4-scout__segment · list_inheritance

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | To reset your password, you must: | Para restablecer tu contraseña, debes: | ok |
| 2 | open the Settings menu | Abre el menú de Ajustes | ok |
| 3 | select Security | seleccionar Seguridad | ok |
| 4 | click Reset | Haz clic en Restablecer | ok |

**Failed assertion** (judge, segment None): The items in segments 2-4 use one consistent verb form that fits the lead-in in segment 1 (either infinitives after 'debes/debe/tienes que', or imperatives consistent in register with the lead-in), with no mixture of forms and no register mismatch (tú vs usted).  
→ Segments 2 and 4 use tú imperatives (Abre, Haz) while segment 3 uses an infinitive (seleccionar), so the forms are mixed, and the imperatives also do not follow grammatically from the lead-in 'debes:', which requires infinitives.

### list_inheritance-07 · llama-4-scout__segment · list_inheritance

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | We will not share your personal data with third parties, except: | No compartiremos tus datos personales con terceros, excepto: | ok |
| 2 | where required by law; | donde lo exija la ley; | ok |
| 3 | with your explicit consent; or | con su consentimiento explícito; o | ok |
| 4 | to protect our legal rights. | para proteger nuestros derechos legales. | ok |

**Failed assertion** (judge, segment None): The items in segments 2-4 read as exceptions to the prohibition in segment 1 (cases where data may be shared) and are grammatically coherent with 'salvo/excepto' (e.g. 'cuando lo exija la ley', 'con su consentimiento explícito', 'para proteger...'), keeping the 'o' connector at the end of segment 3.  
→ Segments 2-4 do read as exceptions after 'excepto:' and the 'o' connector is kept at the end of segment 3, but segment 2 uses 'donde' (locative, 'in places where') rather than 'cuando', and segment 3 'su' clashes with the informal 'tus' of segment 1, so the property is not fully satisfied.

### list_inheritance-02 · gpt-5.4-nano__segment · list_inheritance

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Do not use the device if you: | No utilice el dispositivo si: | ok |
| 2 | are pregnant | están embarazadas | ok |
| 3 | have a pacemaker | tener un marcapasos | ok |
| 4 | are allergic to nickel | son alérgicas al níquel | ok |

**Failed assertion** (contains, segment 2): ['está embarazada', 'estás embarazada', 'esté embarazada', 'estéis embarazadas', 'se encuentra embarazada', 'está embarazada o', 'esté embarazada o']  
→ none of ['está embarazada', 'estás embarazada', 'esté embarazada', 'estéis embarazadas', 'se encuentra embarazada', 'está embarazada o', 'esté embarazada o'] found

### list_inheritance-02 · gpt-5.4-nano__segment · list_inheritance

| # | source | translation | segment QE |
|---|---|---|---|
| 1 | Do not use the device if you: | No utilice el dispositivo si: | ok |
| 2 | are pregnant | están embarazadas | ok |
| 3 | have a pacemaker | tener un marcapasos | ok |
| 4 | are allergic to nickel | son alérgicas al níquel | ok |

**Failed assertion** (judge, segment None): Segments 2-4 use the same grammatical person and mood as the lead-in in segment 1 (e.g. if the lead-in is 'si usted...', items use 'está/tiene/es alérgico' consistently), so each item completes the sentence grammatically.  
→ Segments 2 and 4 use third-person plural feminine forms (están, son), while segment 3 uses the infinitive 'tener', so the items are inconsistent with each other and with the lead-in, and segment 3 does not complete the sentence grammatically.
