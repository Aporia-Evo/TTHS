## Auswertung

### Vorhersagen

| Vorhersage | Ergebnis | Zahlen |
|---|---|---|
| P1 Prämissen | erfüllt | 10/10 Seeds erfüllen die Prämissen; gescheitert: keine |
| P2 M3-B schreibt `red` richtig zu | erfüllt | 10/10 Seeds (Schwelle ≥ 9) |
| P3 M3-B öffnet bei `global` nichts | nicht erfüllt | 6/10 Seeds ohne Öffnung (Schwelle ≥ 9) |
| P4 M3-A langsamer oder mehr Fehlzuschreibungen als M3-B | erfüllt | Zuschreibungslatenz `red` (Mittel, zensiert am Horizont): M3-A 182.0, M3-B 49.0, Abstand A − B 133.0 Episoden; Fehlzuschreibungen insgesamt: M3-A 10, M3-B 11, Abstand A − B -1 |
| P5 M3-B mindestens so treffsicher wie S1-B | erfüllt | Treffer bei `red`: M3-B 10, S1-B 9 (von 10 Seeds mit erfüllter Prämisse) |

Seeds mit gescheiterter Prämisse zählen bei P2, P3 und beim Abbruchkriterium gegen M3-B und fehlen in P4 und P5.

### Abbruchkriterium

| Größe | Wert | Abbruch bei |
|---|---|---|
| Richtige Zuschreibung M3-B bei `red` | 10/10 Seeds | < 5 |
| M3-B öffnet bei `global` ein Merkmal | 4/10 Seeds | > 3 |

Abbruchkriterium ausgelöst: das Wiederöffnen per Modellvergleich funktioniert in diesem Aufbau nicht.

### Werte je Seed

| Seed | Prämisse | Farbinvarianz | Restanteil | Verschiebung | Übungs-Ontologie M3-B | Übungs-Ontologie M3-A | Übungs-Ontologie S1-B | Übungs-Ontologie S1-A | δ M3-B | δ M3-A | Nutzbarkeit M3-B | Nutzbarkeit M3-A |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 400 | erfüllt | 0.964 | -0.049 | 0.090 | Wand | bit23&a2, bit25&a3, bit17&a0 | Farbe 0, Ziel | bit78&a2, bit153&a2, bit253&a2, bit121&a2, bit277&a2, bit131&a2, bit22&a2, bit268&a2 | 0.0000 | 0.0215 | 0.0187 | – |
| 401 | erfüllt | 0.952 | 0.016 | 0.063 | Wand | bit23&a2, bit25&a3, bit31&a1 | keine | bit67&a2, bit297&a2, bit231&a2, bit183&a2, bit171&a2, bit31&a1, bit121&a2, bit173&a2 | 0.0000 | 0.0423 | 0.0258 | – |
| 402 | erfüllt | 0.974 | 0.052 | 0.068 | Wand | bit23&a2, bit25&a3, bit17&a0 | Farbe 2 | bit59&a2, bit145&a2, bit166&a2, bit182&a2, bit100&a2, bit219&a2, bit211&a2, bit102&a2 | 0.0012 | 0.0265 | 0.0041 | – |
| 403 | erfüllt | 0.957 | 0.051 | 0.072 | Wand | bit23&a2, bit25&a3, bit31&a1, bit17&a0 | keine | bit92&a1, bit89&a1, bit31&a1, bit196&a1, bit287&a1, bit128&a1, bit279&a1, bit250&a1 | 0.0006 | 0.0043 | 0.0080 | 0.0083 |
| 404 | erfüllt | 0.972 | -0.018 | 0.072 | Wand | bit23&a2, bit25&a3 | Ziel, Farbe 3 | bit26&a3 | 0.0000 | 0.0417 | 0.0226 | – |
| 405 | erfüllt | 0.960 | 0.024 | 0.071 | Wand | bit23&a2, bit25&a3, bit17&a0 | Farbe 2 | bit82&a2, bit297&a2, bit286&a2, bit88&a2, bit195&a2, bit295&a2, bit236&a2, bit144&a2 | 0.0000 | 0.0308 | 0.0405 | – |
| 406 | erfüllt | 0.978 | 0.014 | 0.074 | Wand | bit23&a2, bit25&a3, bit17&a0, bit31&a1 | keine | bit17&a0, bit236&a0, bit209&a0, bit268&a0, bit228&a0 | 0.0018 | 0.0030 | 0.0102 | 0.0057 |
| 407 | erfüllt | 0.963 | 0.007 | 0.083 | Wand | bit23&a2, bit25&a3, bit17&a0, bit31&a1 | keine | bit188&a2 | 0.0017 | 0.0044 | 0.0116 | 0.0055 |
| 408 | erfüllt | 0.966 | 0.047 | 0.071 | Wand | bit25&a3, bit23&a2, bit31&a1 | Farbe 2 | bit31&a1, bit205&a1, bit264&a1, bit234&a1, bit242&a1, bit281&a1, bit109&a1, bit142&a1 | 0.0000 | 0.0260 | 0.0116 | 0.0264 |
| 409 | erfüllt | 0.970 | 0.021 | 0.077 | Wand | bit23&a2, bit25&a3, bit17&a0, bit31&a1 | keine | bit254&a2 | 0.0011 | 0.0032 | 0.0106 | 0.0044 |

