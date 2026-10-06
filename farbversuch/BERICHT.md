# Bericht Farbversuch v2 (Hauptlauf Seeds 400–409)

Stand 06.10.2026. Gliederung nach Spec v2 §11. Grundlage:
- die eingefrorene Konfiguration (`frozen_config.json`, Commit `b9589ce`);
- der Hauptlauf in `results/main/` mit der Auswertung `results/main_report.md`;
- das Protokoll `PROTOKOLL.md`.

Abschnitt 2 enthält nur Beobachtungen. Jede Deutung steht in Abschnitt 3 und ist als Annahme gekennzeichnet.

## 1. Frage und Aufbau

**Frage:** Kann ein System eine Dimension, die es beim Üben ignorieren gelernt hat, wieder „öffnen“, wenn sie relevant wird? Die Dimension ist hier die Bodenfarbe.

Neuheit hilft dabei nicht. Die Farbe ist im Training vorhanden und variiert, ist aber bedeutungslos. Auslöser kann nur Überraschung im Ergebnis sein.

**Welt und Ablauf:**
- **Welt:** 9×9-Gitter mit vier Bodenfarben.
- **Routine:** imitiert einen BFS-Lehrer. Encoder z = tanh(E·x), Softmax-Policy.
- **Vorwärtsmodell:** sagt die eigene Verschiebung voraus. Die Überraschung (−log p) dient dem Bemerken.
- **Einsatz:** 400 Episoden, Wechsel bei Episode 100. Bedingungen:
  - `red`: Farbe 0 wird rutschig;
  - `global`: mehr Rutschen überall, mit gleicher mittlerer Überraschung;
  - `walls`: dichtere Wände;
  - `none`: keine Änderung.

**Systeme:**
- **M3-B (Hauptsystem):**
  - Bemerken über das Fenstermittel der Überraschung.
  - Erklären per kreuzvalidiertem Modellvergleich über 6 Zielzellen-Merkmale, mit Residualisieren, Mindestverbesserung δ und Übungs-Ontologie.
- **M3-A:** wie M3-B, aber mit 1192 Rohbit×Aktion-Merkmalen.
- **S1-B und S1-A:** CUSUM für das Bemerken, Permutationstest mit Holm für das Erklären. B und A bezeichnen dieselben Merkmalsmengen wie bei M3.

**Vorab festgelegt** (Spec v2 §7, Hauptlauf 400–409):
- **P1:** Prämissen in jedem Seed erfüllt.
- **P2:** M3-B schreibt `red` in ≥ 9/10 Seeds richtig zu.
- **P3:** M3-B öffnet bei `global` in ≥ 9/10 Seeds nichts.
- **P4:** M3-A ist langsamer oder macht mehr Fehlzuschreibungen als M3-B.
- **P5:** M3-B trifft bei `red` mindestens so oft wie S1-B.
- **Abbruch:** < 5/10 richtig bei `red` oder > 3/10 Öffnungen bei `global`.

## 2. Beobachtet

### 2.1 Vorhersagen und Abbruchkriterium

| Vorhersage | Ergebnis | Zahlen (95-%-Wilson-Intervall der Quote) |
|---|---|---|
| P1 Prämissen (P1 und P1b) | erfüllt | 10/10 |
| P2 M3-B schreibt `red` richtig zu | erfüllt | 10/10, Schwelle ≥ 9 (0,72–1,00) |
| P3 M3-B öffnet bei `global` nichts | **nicht erfüllt** | 6/10, Schwelle ≥ 9 (0,31–0,83) |
| P4 M3-A langsamer oder mehr Fehlzuschreibungen | erfüllt | Zuschreibungslatenz `red` M3-A 182 gegen M3-B 49 Episoden (zensiert am Horizont 300). Fehlzuschreibungen insgesamt M3-A 10, M3-B 11. P4 ist allein über die Latenz erfüllt. |
| P5 M3-B mindestens so treffsicher wie S1-B | erfüllt | Treffer bei `red`: M3-B 10, S1-B 9 |
| **Abbruchkriterium** | **ausgelöst** | M3-B öffnet bei `global` in 4/10 Seeds ein Merkmal (Grenze: > 3). Richtige Zuschreibung bei `red`: 10/10 (Grenze: < 5). |

Die Auswertung schreibt bei ausgelöstem Abbruchkriterium den vorab festgelegten Satz: „das Wiederöffnen per Modellvergleich funktioniert in diesem Aufbau nicht“.

**Integrität:**
- `freeze verify` vor und nach dem Lauf: OK.
- Fingerabdruck von Code und Umgebung auf allen 10 Seeds identisch, gleich dem beim Einfrieren protokollierten.
- `analyze` meldet keine Warnung.
- Lauf am 05./06.10.2026 von 20:56 bis 00:32, ohne Unterbrechung.

