## Auswertung

> **Explorative Auswertung (Seeds 500, 501, 502, 503, 504) – keine Prüfung der vorregistrierten Vorhersagen; diese gilt nur für die Seeds 400–409.**

### Vorhersagen

| Vorhersage | Ergebnis | Zahlen |
|---|---|---|
| P1 Prämissen | nicht erfüllt | 2/5 Seeds erfüllen die Prämissen; gescheitert: 501, 503, 504 |
| P2 M3-B schreibt `red` richtig zu | – | 2/5 Seeds (Schwelle ≥ 9) |
| P3 M3-B öffnet bei `global` nichts | – | 2/5 Seeds ohne Öffnung (Schwelle ≥ 9) |
| P4 M3-A langsamer oder mehr Fehlzuschreibungen als M3-B | – | Zuschreibungslatenz `red` (Mittel, zensiert am Horizont): M3-A 105.0, M3-B 35.0, Abstand A − B 70.0 Episoden; Fehlzuschreibungen insgesamt: M3-A 1, M3-B 1, Abstand A − B 0 |
| P5 M3-B mindestens so treffsicher wie S1-B | – | Treffer bei `red`: M3-B 2, S1-B 2 (von 2 Seeds mit erfüllter Prämisse) |

Seeds mit gescheiterter Prämisse zählen bei P2, P3 und beim Abbruchkriterium gegen M3-B und fehlen in P4 und P5.

### Abbruchkriterium

| Größe | Wert | Abbruch bei |
|---|---|---|
| Richtige Zuschreibung M3-B bei `red` | 2/5 Seeds | < 5 |
| M3-B öffnet bei `global` ein Merkmal | 3/5 Seeds | > 3 |


### Werte je Seed

| Seed | Prämisse | Farbinvarianz | Restanteil | Verschiebung | Übungs-Ontologie M3-B | Übungs-Ontologie M3-A | Übungs-Ontologie S1-B | Übungs-Ontologie S1-A | δ M3-B | δ M3-A | Nutzbarkeit M3-B | Nutzbarkeit M3-A |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 500 | erfüllt | 0.967 | 0.029 | 0.104 | Wand | bit23&a2, bit25&a3, bit17&a0 | Farbe 2 | bit202&a2, bit125&a2, bit219&a2, bit122&a2 | 0.0005 | 0.0172 | 0.0092 | 0.0179 |
| 501 | nicht erfüllt | 0.939 | 0.011 | 0.082 | – | – | – | – | – | – | – | – |
| 502 | erfüllt | 0.980 | 0.065 | 0.104 | Wand | bit25&a3, bit23&a2, bit17&a0 | Farbe 2 | bit141&a2, bit242&a2, bit219&a2, bit169&a2, bit17&a2, bit178&a3 | 0.0011 | 0.0141 | 0.0060 | 0.0149 |
| 503 | nicht erfüllt | 0.941 | 0.004 | 0.080 | – | – | – | – | – | – | – | – |
| 504 | nicht erfüllt | 0.946 | -0.035 | 0.081 | – | – | – | – | – | – | – | – |

Prämisse umfasst P1 und P1b; fehlende oder ungültige Messwerte zählen nicht als erfüllt. Restanteil und Verschiebung gehören zu P1b. Übungs-Ontologie: vor dem Einsatz geöffnete Merkmale des jeweiligen Systems; sie zählen nie als geöffnet. δ: Mindestverbesserung aus den Null-Strömen. Nutzbarkeit: mittlere Verbesserung (nats pro Schritt) des richtigen Merkmals (Arm B: „Farbe 0“, Arm A: Farbe-0-Bit in Richtung der Aktion) bei der ersten richtigen Öffnung durch das jeweilige M3-System unter `red`. „–“: im Ergebnis nicht enthalten oder keine richtige Öffnung.

### Kennzahlen je System und Bedingung (2 Seeds mit erfüllter Prämisse)

| System | Bedingung | Seeds | Fehlalarme | Bemerkt | Latenz Bemerken (Mittel) | Richtig zugeschrieben | Latenz Zuschreibung (Mittel) | Fehlzuschreibungen | Geöffnet |
|---|---|---|---|---|---|---|---|---|---|
| M3-B | none | 2 | 0 | 0 | – | – | – | 0 | 0 |
| M3-B | red | 2 | 0 | 2 | 35.0 | 2 | 35.0 | 1 | 3 |
| M3-B | global | 2 | 0 | 2 | 30.0 | – | – | 0 | 0 |
| M3-B | walls | 2 | 0 | 1 | 255.0 | – | – | 0 | 0 |
| M3-A | none | 2 | 0 | 0 | – | – | – | 0 | 0 |
| M3-A | red | 2 | 0 | 2 | 35.0 | 2 | 105.0 | 1 | 6 |
| M3-A | global | 2 | 0 | 2 | 30.0 | – | – | 0 | 1 |
| M3-A | walls | 2 | 0 | 1 | 255.0 | – | – | 0 | 1 |
| S1-B | none | 2 | 0 | 0 | – | – | – | 0 | 0 |
| S1-B | red | 2 | 0 | 2 | 61.5 | 2 | 65.0 | 3 | 5 |
| S1-B | global | 2 | 0 | 1 | 274.5 | – | – | 1 | 1 |
| S1-B | walls | 2 | 0 | 0 | 300.0 | – | – | 0 | 0 |
| S1-A | none | 2 | 0 | 0 | – | – | – | 0 | 0 |
| S1-A | red | 2 | 0 | 2 | 61.5 | 1 | 195.0 | 4 | 6 |
| S1-A | global | 2 | 0 | 1 | 274.5 | – | – | 1 | 1 |
| S1-A | walls | 2 | 0 | 0 | 300.0 | – | – | 0 | 0 |

