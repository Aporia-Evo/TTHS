## Auswertung

> **Explorative Auswertung (Seeds 510, 511, 512, 513, 514) – keine Prüfung der vorregistrierten Vorhersagen; diese gilt nur für die Seeds 400–409.**

### Vorhersagen

| Vorhersage | Ergebnis | Zahlen |
|---|---|---|
| P1 Prämissen | erfüllt | 5/5 Seeds erfüllen die Prämissen; gescheitert: keine |
| P2 M3-B schreibt `red` richtig zu | – | 5/5 Seeds (Schwelle ≥ 9) |
| P3 M3-B öffnet bei `global` nichts | – | 4/5 Seeds ohne Öffnung (Schwelle ≥ 9) |
| P4 M3-A langsamer oder mehr Fehlzuschreibungen als M3-B | – | Zuschreibungslatenz `red` (Mittel, zensiert am Horizont): M3-A 144.0, M3-B 34.0, Abstand A − B 110.0 Episoden; Fehlzuschreibungen insgesamt: M3-A 2, M3-B 5, Abstand A − B -3 |
| P5 M3-B mindestens so treffsicher wie S1-B | – | Treffer bei `red`: M3-B 5, S1-B 5 (von 5 Seeds mit erfüllter Prämisse) |

Seeds mit gescheiterter Prämisse zählen bei P2, P3 und beim Abbruchkriterium gegen M3-B und fehlen in P4 und P5.

### Abbruchkriterium

| Größe | Wert | Abbruch bei |
|---|---|---|
| Richtige Zuschreibung M3-B bei `red` | 5/5 Seeds | < 5 |
| M3-B öffnet bei `global` ein Merkmal | 1/5 Seeds | > 3 |


### Werte je Seed

| Seed | Prämisse | Farbinvarianz | Restanteil | Verschiebung | Übungs-Ontologie M3-B | Übungs-Ontologie M3-A | Übungs-Ontologie S1-B | Übungs-Ontologie S1-A | δ M3-B | δ M3-A | Nutzbarkeit M3-B | Nutzbarkeit M3-A |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 510 | erfüllt | 0.978 | -0.064 | 0.082 | Wand | bit23&a2, bit25&a3, bit17&a0 | Farbe 1 | bit195&a3, bit111&a2, bit294&a2, bit237&a2, bit117&a2, bit170&a2, bit194&a3, bit293&a2 | 0.0019 | 0.0344 | 0.0152 | – |
| 511 | erfüllt | 0.964 | 0.054 | 0.083 | Wand | bit25&a3, bit23&a2, bit17&a0, bit31&a1 | Farbe 1 | bit79&a3, bit296&a3, bit147&a3, bit288&a3, bit266&a3, bit31&a1, bit86&a1, bit232&a3 | 0.0000 | 0.0041 | 0.0159 | 0.0058 |
| 512 | erfüllt | 0.971 | 0.056 | 0.075 | Wand | bit23&a2, bit25&a3, bit31&a1, bit17&a0 | keine | bit139&a2 | 0.0000 | 0.0042 | 0.0137 | 0.0050 |
| 513 | erfüllt | 0.965 | 0.041 | 0.066 | Wand | bit25&a3, bit23&a2 | Farbe 2 | bit221&a3, bit48&a3 | 0.0015 | 0.0318 | 0.0089 | – |
| 514 | erfüllt | 0.984 | 0.025 | 0.076 | Wand | bit25&a3, bit23&a2, bit17&a0, bit31&a1 | Farbe 1 | bit60&a2, bit59&a2, bit297&a2, bit202&a2, bit105&a3, bit191&a2, bit257&a2, bit146&a2 | 0.0007 | 0.0041 | 0.0126 | 0.0067 |

Prämisse umfasst P1 und P1b; fehlende oder ungültige Messwerte zählen nicht als erfüllt. Restanteil und Verschiebung gehören zu P1b. Übungs-Ontologie: vor dem Einsatz geöffnete Merkmale des jeweiligen Systems; sie zählen nie als geöffnet. δ: Mindestverbesserung aus den Null-Strömen. Nutzbarkeit: mittlere Verbesserung (nats pro Schritt) des richtigen Merkmals (Arm B: „Farbe 0“, Arm A: Farbe-0-Bit in Richtung der Aktion) bei der ersten richtigen Öffnung durch das jeweilige M3-System unter `red`. „–“: im Ergebnis nicht enthalten oder keine richtige Öffnung.

### Kennzahlen je System und Bedingung (5 Seeds mit erfüllter Prämisse)