### 2.2 Prämissen (P1/P1b) und Übungs-Ontologien je Seed

| Seed | Farbinvarianz | Restanteil | Verschiebung | O von M3-B | O von M3-A (Anzahl) | O von S1-B | δ M3-B | δ M3-A |
|---|---|---|---|---|---|---|---|---|
| 400 | 0,964 | −0,049 | 0,090 | Wand | 3 | Farbe 0, Ziel | 0 | 0,0215 |
| 401 | 0,952 | 0,016 | 0,063 | Wand | 3 | – | 0 | 0,0423 |
| 402 | 0,974 | 0,052 | 0,068 | Wand | 3 | Farbe 2 | 0,0012 | 0,0265 |
| 403 | 0,957 | 0,051 | 0,072 | Wand | 4 | – | 0,0006 | 0,0043 |
| 404 | 0,972 | −0,018 | 0,072 | Wand | 2 | Ziel, Farbe 3 | 0 | 0,0417 |
| 405 | 0,960 | 0,024 | 0,071 | Wand | 3 | Farbe 2 | 0 | 0,0308 |
| 406 | 0,978 | 0,014 | 0,074 | Wand | 4 | – | 0,0018 | 0,0030 |
| 407 | 0,963 | 0,007 | 0,083 | Wand | 4 | – | 0,0017 | 0,0044 |
| 408 | 0,966 | 0,047 | 0,071 | Wand | 3 | Farbe 2 | 0 | 0,0260 |
| 409 | 0,970 | 0,021 | 0,077 | Wand | 4 | – | 0,0011 | 0,0032 |

Grenzen: Invarianz ≥ 0,95, Restanteil ≤ 0,15, Verschiebung ≤ 0,25. Das Vorwärtsmodell war auf allen Seeds besser als das Häufigkeitsmodell.

**Übungs-Ontologien:**
- **M3-B:** öffnete in allen 10 Seeds „Wand“ vor.
- **M3-A:** 2–4 Bit×Aktion-Merkmale. Bei M3-A ist „O“ seine eigene Übungs-Ontologie, nicht Farbe 0.
- **S1-B:** in 5 Seeds Farbmerkmale oder „Ziel“, in Seed 400 auch „Farbe 0“.
- **S1-A:** 1–8 Bit×Aktion-Merkmale.

Erwartete Fehlalarmrate des Bemerkens pro Strom: ≈ 1/21 ≈ 4,8 %. Das sind 20 Null-Ströme zu je 400 Episoden, Schwelle ist der größte Null-Wert.

### 2.3 Kennzahlen je System und Bedingung

Alle 10 Seeds haben die Prämisse erfüllt. Latenzen sind in Episoden nach dem Wechsel angegeben; „nicht bemerkt“ und „nicht zugeschrieben“ zählen mit 300.

| System | `none`: Fehlalarme | `red`: richtig zugeschrieben, Latenz Mittel | `red`: Fehlzuschreibungen | `global`: Öffnungen | `global`: Fehlzuschreibungen | `walls`: bemerkt / Fehlzuschreibungen |
|---|---|---|---|---|---|---|
| M3-B | 0 | 10/10, 49 | 7 | 4 (in 4 Seeds) | 3 | 2 / 1 |
| M3-A | 0 | 5/10, 182 | 6 | 9 | 4 | 2 / 0 |
| S1-B | 0 | 9/10, 72 | 8 | 20 | 17 | 0 / 0 |
| S1-A | 0 | 8/10, 104 | 18 | 21 | 18 | 0 / 0 |

Fehlzuschreibung nach Spec §6: Außerhalb von `red` zählt jedes geöffnete Farbmerkmal, unter `red` jede Öffnung außer der richtigen Zuschreibung.

**Bemerken:**
- Unter `red` und `global` haben M3 alle 10 Seeds bemerkt (mittlere Latenz 49 bzw. 42), S1 alle 10 bzw. 7 Seeds.
- Unter `walls` haben M3 2 Seeds bemerkt, S1 keinen.

### 2.4 M3-B im Einzelnen

**`red`:** M3-B öffnet „Farbe 0“ in allen 10 Seeds.

| Seed | 400 | 401 | 402 | 403 | 404 | 405 | 406 | 407 | 408 | 409 |
|---|---|---|---|---|---|---|---|---|---|---|
| Episode | 180 | 160 | 110 | 130 | 170 | 200 | 120 | 130 | 150 | 140 |
| Latenz | 80 | 60 | 10 | 30 | 70 | 100 | 20 | 30 | 50 | 40 |

- **Zusatzöffnungen:** in 6 Seeds, insgesamt 7 („Ziel“ 3×, „Farbe 1“, „Farbe 2“, „Farbe 3“ 2×).
- **Nutzbarkeit** (Gewinn der richtigen Öffnung): 0,004–0,041 nats pro Schritt.