Prämisse umfasst P1 und P1b; fehlende oder ungültige Messwerte zählen nicht als erfüllt. Restanteil und Verschiebung gehören zu P1b. Übungs-Ontologie: vor dem Einsatz geöffnete Merkmale des jeweiligen Systems; sie zählen nie als geöffnet. δ: Mindestverbesserung aus den Null-Strömen. Nutzbarkeit: mittlere Verbesserung (nats pro Schritt) des richtigen Merkmals (Arm B: „Farbe 0“, Arm A: Farbe-0-Bit in Richtung der Aktion) bei der ersten richtigen Öffnung durch das jeweilige M3-System unter `red`. „–“: im Ergebnis nicht enthalten oder keine richtige Öffnung.

### Kennzahlen je System und Bedingung (10 Seeds mit erfüllter Prämisse)

| System | Bedingung | Seeds | Fehlalarme | Bemerkt | Latenz Bemerken (Mittel) | Richtig zugeschrieben | Latenz Zuschreibung (Mittel) | Fehlzuschreibungen | Geöffnet |
|---|---|---|---|---|---|---|---|---|---|
| M3-B | none | 10 | 0 | 0 | – | – | – | 0 | 0 |
| M3-B | red | 10 | 0 | 10 | 49.0 | 10 | 49.0 | 7 | 17 |
| M3-B | global | 10 | 0 | 10 | 42.0 | – | – | 3 | 4 |
| M3-B | walls | 10 | 0 | 2 | 275.0 | – | – | 1 | 1 |
| M3-A | none | 10 | 0 | 0 | – | – | – | 0 | 0 |
| M3-A | red | 10 | 0 | 10 | 49.0 | 5 | 182.0 | 6 | 18 |
| M3-A | global | 10 | 0 | 10 | 42.0 | – | – | 4 | 9 |
| M3-A | walls | 10 | 0 | 2 | 275.0 | – | – | 0 | 0 |
| S1-B | none | 10 | 0 | 0 | – | – | – | 0 | 0 |
| S1-B | red | 10 | 0 | 10 | 49.1 | 9 | 72.0 | 8 | 17 |
| S1-B | global | 10 | 0 | 7 | 128.6 | – | – | 17 | 20 |
| S1-B | walls | 10 | 0 | 0 | 300.0 | – | – | 0 | 0 |
| S1-A | none | 10 | 0 | 0 | – | – | – | 0 | 0 |
| S1-A | red | 10 | 0 | 10 | 49.1 | 8 | 104.0 | 18 | 30 |
| S1-A | global | 10 | 0 | 7 | 128.6 | – | – | 18 | 21 |
| S1-A | walls | 10 | 0 | 0 | 300.0 | – | – | 0 | 0 |

Latenzen in Episoden ab dem Wechsel; nicht bemerkt oder nicht zugeschrieben zählt als Horizont. Die Latenz des Bemerkens mittelt über Seeds ohne Fehlalarm und gilt nicht für `none`.

Erwartete Fehlalarmrate pro Strom: ≈ 1/21 = 4,8 % (20 Null-Ströme, höchstens 0 Alarme bei der Kalibrierung).

### Kosten

| System | Bedingung | Puffer (Byte) | Anpassungen | Größe der Anpassungen | Prüfung Mittel (s) | Prüfung Max (s) | Gesamt (s) |
|---|---|---|---|---|---|---|---|
| M3-B | none | 616000 | 0 | 0 | 0.000 | 0.003 | 0.07 |
| M3-B | red | 616000 | 5910 | 3401955360 | 0.255 | 0.544 | 92.71 |
| M3-B | global | 616000 | 7745 | 4351536000 | 0.332 | 0.613 | 124.32 |
| M3-B | walls | 616000 | 785 | 440712000 | 0.028 | 0.515 | 10.47 |
| M3-A | none | 616000 | 0 | 0 | 0.000 | 0.000 | 0.00 |
| M3-A | red | 616000 | 871844 | 520820265753 | 41.922 | 83.400 | 11696.22 |
| M3-A | global | 616000 | 1195439 | 714440880000 | 50.328 | 84.368 | 16759.33 |
| M3-A | walls | 616000 | 143700 | 85755254400 | 4.276 | 67.912 | 1603.53 |
| S1-B | none | 616000 | 0 | 0 | 0.000 | 0.000 | 0.00 |
| S1-B | red | 616000 | 0 | 0 | 0.043 | 0.167 | 10.98 |
| S1-B | global | 616000 | 0 | 0 | 0.044 | 0.112 | 4.70 |
| S1-B | walls | 616000 | 0 | 0 | 0.000 | 0.000 | 0.00 |
| S1-A | none | 616000 | 0 | 0 | 0.000 | 0.000 | 0.00 |
| S1-A | red | 616000 | 0 | 0 | 3.154 | 3.564 | 37.85 |
| S1-A | global | 616000 | 0 | 0 | 3.112 | 3.530 | 158.71 |
| S1-A | walls | 616000 | 0 | 0 | 0.000 | 0.000 | 0.00 |

