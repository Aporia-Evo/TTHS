## Auswertung

> **Explorative Auswertung (Seeds 0) – keine Prüfung der vorregistrierten Vorhersagen; diese gilt nur für die Seeds 400–409.**

### Vorhersagen

| Vorhersage | Ergebnis | Zahlen |
|---|---|---|
| P1 Prämissen | erfüllt | 1/1 Seeds erfüllen die Prämissen; gescheitert: keine |
| P2 M3-B schreibt `red` richtig zu | – | 1/1 Seeds (Schwelle ≥ 9) |
| P3 M3-B öffnet bei `global` nichts | – | 1/1 Seeds ohne Öffnung (Schwelle ≥ 9) |
| P4 M3-A langsamer oder mehr Fehlzuschreibungen als M3-B | – | Zuschreibungslatenz `red` (Mittel, zensiert am Horizont): M3-A 90.0, M3-B 10.0, Abstand A − B 80.0 Episoden; Fehlzuschreibungen insgesamt: M3-A 0, M3-B 0, Abstand A − B 0 |
| P5 M3-B mindestens so treffsicher wie S1-B | – | Treffer bei `red`: M3-B 1, S1-B 1 (von 1 Seeds mit erfüllter Prämisse) |

Seeds mit gescheiterter Prämisse zählen bei P2, P3 und beim Abbruchkriterium gegen M3-B und fehlen in P4 und P5.

### Abbruchkriterium

| Größe | Wert | Abbruch bei |
|---|---|---|
| Richtige Zuschreibung M3-B bei `red` | 1/1 Seeds | < 5 |
| M3-B öffnet bei `global` ein Merkmal | 0/1 Seeds | > 3 |


### Werte je Seed

| Seed | Prämisse | Farbinvarianz | Restanteil | Verschiebung | Übungs-Ontologie M3-B | Übungs-Ontologie M3-A | Übungs-Ontologie S1-B | Übungs-Ontologie S1-A | δ M3-B | δ M3-A | Nutzbarkeit M3-B | Nutzbarkeit M3-A |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | erfüllt | 0.980 | -0.036 | 0.103 | Wand | bit25&a3, bit23&a2, bit31&a1 | Farbe 3 | bit93&a3, bit296&a3, bit144&a3, bit189&a2, bit143&a3, bit279&a3, bit118&a3, bit270&a3 | 0.0008 | 0.0199 | 0.0062 | 0.0200 |

Prämisse umfasst P1 und P1b; fehlende oder ungültige Messwerte zählen nicht als erfüllt. Restanteil und Verschiebung gehören zu P1b. Übungs-Ontologie: vor dem Einsatz geöffnete Merkmale des jeweiligen Systems; sie zählen nie als geöffnet. δ: Mindestverbesserung aus den Null-Strömen. Nutzbarkeit: mittlere Verbesserung (nats pro Schritt) des richtigen Merkmals (Arm B: „Farbe 0“, Arm A: Farbe-0-Bit in Richtung der Aktion) bei der ersten richtigen Öffnung durch das jeweilige M3-System unter `red`. „–“: im Ergebnis nicht enthalten oder keine richtige Öffnung.

### Kennzahlen je System und Bedingung (1 Seeds mit erfüllter Prämisse)

| System | Bedingung | Seeds | Fehlalarme | Bemerkt | Latenz Bemerken (Mittel) | Richtig zugeschrieben | Latenz Zuschreibung (Mittel) | Fehlzuschreibungen | Geöffnet |
|---|---|---|---|---|---|---|---|---|---|
| M3-B | none | 1 | 1 | 0 | – | – | – | 0 | 0 |
| M3-B | red | 1 | 0 | 1 | 10.0 | 1 | 10.0 | 0 | 1 |
| M3-B | global | 1 | 0 | 1 | 20.0 | – | – | 0 | 0 |
| M3-B | walls | 1 | 0 | 0 | 300.0 | – | – | 0 | 0 |
| M3-A | none | 1 | 1 | 0 | – | – | – | 0 | 0 |
| M3-A | red | 1 | 0 | 1 | 10.0 | 1 | 90.0 | 0 | 3 |
| M3-A | global | 1 | 0 | 1 | 20.0 | – | – | 0 | 0 |
| M3-A | walls | 1 | 0 | 0 | 300.0 | – | – | 0 | 0 |
| S1-B | none | 1 | 1 | 0 | – | – | – | 1 | 1 |
| S1-B | red | 1 | 0 | 1 | 5.0 | 1 | 10.0 | 1 | 2 |
| S1-B | global | 1 | 0 | 1 | 141.0 | – | – | 2 | 2 |
| S1-B | walls | 1 | 0 | 0 | 300.0 | – | – | 0 | 0 |
| S1-A | none | 1 | 1 | 0 | – | – | – | 1 | 3 |
| S1-A | red | 1 | 0 | 1 | 5.0 | 1 | 10.0 | 2 | 3 |
| S1-A | global | 1 | 0 | 1 | 141.0 | – | – | 2 | 3 |
| S1-A | walls | 1 | 0 | 0 | 300.0 | – | – | 0 | 0 |

Latenzen in Episoden ab dem Wechsel; nicht bemerkt oder nicht zugeschrieben zählt als Horizont. Die Latenz des Bemerkens mittelt über Seeds ohne Fehlalarm und gilt nicht für `none`.

Erwartete Fehlalarmrate pro Strom: ≈ 1/21 = 4,8 % (20 Null-Ströme, höchstens 0 Alarme bei der Kalibrierung).

### Kosten

| System | Bedingung | Puffer (Byte) | Anpassungen | Größe der Anpassungen | Prüfung Mittel (s) | Prüfung Max (s) | Gesamt (s) |
|---|---|---|---|---|---|---|---|
| M3-B | none | 616000 | 450 | 251640000 | 0.182 | 0.544 | 6.93 |
| M3-B | red | 616000 | 755 | 430398648 | 0.377 | 0.609 | 14.32 |
| M3-B | global | 616000 | 870 | 486302688 | 0.443 | 0.668 | 16.85 |
| M3-B | walls | 616000 | 0 | 0 | 0.000 | 0.001 | 0.01 |
| M3-A | none | 616000 | 79563 | 46972915200 | 29.002 | 77.466 | 1102.07 |
| M3-A | red | 616000 | 121376 | 72974133513 | 65.836 | 99.614 | 2040.91 |
| M3-A | global | 616000 | 153568 | 90627258591 | 68.488 | 95.855 | 2602.54 |
| M3-A | walls | 616000 | 0 | 0 | 0.000 | 0.000 | 0.00 |
| S1-B | none | 616000 | 0 | 0 | 0.047 | 0.099 | 0.84 |
| S1-B | red | 616000 | 0 | 0 | 0.047 | 0.083 | 1.40 |
| S1-B | global | 616000 | 0 | 0 | 0.042 | 0.044 | 0.67 |
| S1-B | walls | 616000 | 0 | 0 | 0.000 | 0.000 | 0.00 |
| S1-A | none | 616000 | 0 | 0 | 3.357 | 3.357 | 3.36 |
| S1-A | red | 616000 | 0 | 0 | 2.966 | 3.057 | 5.93 |
| S1-A | global | 616000 | 0 | 0 | 3.054 | 3.143 | 18.33 |
| S1-A | walls | 616000 | 0 | 0 | 0.000 | 0.000 | 0.00 |