**`global`:** Bemerkt wird in allen 10 Seeds (Episode 120–210). Geöffnet wird in 4 Seeds:

| Seed | Bemerkt bei | Geöffnet | Bei Episode | Gewinn | δ |
|---|---|---|---|---|---|
| 400 | 120 | Farbe 2 | 220 | 0,0017 | 0 |
| 403 | 180 | Ziel | 390 | 0,0014 | 0,0006 |
| 405 | 120 | Farbe 0 | 220 | 0,0014 | 0 |
| 409 | 120 | Farbe 0 | 180 | 0,0015 | 0,0011 |

- Alle vier Öffnungen liegen in einer späteren Erklärrunde, 60–210 Episoden nach dem Bemerken, nicht in der ersten.
- Ihre Gewinne (0,0014–0,0017) liegen unter allen Gewinnen der richtigen Öffnungen unter `red` (≥ 0,004).
- δ von M3-B war in 5 von 10 Seeds 0, darunter 2 der 4 Seeds mit Fehlöffnung.

**`none`:** kein Fehlalarm.

**`walls`:** bemerkt in 2 Seeds. Seed 407 öffnet „Farbe 3“.

### 2.5 Weitere Beobachtungen

- **S1-B, Seed 400:** S1-B hatte „Farbe 0“ schon in seiner Übungs-Ontologie. Ein Merkmal aus O kann nicht wieder geöffnet werden; das ist S1-Bs einziger Nichttreffer unter `red`.
- **M3-A unter `red`:** Die 5 Treffer haben Latenzen 20, 30, 30, 40 und 200.
- **`p_global`:** 0,213–0,276, überall `hit` und `bracketed`.
- **Laufzeit je Seed:** Phase 1 1589–1738 s, Rechenzeit gesamt 2271–6408 s. Wandzeit des ganzen Laufs auf 4 Kernen: 3 h 36 min.

## 3. Deutung (Annahme)

Alle Aussagen in diesem Abschnitt sind Annahmen. Geprüft ist nur, was in Abschnitt 2 steht.

1. **Bemerken und richtige Zuschreibung funktionieren hier.**
   - Die Routine hat die Farbe weitgehend ausgeblendet.
   - Das System bemerkt die rutschige Farbe trotzdem allein über Überraschung im Ergebnis, ohne Fehlalarm unter `none`.
   - Es öffnet in 10 von 10 Seeds genau die Dimension, die es vorher selbst geschlossen hatte.
   - Annahme: In diesem Aufbau gelingt das „Wiederöffnen“ im Sinn der Erklärungserweiterung zuverlässig.
2. **Die Abgrenzung gegen eine Änderung ohne Merkmalsursache gelingt nicht.**
   - Unter `global` öffnet M3-B in 4 von 10 Seeds ein Merkmal. Nach der vorab festgelegten Regel gilt das Wiederöffnen per Modellvergleich deshalb in diesem Aufbau als nicht funktionsfähig.
   - Annahme: Die Methode ist empfindlich, aber nicht spezifisch genug.
3. **Vermutete Ursache, nicht geprüft:** Die Fehlöffnungen haben kleine Gewinne und kommen erst nach mehreren Erklärrunden. δ ist dagegen pro einzelner Erklärung aus einem Endpuffer je Null-Strom kalibriert und war in der Hälfte der Seeds 0.
   - Annahme: Das wiederholte Erklären nach dem Bemerken, etwa 20–30 Runden je Strom, wirkt als nicht korrigierte Mehrfachprüfung. Gegen die Zeilenabhängigkeit der Kreuzvalidierung ist das nicht abgesichert.
   - Dagegen spricht: Im Bestätigungslauf (Seed 510) gab es eine Fehlöffnung schon beim ersten Erklären, mit δ > 0. Die Ursache ist also möglicherweise nicht allein die Mehrfachprüfung.
4. **Arm B gegen Arm A:**
   - M3-B trifft 10/10, M3-A 5/10.
   - Annahme: Ein großer Teil der Treffsicherheit kommt von der räumlichen Strukturvorgabe der 6 Zielzellen-Merkmale, nicht vom Verfahren allein.
5. **M3 gegen S1:**
   - S1-B trifft unter `red` fast gleich oft (9/10), öffnet unter `global` aber 20 Merkmale gegenüber 4 bei M3-B.
   - Annahme: Der Modellvergleich mit Residualisieren verringert falsche Öffnungen gegenüber marginalen Permutationstests deutlich, beseitigt sie aber nicht.
   - Eine allgemeine Überlegenheit gegenüber klassischer Statistik zeigt das nicht (Spec v2, Anhang B.3).

## 4. Grenzen

