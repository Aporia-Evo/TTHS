# Spezifikation: Wiederöffnen einer ignorierten Dimension („Farbversuch“)

Stand: 03.10.2026 · Status: Entwurf zur Freigabe · Umsetzung: Claude Code
Ablage im Repo: `docs/superpowers/specs/2026-10-03-farb-wiederoeffnung-design.md`

Diese Spezifikation ist eigenständig. Sie setzt keinen Code aus früheren Versuchen voraus.

---

## 1. Frage und Abgrenzung

**Frage:** Kann ein System lernen, welche Information es bei einer Routine ignorieren darf, und erkennen, wann diese Vereinfachung nicht mehr reicht?

**Umfang dieser Version:** nur **Bemerken** und **Erklären**. Die Routine wird nach dem Üben nicht verändert. Anpassen (Rot meiden, Routine umlernen) ist ausdrücklich ein späterer, eigener Versuch.

**Abgrenzung zu Ontologic M5:** M5 zeigt, dass ein überraschungsgesteuertes Gate sich neu kalibriert, wenn sich der *Wert eines beachteten* Hinweises ändert. Hier muss das System eine *Dimension wieder öffnen, die es beim Üben selbst geschlossen hat*. Es ändert sich also nicht eine Bewertung, sondern die Ontologie muss wieder wachsen.

**Abgrenzung zu früheren Gittertests (Winkel-Test):** Dort war das kritische Merkmal (Lava) im Training *nie* vorhanden, und jeder Neuheitsdetektor fand es leicht. Hier ist das Merkmal (Bodenfarbe) im Training *vorhanden, variabel und bedeutungslos*. Neuheit hilft deshalb nicht, nur Überraschung im Ergebnis.

---

## 2. Vorgaben (offen erklärt)

Leitlinie: Vorgegeben werden darf allgemeine Struktur und Sinne („der Hunger“), nie die Antwort („das Gegessene“). Die Antwort „Rot ist rutschig“ darf nirgends im System vorkommen.

| Vorgabe | Begründung |
|---|---|
| **Eigenwahrnehmung:** Das System spürt nach jedem Schritt seine tatsächliche Verschiebung. | Ein Sinn, kein Weltwissen. Ohne ihn ist Rutschen nicht bemerkbar. |
| **Zellstruktur (nur Arm B):** Die Welt besteht aus Zellen; der Inhalt der Zelle, die eine Aktion betreten will, kann Folgen haben. | Allgemeines Struktur-Prior, analog zu angeborenem Kernwissen. Arm A misst seinen Wert. |
| **Lehrer für die Nachahmung:** BFS mit vollständiger Karte. | Nur in der Übungsphase, nur für die Routine. Kein Zugriff in der Einsatzphase. |

Nicht vorgegeben: dass Farbe ignoriert werden soll (muss durch Kompression entstehen), das Vorwärtsmodell (wird gelernt), welche Farbe später wichtig wird, welche Veränderung stattfindet.

---

## 3. Welt

- Gitter 9×9. Rand und Felder außerhalb sind Wand.
- Innenwände: jede Innenzelle mit Wahrscheinlichkeit 0,15 Wand (Bedingung „dichtere Wände“: 0,30). Start und Ziel sind freie Zellen mit Manhattan-Abstand ≥ 5; ein Weg muss existieren (sonst neu ziehen).
- Jede Nicht-Wand-Zelle hat genau eine von vier Bodenfarben (Index 0–3), gleichverteilt und unabhängig neu gezogen pro Karte. Farbindex 0 heißt im Code `C_SPECIAL`; das System kennt keine Namen.
- Aktionen: oben, unten, links, rechts. Episodenlänge höchstens 40 Schritte; Ende bei Erreichen des Ziels.
- **Grundrutschen:** Mit Wahrscheinlichkeit `p_slip` = 0,10 wird die gewählte Aktion durch eine gleichverteilt zufällige Aktion ersetzt (die gleiche ist möglich). Ein Schritt in eine Wand lässt das System stehen.
- **Rot-Effekt (nur Bedingung „Rot rutschig“, nur nach dem Wechsel):** Betritt das System nach seinem Schritt eine Zelle mit Farbe `C_SPECIAL`, rutscht es mit Wahrscheinlichkeit 0,5 eine weitere Zelle in dieselbe Richtung, sofern diese frei ist.
- **Beobachtung (roh):** egozentrisches 7×7-Fenster, Kanäle je Zelle: Wand, Ziel, Farbe 0, Farbe 1, Farbe 2, Farbe 3 (one-hot), plus 4 Bit Zielrichtung (Ziel oben/unten/links/rechts). Dimension 6·49 + 4 = 298.
- **Eigenwahrnehmung:** Verschiebung (dr, dc) dieses Schritts als eine von 9 Klassen: (0,0), vier Einheitsschritte, vier Doppelschritte.