| System | Bedingung | Seeds | Fehlalarme | Bemerkt | Latenz Bemerken (Mittel) | Richtig zugeschrieben | Latenz Zuschreibung (Mittel) | Fehlzuschreibungen | Geöffnet |
|---|---|---|---|---|---|---|---|---|---|
| M3-B | none | 5 | 0 | 0 | – | – | – | 0 | 0 |
| M3-B | red | 5 | 0 | 5 | 30.0 | 5 | 34.0 | 2 | 7 |
| M3-B | global | 5 | 0 | 5 | 28.0 | – | – | 1 | 1 |
| M3-B | walls | 5 | 0 | 2 | 256.0 | – | – | 2 | 2 |
| M3-A | none | 5 | 0 | 0 | – | – | – | 0 | 0 |
| M3-A | red | 5 | 0 | 5 | 30.0 | 3 | 144.0 | 1 | 10 |
| M3-A | global | 5 | 0 | 5 | 28.0 | – | – | 0 | 6 |
| M3-A | walls | 5 | 0 | 2 | 256.0 | – | – | 1 | 1 |
| S1-B | none | 5 | 0 | 0 | – | – | – | 0 | 0 |
| S1-B | red | 5 | 0 | 5 | 48.6 | 5 | 54.0 | 6 | 11 |
| S1-B | global | 5 | 0 | 3 | 194.0 | – | – | 6 | 8 |
| S1-B | walls | 5 | 0 | 2 | 274.0 | – | – | 2 | 2 |
| S1-A | none | 5 | 0 | 0 | – | – | – | 0 | 0 |
| S1-A | red | 5 | 0 | 5 | 48.6 | 3 | 162.0 | 10 | 15 |
| S1-A | global | 5 | 0 | 3 | 194.0 | – | – | 7 | 8 |
| S1-A | walls | 5 | 0 | 2 | 274.0 | – | – | 4 | 6 |

Latenzen in Episoden ab dem Wechsel; nicht bemerkt oder nicht zugeschrieben zählt als Horizont. Die Latenz des Bemerkens mittelt über Seeds ohne Fehlalarm und gilt nicht für `none`.

Erwartete Fehlalarmrate pro Strom: ≈ 1/21 = 4,8 % (20 Null-Ströme, höchstens 0 Alarme bei der Kalibrierung).

### Kosten

| System | Bedingung | Puffer (Byte) | Anpassungen | Größe der Anpassungen | Prüfung Mittel (s) | Prüfung Max (s) | Gesamt (s) |
|---|---|---|---|---|---|---|---|
| M3-B | none | 616000 | 0 | 0 | 0.000 | 0.001 | 0.04 |
| M3-B | red | 616000 | 3415 | 1959765948 | 0.309 | 0.584 | 57.87 |
| M3-B | global | 616000 | 4085 | 2293207740 | 0.398 | 0.788 | 74.39 |
| M3-B | walls | 616000 | 585 | 334944000 | 0.048 | 0.741 | 9.05 |
| M3-A | none | 616000 | 0 | 0 | 0.000 | 0.000 | 0.00 |
| M3-A | red | 616000 | 368855 | 219392981604 | 45.171 | 89.747 | 5285.03 |
| M3-A | global | 616000 | 739798 | 446430684420 | 64.036 | 98.479 | 11910.64 |
| M3-A | walls | 616000 | 127660 | 78049598400 | 7.560 | 66.705 | 1413.64 |
| S1-B | none | 616000 | 0 | 0 | 0.000 | 0.000 | 0.00 |
| S1-B | red | 616000 | 0 | 0 | 0.046 | 0.128 | 4.49 |
| S1-B | global | 616000 | 0 | 0 | 0.047 | 0.066 | 1.63 |
| S1-B | walls | 616000 | 0 | 0 | 0.045 | 0.065 | 0.63 |
| S1-A | none | 616000 | 0 | 0 | 0.000 | 0.000 | 0.00 |
| S1-A | red | 616000 | 0 | 0 | 3.296 | 3.386 | 16.48 |
| S1-A | global | 616000 | 0 | 0 | 3.469 | 3.864 | 79.79 |
| S1-A | walls | 616000 | 0 | 0 | 3.438 | 3.709 | 6.88 |

## Bestätigung (Spec v2 §8)

Seeds 510, 511, 512, 513, 514 (n = 5), explorativ ausgewertet. Die Methode gilt als bestätigt, wenn in mindestens 4 von 5 Seeds alle drei Kriterien gleichzeitig gelten (Präzisierung, Entscheidung des Nutzers vom 04.10.2026). Ein Seed mit gescheiterter Prämisse zählt bei den Kriterien 2 und 3 als nicht erfüllt. Die Zählungen je Kriterium stehen nur zur Information da.

| Kriterium | Seeds | Benötigt | Ergebnis |
|---|---|---|---|
| **Alle drei Kriterien gleichzeitig (entscheidend)** | 4/5 | ≥ 4 | erfüllt |
| 1 Prämissen P1 und P1b erfüllt (zur Information) | 5/5 | – | – |
| 2 M3-B öffnet bei `none` und `global` nichts über die Übungs-Ontologie hinaus (zur Information) | 4/5 | – | – |
| 3 M3-B öffnet bei `red` „Farbe 0“ nach dem Wechsel (zur Information) | 5/5 | – | – |

| Seed | Kriterium 1 | Kriterium 2 | Kriterium 3 | Alle drei |
|---|---|---|---|---|
| 510 | ja | nein | ja | nein |
| 511 | ja | ja | ja | ja |
| 512 | ja | ja | ja | ja |
| 513 | ja | ja | ja | ja |
| 514 | ja | ja | ja | ja |

Bestätigt.