- **Zeilenabhängigkeit:** Die Kreuzvalidierung von M3 teilt nach Zeilen, die Permutationen von S1 vertauschen einzelne Zeilen. Schritte derselben Episode sind abhängig, die Fehlerniveaus des Erklärens sind daher vermutlich zu optimistisch. Die Wahl „Zeilen statt Episoden“ war ergebnisgeleitet (Diagnose auf Seed 0, Spec v2 Anhang A).
- **„Weitgehend geschlossen“, nicht „vollständig“:** P1/P1b operationalisieren „weitgehend ignoriert“ (Invarianz ≥ 0,95, Restanteil ≤ 0,15, Verschiebung ≤ 0,25). Der Restanteil ist kein Informationsprozentsatz; negative Werte bedeuten eine schlechtere Probe als die Mehrheitsbasis.
- **δ_Übung = 0,01 fest gewählt:** Die Mindestverbesserung des Vor-Öffnens wurde gesetzt, nicht kalibriert.
- **Kalibrierung:** Das Bemerken ist über ganze Null-Ströme kalibriert, δ über einen Endpuffer je Null-Strom. Eine Gesamtrate falscher Öffnungen über einen Einsatz ist nicht kalibriert. Spätere Öffnungen sind adaptiv: Sie sind bedingt auf frühere, und ihr Fehlerniveau ist ebenfalls nicht kalibriert.
- **Was „Wiederöffnen“ hier heißt:** Das Erklärmodell bekommt ein Merkmal dazu. Routine und Encoder bleiben unverändert, ein Umlernen ist nicht Teil dieser Version.
- **Strukturvorgabe von Arm B:** 6 handverlesene Zielzellen-Merkmale. Ein Vorteil von B gegenüber A ist zunächst ein Vorteil dieser Vorgabe in dieser Welt.
- **Zusatzöffnungen „Ziel“:** Sie zählen als Fehlzuschreibungen. Ein echter Vorhersagegewinn durch ein Ersatzmerkmal ist möglich, aber ungeprüft.
- **Stichprobe:** 10 Seeds, die Intervalle sind breit. Die Quote „keine Öffnung unter `global`“ liegt bei 0,31–0,83.
- **Eine Welt:** ein kleines Gitter mit einer einzigen rutschigen Farbe. Jede Übertragung auf andere Aufgaben ist eine Annahme.
- **Entwicklung auf denselben Regeln:** Alle Regeln und Trainingsparameter wurden auf den Seeds 0 und 500–504 entwickelt, darunter Raster und Evolution mit 34 Kandidaten. Danach wurde einmal auf 510–514 nach der gemeinsamen 4/5-Regel geprüft. Die Hauptlauf-Seeds 400–409 waren nach allen verfügbaren Aufzeichnungen vorher unbenutzt.

## 5. Pilot-Änderungen, Bestätigungsläufe, nachträgliche Erkundungen

Einzelheiten stehen in `PROTOKOLL.md`.

**Hintergrund:** Die Regeln von v2 entstanden aus einer explorativen Diagnose auf Seed 0 (Spec v2, Anhang A): Übungs-Ontologie, Residualisieren, δ, Kalibrierung über den größten Null-Wert und P1b. Die Diagnose war nicht Teil der Vorhersagen.

**Pilot-Änderungen**, nur Trainings-Hyperparameter der Routine:
1. `wd` 0,001 → 0,01 auf Seed 0. Grund: Die Farbinvarianz lag bei 0,926.
2. Nach dem gescheiterten Bestätigungslauf 500–504 folgten Raster und Evolution auf den Entwicklungs-Seeds 0 und 500–504.
   - Auswahlregel, vorab festgelegt: Invarianz ≥ 0,96 und Trainingsgenauigkeit ≥ 0,90 auf allen 6 Seeds.
   - Ergebnis: `wd` 0,0203, `lr` 0,1535, `epochs` 500, `init_std` 0,00772, `n_teacher_episodes` 8000.

**Bestätigungsläufe:**
- **500–504 (wd 0,01):** Regel nicht erfüllt. Die Prämisse hielt nur in 2/5 Seeds.
- **510–514 (Endkonfiguration):** gemeinsame 4/5-Regel erfüllt, Prämisse 5/5. Eine Fehlöffnung „Farbe 0“ unter `global` (Seed 510) gab es schon dort.
- 505–509 liefen nicht.

**Nachträgliche Erkundungen:** keine durchgeführt.
- **Möglich für eine v3:**
  - δ über die ganze Erklärserie eines Null-Stroms kalibrieren statt über einen Endpuffer;
  - die Kreuzvalidierung nach Episoden teilen;
  - eine Mindestverbesserung relativ zur Stärke der bemerkten Änderung.
- **Bedingungen:** Jede solche Änderung ist eine neue Version. Sie braucht frische Bestätigungs- und Hauptlauf-Seeds, die Seeds 400–409 sind verbraucht.