Latenzen in Episoden ab dem Wechsel; nicht bemerkt oder nicht zugeschrieben zählt als Horizont. Die Latenz des Bemerkens mittelt über Seeds ohne Fehlalarm und gilt nicht für `none`.

Erwartete Fehlalarmrate pro Strom: ≈ 1/21 = 4,8 % (20 Null-Ströme, höchstens 0 Alarme bei der Kalibrierung).

### Kosten

| System | Bedingung | Puffer (Byte) | Anpassungen | Größe der Anpassungen | Prüfung Mittel (s) | Prüfung Max (s) | Gesamt (s) |
|---|---|---|---|---|---|---|---|
| M3-B | none | 616000 | 0 | 0 | 0.000 | 0.001 | 0.02 |
| M3-B | red | 616000 | 1260 | 728136000 | 0.328 | 0.673 | 24.63 |
| M3-B | global | 616000 | 1680 | 939456000 | 0.452 | 0.682 | 33.93 |
| M3-B | walls | 616000 | 300 | 167760000 | 0.066 | 0.566 | 4.98 |
| M3-A | none | 616000 | 0 | 0 | 0.000 | 0.000 | 0.00 |
| M3-A | red | 616000 | 110862 | 66664886400 | 42.452 | 94.338 | 1740.51 |
| M3-A | global | 616000 | 295988 | 176805604800 | 69.781 | 100.909 | 5233.57 |
| M3-A | walls | 616000 | 52687 | 31635648000 | 10.016 | 87.522 | 751.20 |
| S1-B | none | 616000 | 0 | 0 | 0.000 | 0.000 | 0.00 |
| S1-B | red | 616000 | 0 | 0 | 0.044 | 0.083 | 1.20 |
| S1-B | global | 616000 | 0 | 0 | 0.042 | 0.046 | 0.25 |
| S1-B | walls | 616000 | 0 | 0 | 0.000 | 0.000 | 0.00 |
| S1-A | none | 616000 | 0 | 0 | 0.000 | 0.000 | 0.00 |
| S1-A | red | 616000 | 0 | 0 | 3.053 | 3.087 | 6.11 |
| S1-A | global | 616000 | 0 | 0 | 3.168 | 3.293 | 19.01 |
| S1-A | walls | 616000 | 0 | 0 | 0.000 | 0.000 | 0.00 |

## Bestätigung (Spec v2 §8)

Seeds 500, 501, 502, 503, 504 (n = 5), explorativ ausgewertet. Die Methode gilt als bestätigt, wenn in mindestens 4 von 5 Seeds alle drei Kriterien gleichzeitig gelten (Präzisierung, Entscheidung des Nutzers vom 04.10.2026). Ein Seed mit gescheiterter Prämisse zählt bei den Kriterien 2 und 3 als nicht erfüllt. Die Zählungen je Kriterium stehen nur zur Information da.

| Kriterium | Seeds | Benötigt | Ergebnis |
|---|---|---|---|
| **Alle drei Kriterien gleichzeitig (entscheidend)** | 2/5 | ≥ 4 | nicht erfüllt |
| 1 Prämissen P1 und P1b erfüllt (zur Information) | 2/5 | – | – |
| 2 M3-B öffnet bei `none` und `global` nichts über die Übungs-Ontologie hinaus (zur Information) | 2/5 | – | – |
| 3 M3-B öffnet bei `red` „Farbe 0“ nach dem Wechsel (zur Information) | 2/5 | – | – |

| Seed | Kriterium 1 | Kriterium 2 | Kriterium 3 | Alle drei |
|---|---|---|---|---|
| 500 | ja | ja | ja | ja |
| 501 | nein | nein | nein | nein |
| 502 | ja | ja | ja | ja |
| 503 | nein | nein | nein | nein |
| 504 | nein | nein | nein | nein |

Nicht bestätigt: Ergebnis zurück an den Nutzer; eine weitere Runde läuft nur auf neuen Seeds.