---

## 4. Ablauf pro Seed

### Phase 1: Üben (Farbe bedeutungslos, kein Rot-Effekt)
1. **Routine:** Nachahmung des BFS-Lehrers auf 4000 Episoden. Encoder z = tanh(E·x) mit k = 32, Softmax-Policy auf [z, 1]. Gemeinsames Training, Kreuzentropie, Weight Decay 1e-3 auf E, Volltraining (Startwerte: lr 0,5, 1000 Epochen, E-Initialisierung N(0; 0,01)).
2. **Vorwärtsmodell:** Die fertige Routine läuft 1000 Episoden selbst (mit Grundrutschen). Aus ihren Schritten wird ein multinomiales logistisches Modell gelernt: Eingabe [z, one-hot(Aktion), 1], Ausgabe die 9 Verschiebungsklassen, L2-Regularisierung. **Überraschung** eines Schritts: s = −log p(beobachtete Klasse).
3. **Kalibrierung:** 20 Null-Ströme zu je 300 Episoden auf frischen Karten ohne jede Veränderung, die Routine handelt wie im Einsatz. Daraus werden die Schwellen beider Erkennungsverfahren (Abschnitt 5) bestimmt, nach derselben Regel: höchstens 1 von 20 Null-Strömen darf einen Alarm auslösen.

### Phase 2: Voraussetzungen prüfen (P1)
- **Farbinvarianz:** Auf 500 frischen Karten werden die Farben neu gemischt. Die Aktion der Routine muss in mindestens 95 % der Schritte gleich bleiben.
- **Vorwärtsmodell:** Mittlere Überraschung auf frischen Übungskarten muss kleiner sein als die eines Modells, das nur die Klassenhäufigkeiten kennt.
- Scheitert eine Prüfung: Abbruch für diesen Seed, Bericht als „Prämisse nicht erfüllt“. Kein Weiterlaufen.

### Phase 3: Einsatz
- Strom aus 400 Episoden, Wechsel bei Episode 100. Die Routine handelt unverändert. Pro Schritt wandert ein Eintrag in den Ringpuffer (letzte 2000 Schritte): Rohbeobachtung, Aktion, Verschiebungsklasse, Überraschung.
- Vier Bedingungen, je eigener Strom mit denselben Karten:
  - `none`: keine Veränderung.
  - `red`: Rot-Effekt ab Episode 100.
  - `global`: `p_slip` steigt ab Episode 100 auf `p_global`. `p_global` wird pro Seed vor dem Einsatz bestimmt: Auf 300 eigenen Kalibrierungskarten wird mit dem in Phase 1 gelernten Vorwärtsmodell die mittlere Überraschung pro Schritt unter `red`-Bedingungen gemessen (Routine handelt); dann wird `p_global` per Bisektion so gewählt, dass die mittlere Überraschung unter erhöhtem Grundrutschen denselben Wert erreicht (Toleranz 2 %).
  - `walls`: ab Episode 100 Innenwand-Dichte 0,30.
- Das System bekommt die Bedingung nirgends zu sehen. Nur die Umwelt kennt sie.

---

## 5. Mechanismen

Bemerken und Erklären sind getrennt. Erklärt wird erst nach dem Bemerken.

### Mechanismus M3 (Hauptmechanismus, Modellvergleich)
- **Bemerken:** Alle 10 Episoden wird die mittlere Überraschung der letzten 500 Pufferschritte berechnet. Schwelle = kleinster Wert, bei dem höchstens 1 der 20 Null-Ströme (Phase 1) irgendwann überschreitet. Überschreitung = „Veränderung bemerkt“.
- **Erklären:** Ab dem Bemerken alle 10 Episoden, auf dem aktuellen Puffer, 5-fache Kreuzvalidierung (zufällige Teilung, fester Seed):
  - Basismodell: das Vorwärtsmodell mit allen bereits wieder geöffneten Merkmalen.
  - Pro Kandidat ein erweitertes Modell: Basismodell plus dieses eine Merkmal als zusätzliche Eingabe.
  - Basis- und erweitertes Modell werden auf jeder Trainingsteilung gleich neu angepasst (gleiche Regularisierung).
  - **Wieder geöffnet** wird der Kandidat mit der größten mittleren Verbesserung, aber nur, wenn das erweiterte Modell in **allen 5 Teilungen** eine höhere Log-Likelihood auf den zurückgehaltenen Daten hat.
  - Gierig, höchstens 3 wieder geöffnete Merkmale. Ein geöffnetes Merkmal bleibt offen.

### Vergleich S1 (klassische Statistik)
- **Bemerken:** einseitige CUSUM auf der Überraschung pro Schritt. Referenz k = Mittelwert + 0,5 · Standardabweichung der Überraschung in den Null-Strömen; Schwelle h = kleinster Wert, bei dem höchstens 1 der 20 Null-Ströme die Schwelle überschreitet.
- **Erklären:** Nach dem Bemerken, alle 10 Episoden: Für jeden Kandidaten die Differenz der mittleren Überraschung zwischen Merkmal = 1 und Merkmal = 0 im Puffer; Permutationstest mit 1000 Permutationen; Holm-Korrektur bei α = 0,05; höchstens 3 Merkmale, nach p-Wert.

### Kandidaten
- **Arm B (Zellen, Hauptarm):** Inhalt der Zielzelle der von der Routine *gewählten* (nicht der nach Rutschen ausgeführten) Aktion, also der Nachbarzelle in Aktionsrichtung, gelesen aus der Rohbeobachtung vor dem Schritt: Farbe 0, Farbe 1, Farbe 2, Farbe 3, Wand, Ziel. 6 Kandidaten.
- **Arm A (rohe Bits, Kontrolle):** jedes Rohbit i kombiniert mit jeder Aktion a als Merkmal (Bit_i UND Aktion = a). 298 · 4 = 1192 Kandidaten.
- Arm A und B unterscheiden sich **nur** in der Kandidatenmenge. Bemerken ist in beiden Armen identisch.

Daraus ergeben sich 4 Systeme: M3-B (Hauptsystem), M3-A, S1-B, S1-A.

---

## 6. Messung

- **Bemerken:** Latenz in Episoden ab dem Wechsel (nicht bemerkt = zensiert bei 300). Fehlalarm = Bemerken in `none` oder vor Episode 100.
- **Richtige Zuschreibung (`red`):**
  - Arm B: Der Kandidat „Farbe 0 in der Zielzelle“ ist unter den wieder geöffneten Merkmalen.
  - Arm A: Mindestens ein wieder geöffnetes Merkmal ist ein Bit von Kanal „Farbe 0“ in der Nachbarzelle in Richtung der kombinierten Aktion.
  - Latenz der Zuschreibung in Episoden ab dem Wechsel.
- **Fehlzuschreibung:** in `none`, `global`, `walls` jedes wieder geöffnete Farbmerkmal; in `red` jedes wieder geöffnete Merkmal, das nicht zur richtigen Zuschreibung zählt.
- **Kosten:** Puffergröße in Byte; Zahl der Modellanpassungen und deren Größe (Parameter × Stichproben); Wandzeit pro Prüfung und gesamt.
- **Vergleiche:** A gegen B (Wert des Zellen-Priors), M3 gegen S1 (eigener Mechanismus gegen Standardstatistik).

---

## 7. Vorhersagen und Abbruchkriterium

Vor dem Hauptlauf eingefroren. Hauptlauf: Seeds 400–409. Pilot: Seed 0.

- **P1 Prämissen:** In jedem Hauptlauf-Seed Farbinvarianz ≥ 95 % und Vorwärtsmodell besser als Klassenhäufigkeiten. Seeds, die scheitern, werden berichtet und nicht ersetzt.
- **P2:** M3-B schreibt `red` in ≥ 9/10 Seeds korrekt zu.
- **P3:** M3-B öffnet bei `global` in ≥ 9/10 Seeds kein Merkmal.
- **P4:** M3-A ist bei `red` langsamer (Zuschreibungslatenz) oder macht über alle Bedingungen mehr Fehlzuschreibungen als M3-B. Der Abstand wird beziffert.
- **P5:** M3-B erreicht bei `red` mindestens die Trefferquote von S1-B.

**Abbruchkriterium:** M3-B schreibt `red` in weniger als 5/10 Seeds korrekt zu, oder öffnet bei `global` in mehr als 3/10 Seeds ein Merkmal. Dann funktioniert das Wiederöffnen per Modellvergleich in diesem Aufbau nicht, und das wird so berichtet.

Hinweis zu `walls`: Dichtere Wände erzeugen vermutlich wenig Bewegungsüberraschung, weil Wände beachtet werden. Diese Bedingung prüft vor allem, dass keine Farbe beschuldigt wird.

---

## 8. Pilot und Einfrieren

- Der Pilot auf Seed 0 dient der Fehlersuche und der Erfüllung von P1.
- Im Pilot dürfen nur angepasst werden: Trainings-Hyperparameter der Routine und des Vorwärtsmodells, Puffergröße, Prüfintervall. Jede Änderung wird mit Grund im Protokoll festgehalten.
- Danach: `frozen_config.json` schreiben, SHA-256 aller Quelldateien in `freeze.sha256`, erst dann der Hauptlauf. Nach dem Hauptlauf Prüfsummen bestätigen.
- Alles, was nach dem Hauptlauf geändert oder ergänzt wird, ist „nachträgliche Erkundung“, steht getrennt im Bericht und muss auf frischen Seeds bestätigt werden.

---

## 9. Tests (testgetrieben, vor der Implementierung)

- **Welt:** Grundrutschen tritt mit der richtigen Rate auf; der Rot-Effekt wirkt nur in `red` und nur nach dem Wechsel; Doppelschritt nur bei freier Folgezelle; die Eigenwahrnehmung liefert die richtige Klasse.
- **Beobachtung:** Dimension 298; außerhalb des Gitters = Wand; jede Nicht-Wand-Zelle hat genau eine Farbe.
- **Puffer:** Ringverhalten, Länge, Inhalt pro Schritt.
- **Lecktest Zuschreibung:** Werden die Werte eines Kandidaten im Puffer zufällig zeilenweise vertauscht, wird er nie wieder geöffnet (Prüfung auf `red`-Daten).
- **Isolation:** Agent, Routine, Vorwärtsmodell und Monitor haben keinen Zugriff auf Bedingung, Wechselzeitpunkt oder `C_SPECIAL`.
- **Determinismus:** Gleicher Seed ergibt identische Ergebnisse.

---

## 10. Vorgeschlagener Aufbau

Python 3, nur numpy (plus pytest für Tests).

```
farbversuch/
  world.py      # Karte, Schritt, Rutschen, Rot-Effekt, Beobachtung, Eigenwahrnehmung
  routine.py    # Lehrer-Daten, Encoder + Policy, Training
  forward.py    # Vorwärtsmodell, Überraschung, erweiterte Modelle
  monitor.py    # Puffer, Bemerken (M3, S1), Erklären (M3, S1), Kandidaten A/B
  run.py        # Phasen pro Seed, Bedingungen, Ergebnis-JSON
  analyze.py    # Kennzahlen, Vorhersagen P1–P5, Abbruchkriterium
  tests/
  PROTOKOLL.md  frozen_config.json  freeze.sha256  BERICHT.md
```

---

## 11. Bericht

Feste Gliederung:
1. Frage und Aufbau (kurz)
2. **Beobachtet:** Zahlen, Vorhersagen P1–P5 jeweils erfüllt oder nicht erfüllt, Abbruchkriterium
3. **Deutung (Annahme):** getrennt, ausdrücklich als Annahme gekennzeichnet
4. Grenzen
5. Pilot-Änderungen und nachträgliche Erkundungen

Sprachregel: Wörter wie „bestätigt“, „bewiesen“, „aus ersten Prinzipien“ nur, wenn die vorab festgelegte Vorhersage tatsächlich erfüllt ist. Keine Verallgemeinerung über diese Welt hinaus ohne Kennzeichnung als Annahme.

---

## 12. Nicht Teil dieser Version

Anpassen der Routine; Evolution oder NEAT; Aussagen über Zeitgewinn; Ansatz 2 (Ontologic-Präzisionsgate) als Mechanismus. Ansatz 2 wird erst geprüft, wenn das Wiederöffnen überhaupt funktioniert.
