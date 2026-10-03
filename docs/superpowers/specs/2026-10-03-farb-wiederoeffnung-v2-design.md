# Spezifikation v2: Wiederöffnen einer ignorierten Dimension („Farbversuch“)

Stand: 03.10.2026 · Status: Entwurf zur Freigabe · Umsetzung: Claude Code
Ersetzt: `docs/superpowers/specs/2026-10-03-farb-wiederoeffnung-design.md` (v1). Änderungen gegenüber v1 und ihre Gründe stehen in Anhang A.

Diese Spezifikation ist eigenständig. Sie setzt den Code der v1-Umsetzung als Ausgangspunkt voraus und beschreibt den Zielzustand.

---

## 1. Frage, Begriffe und Abgrenzung

**Frage:** Kann ein System lernen, welche Information es bei einer Routine ignorieren darf, und erkennen, wann diese Vereinfachung nicht mehr reicht?

**Umfang dieser Version:** nur **Bemerken** und **Erklären**. Die Routine wird nach dem Üben nicht verändert. Anpassen ist ein späterer, eigener Versuch.

**Begriffe:**
- **Übungs-Ontologie** eines Systems: die Merkmale, die das System schon in der Übungsphase mit seinem eigenen Erklärverfahren als nötig erkennt (§4, Phase 1, Schritt 3). Sie gehören zum geübten Modell und gelten nicht als „wieder geöffnet“.
- **Geschlossen:** Eine Dimension ist *weitgehend geschlossen*, wenn die Routine sich unabhängig von ihr verhält (P1) und ihre interne Darstellung z nur einen kleinen, gemessenen Rest der Information trägt (P1b). „Vollständig geschlossen“ wird nicht behauptet.
- **Wieder geöffnet:** ein Merkmal, das im Einsatz über die Übungs-Ontologie hinaus geöffnet wird.

**Abgrenzung zu Ontologic M5:** M5 zeigt, dass ein überraschungsgesteuertes Gate sich neu kalibriert, wenn sich der *Wert eines beachteten* Hinweises ändert. Hier muss das System eine *Dimension wieder öffnen, die es beim Üben selbst geschlossen hat*.

**Abgrenzung zu früheren Gittertests (Winkel-Test):** Dort war das kritische Merkmal im Training nie vorhanden. Hier ist die Bodenfarbe im Training *vorhanden, variabel und bedeutungslos*. Neuheit hilft nicht, nur Überraschung im Ergebnis.

---

## 2. Vorgaben (offen erklärt)

Leitlinie: Vorgegeben werden darf allgemeine Struktur und Sinne, nie die Antwort. „Rot ist rutschig“ darf nirgends im System vorkommen.

| Vorgabe | Begründung |
|---|---|
| **Eigenwahrnehmung:** Das System spürt nach jedem Schritt seine tatsächliche Verschiebung. | Ein Sinn, kein Weltwissen. |
| **Zellstruktur (nur Arm B):** Der Inhalt der Zelle, die eine Aktion betreten will, kann Folgen haben. | Allgemeines Struktur-Prior. Arm A misst seinen Wert. |
| **Lehrer für die Nachahmung:** BFS mit vollständiger Karte. | Nur in der Übungsphase, nur für die Routine. |

Nicht vorgegeben: dass Farbe ignoriert werden soll, das Vorwärtsmodell, die Übungs-Ontologie (wird gelernt), welche Farbe später wichtig wird, welche Veränderung stattfindet.

---

## 3. Welt

Unverändert gegenüber v1:
- Gitter 9×9, Rand und Felder außerhalb sind Wand. Innenwände mit Wahrscheinlichkeit 0,15 (Bedingung „dichtere Wände“: 0,30). Start und Ziel frei, Manhattan-Abstand ≥ 5, ein Weg existiert (sonst neu ziehen). Jede Episode eine neue Karte.
- Jede Nicht-Wand-Zelle hat eine von vier Bodenfarben (Index 0–3), gleichverteilt und unabhängig pro Karte. Farbindex 0 heißt im Code `C_SPECIAL`; das System kennt keine Namen.
- Aktionen oben, unten, links, rechts. Höchstens 40 Schritte pro Episode; Ende beim Erreichen des Ziels (geprüft auf der Endposition).
- **Grundrutschen:** Mit `p_slip` = 0,10 wird die gewählte Aktion durch eine gleichverteilt zufällige ersetzt. Ein Schritt in eine Wand lässt das System stehen.
- **Rot-Effekt** (nur Bedingung `red`, nur nach dem Wechsel): Betritt das System eine Zelle mit Farbe `C_SPECIAL`, rutscht es mit Wahrscheinlichkeit 0,5 eine weitere Zelle in dieselbe Richtung, sofern frei.
- **Beobachtung:** egozentrisches 7×7-Fenster, je Zelle Wand, Ziel, Farbe 0–3 (one-hot), plus 4 Bit Zielrichtung; Dimension 298.
- **Eigenwahrnehmung:** Verschiebung als eine von 9 Klassen.

---

## 4. Ablauf pro Seed

### Phase 1: Üben
1. **Routine:** Nachahmung des BFS-Lehrers auf 4000 Episoden. Encoder z = tanh(E·x), k = 32, Softmax-Policy auf [z, 1], Kreuzentropie, Weight Decay 1e-3 auf E, Volltraining (lr 0,5, 1000 Epochen, E ~ N(0; Standardabweichung 0,01)). Die Routine handelt deterministisch (argmax).
2. **Vorwärtsmodell:** Die Routine läuft 1000 Episoden mit Grundrutschen. Multinomiales logistisches Modell auf [z, one-hot(Aktion), 1] für die 9 Verschiebungsklassen, L2 auf allen Gewichten. **Überraschung** s = −log p(beobachtete Klasse). Dieses Modell liefert die Überraschung für das Bemerken; es ist für alle Systeme gleich und wird danach nicht verändert.
3. **Übungs-Ontologie (neu):** Übungspuffer = die letzten 2000 Schritte der Vorwärtsdaten aus Schritt 2. Jedes der vier Systeme öffnet darauf mit seinem eigenen Erklärverfahren (§5) greedy Merkmale vor, höchstens 8:
   - M3-Systeme: Regel aus §5, aber mit fester Mindestverbesserung δ_Übung = 0,01 nats pro Schritt statt δ.
   - S1-Systeme: Holm-Ablehnungen des eigenen Permutationstests (§5), in p-Reihenfolge.
   Ergebnis: Übungs-Ontologie O je System. Sie geht in das Basismodell des Erklärens ein, nicht in die Überraschung.
4. **Kalibrierung:** 20 Null-Ströme zu je **400 Episoden** auf frischen Karten ohne Veränderung, die Routine handelt wie im Einsatz.
   - Schwellen für das Bemerken (M3 und CUSUM): **größter** der 20 Null-Strom-Maxima. Erwartete Fehlalarmrate pro neuem Strom ≈ 1/21 ≈ 4,8 %.
   - **Mindestverbesserung δ (neu, je M3-System):** Auf den letzten 2000 Schritten jedes Null-Stroms läuft eine Erklärrunde mit Basis = Vorwärtsmodell + O. Notiert wird die größte mittlere Verbesserung unter den Kandidaten, die in allen 5 Teilungen positiv sind (0, wenn keiner). δ = größter der 20 Werte.

### Phase 2: Voraussetzungen prüfen
- **P1 Farbinvarianz:** Auf 500 frischen Karten werden die Farben neu gezogen; die Aktion der Routine bleibt in ≥ 95 % der Schritte gleich.
- **P1 Vorwärtsmodell:** Mittlere Überraschung auf frischen Übungskarten kleiner als bei einem Modell, das nur die Klassenhäufigkeiten kennt.
- **P1b Geschlossenheit (neu):**
  - **Restanteil ≤ 15 %:** Auf dem Übungspuffer wird für jede der 4 Nachbarzellen eine multinomiale logistische Probe trainiert, die die Farbe (nur freie Zellen) aus z vorhersagt; 5-fache Kreuzvalidierung mit Teilung nach Episoden. Dieselbe Probe auf der Rohbeobachtung dient als Referenz. Restanteil = (Treffer aus z − Mehrheitsbasis) / (Treffer aus Rohbeobachtung − Mehrheitsbasis), gemittelt über die 4 Zellen.
  - **Verschiebung ≤ 25 %:** An 500 Positionen aus den Invarianzkarten: mittleres ‖z(x) − z(x mit neu gezogenen Farben)‖ geteilt durch mittleres ‖z(x)‖.
- Scheitert eine Prüfung: Abbruch für diesen Seed, Bericht als „Prämisse nicht erfüllt“.

### Phase 3: Einsatz
Unverändert gegenüber v1: Strom aus 400 Episoden, Wechsel bei Episode 100, Routine handelt unverändert, Ringpuffer der letzten 2000 Schritte (Rohbeobachtung, gewählte Aktion, Verschiebungsklasse, Überraschung). Vier Bedingungen auf denselben Karten: `none`, `red`, `global` (`p_slip` steigt auf `p_global`, per Bisektion so bestimmt, dass die mittlere Überraschung der unter `red` entspricht, Toleranz 2 %), `walls` (Innenwanddichte 0,30). Das System bekommt die Bedingung nirgends zu sehen.

---

## 5. Mechanismen

Bemerken und Erklären sind getrennt. Erklärt wird erst nach dem Bemerken. Geprüft wird alle 10 Episoden.

### M3 (Hauptmechanismus, Modellvergleich)
- **Bemerken:** Mittlere Überraschung der letzten 500 Pufferschritte > Schwelle (§4).
- **Erklären:** Ab dem Bemerken bei jeder Prüfung, auf dem aktuellen Puffer, 5-fache Kreuzvalidierung mit zufälliger Teilung nach Zeilen (fester Seed):
  - **Basismodell:** Vorwärtsmodell-Eingaben + Übungs-Ontologie O + bereits wieder geöffnete Merkmale; auf jeder Trainingsteilung neu angepasst.
  - **Residualisieren (neu):** Jede Kandidatenspalte wird auf der Trainingsteilung per kleinsten Quadraten gegen das Basisdesign regressiert; als zusätzliche Eingabe dient der Rest (mit den Trainingskoeffizienten auch auf die Testteilung angewandt). Ist der Rest auf der Trainingsteilung praktisch null (Norm < 1e-8 × Norm der Spalte), ist die Verbesserung genau 0, ohne Anpassung. Duplikate und lineare Kombinationen vorhandener Spalten können so nichts gewinnen.
  - **Erweitertes Modell:** Basismodell plus der residualisierte Kandidat, gleich angepasst (gleiche Regularisierung).
  - **Wieder geöffnet** wird der Kandidat mit der größten mittleren Verbesserung, nur wenn die Verbesserung in **allen 5 Teilungen** positiv ist **und** ihr Mittel **größer als δ** ist (neu).
  - Gierig, höchstens ein Merkmal pro Prüfung, höchstens 3 wieder geöffnete Merkmale über O hinaus. Ein geöffnetes Merkmal bleibt offen. Merkmale aus O werden nicht erneut getestet.

### S1 (Vergleich, klassische Statistik)
- **Bemerken:** einseitige CUSUM auf der Überraschung pro Schritt; Referenz k = Mittelwert + 0,5 · Standardabweichung der Null-Überraschung; Schwelle h = größter der 20 Null-Strom-Maxima.
- **Erklären:** Nach dem Bemerken bei jeder Prüfung: je Kandidat die Differenz der mittleren Überraschung zwischen Merkmal = 1 und Merkmal = 0; einseitiger Permutationstest; Holm-Korrektur bei α = 0,05 über alle noch nicht geöffneten Kandidaten außerhalb von O; höchstens 3 Merkmale über O hinaus, nach p-Wert.
- **Permutationen (neu):** Arm B 1000, Arm A 25.000 (damit Holm bei 1192 Kandidaten ablehnen kann: 0,05/1192 > 1/25.001).

### Kandidaten
- **Arm B (Zellen):** Inhalt der Zielzelle der *gewählten* Aktion, gelesen aus der Rohbeobachtung vor dem Schritt: Farbe 0–3, Wand, Ziel. 6 Kandidaten.
- **Arm A (rohe Bits):** jedes Rohbit i mit jeder Aktion a (Bit_i UND Aktion = a). 1192 Kandidaten.
- Arm A und B unterscheiden sich **nur** in der Kandidatenmenge.

Daraus ergeben sich 4 Systeme: M3-B (Hauptsystem), M3-A, S1-B, S1-A. Jedes hat seine eigene Übungs-Ontologie.

---

## 6. Messung

- **Bemerken:** Latenz in Episoden ab dem Wechsel (nicht bemerkt = zensiert bei 300). Fehlalarm = Bemerken in `none` oder vor Episode 100.
- **Geöffnet** heißt in allen Kennzahlen: über die Übungs-Ontologie hinaus.
- **Richtige Zuschreibung (`red`):** Arm B: „Farbe 0 in der Zielzelle“ wird geöffnet. Arm A: ein Bit von Kanal „Farbe 0“ in der Nachbarzelle in Richtung der kombinierten Aktion wird geöffnet. Nur Öffnungen **nach** dem Wechsel (Prüfung bei Episode > 100) zählen; Latenz = Episode − 100.
- **Fehlzuschreibung:** in `none`, `global`, `walls` jedes geöffnete Farbmerkmal; in `red` jede Öffnung, die nicht als richtige Zuschreibung zählt (auch eine Farbe-0-Öffnung vor dem Wechsel).
- **Zusätzlich je Seed und System berichtet:** Übungs-Ontologie O, δ, P1b-Werte (Restanteil, Verschiebung), Nutzbarkeit (mittlere Verbesserung von „Farbe 0“ bei ihrer Öffnung unter `red`).
- **Kosten:** Puffergröße in Byte; Zahl und Größe der Modellanpassungen; Wandzeit pro Prüfung und gesamt.
- **Vergleiche:** A gegen B, M3 gegen S1.

---

## 7. Vorhersagen und Abbruchkriterium

Vor dem Hauptlauf eingefroren. Hauptlauf: Seeds 400–409.

- **P1 Prämissen:** In jedem Hauptlauf-Seed P1 und P1b erfüllt. Seeds, die scheitern, werden berichtet und nicht ersetzt; sie zählen bei P2, P3 und beim Abbruchkriterium gegen M3-B.
- **P2:** M3-B schreibt `red` in ≥ 9/10 Seeds korrekt zu.
- **P3:** M3-B öffnet bei `global` in ≥ 9/10 Seeds kein Merkmal.
- **P4:** M3-A ist bei `red` langsamer (Zuschreibungslatenz) oder macht über alle Bedingungen mehr Fehlzuschreibungen als M3-B. Der Abstand wird beziffert.
- **P5:** M3-B erreicht bei `red` mindestens die Trefferquote von S1-B.

**Abbruchkriterium:** M3-B schreibt `red` in weniger als 5/10 Seeds korrekt zu, oder öffnet bei `global` in mehr als 3/10 Seeds ein Merkmal.

Urteile zu P2–P5 und zum Abbruch werden nur für genau die Seeds 400–409 ausgegeben; jede andere Seedmenge wird als explorativ gekennzeichnet.

---

## 8. Pilot, Bestätigung und Einfrieren

1. **Pilot auf Seed 0:** Fehlersuche und Erfüllung von P1/P1b. Anpassen dürfen sich nur: Trainings-Hyperparameter der Routine und des Vorwärtsmodells, Puffergröße, Prüfintervall. Jede Änderung mit Grund im Protokoll.
2. **Bestätigung auf Seeds 500–504 (neu):** volle Pipeline mit der Pilot-Konfiguration, explorativ ausgewertet. Vorab festgelegt gilt die Methode als bestätigt, wenn in **mindestens 4 von 5** Seeds jeweils gilt:
   - P1 und P1b erfüllt;
   - M3-B öffnet bei `none` und bei `global` nichts über O hinaus;
   - M3-B öffnet bei `red` „Farbe 0“ nach dem Wechsel.
   Laufzeiten werden berichtet.
3. **Nicht bestätigt:** Ergebnis zurück an den Nutzer. Eine weitere Runde läuft nur auf neuen Seeds (510–514 usw.); verbrauchte Seeds werden nie wiederverwendet.
4. **Bestätigt:** Der Nutzer entscheidet, ob zusätzlich Seeds 505–509 laufen. Danach `frozen_config.json`, SHA-256 aller Quelldateien in `freeze.sha256`, dann der Hauptlauf. Nach dem Hauptlauf Prüfsummen bestätigen.
5. Pilot und Bestätigung laufen jeweils komplett auf derselben Maschine; ebenso der Hauptlauf.
6. Alles, was nach dem Hauptlauf geändert oder ergänzt wird, ist „nachträgliche Erkundung“, steht getrennt im Bericht und muss auf frischen Seeds bestätigt werden.

---

## 9. Tests (testgetrieben)

Alle Tests aus v1 bleiben. Neu:
- **Residualisieren:** Ein Duplikat einer Basisspalte und eine lineare Kombination von Basisspalten ergeben Verbesserung genau 0 ohne Anpassung; ein echtes Signal wird weiterhin geöffnet.
- **Duplikat-Kontrolle:** Drei identische Kopien einer Kandidatenspalte werden nie mehr als einmal geöffnet; eine Kopie einer Spalte aus Basis oder O wird nie geöffnet.
- **Mindestverbesserung:** Ein Kandidat, der in allen Teilungen positiv ist, aber im Mittel ≤ δ liegt, wird nicht geöffnet.
- **Übungs-Ontologie:** deterministisch, höchstens 8 Merkmale, Merkmale aus O werden im Einsatz nicht erneut getestet und zählen nicht als geöffnet.
- **Kalibrierung:** Alle Schwellen und δ sind der größte der 20 Null-Werte; Null-Ströme haben 400 Episoden.
- **P1b:** Restanteil und Verschiebung auf konstruierten Fällen (farbblinde Darstellung → Restanteil ≈ 0; Darstellung, die Farben kopiert → Restanteil ≈ 1).
- **S1-A:** Blockweise Berechnung der Permutationen liefert dieselben p-Werte wie eine Berechnung am Stück.

---

## 10. Aufbau

Python 3, nur numpy (plus pytest). Bestehende Module der v1-Umsetzung (`world`, `routine`, `forward`, `monitor`, `run`, `analyze`, `freeze`, `config`, `seeds`) werden erweitert; neue Logik bekommt eigene, kleine Funktionen. Läufe werden über Seeds **und** Bedingungen parallelisiert, damit Maschinen mit vielen Kernen ausgelastet sind. Jede Ergebnisdatei enthält O, δ, P1b-Werte und die Umgebung (Threads, numpy, BLAS).

---

## 11. Bericht

Feste Gliederung:
1. Frage und Aufbau (kurz)
2. **Beobachtet:** Zahlen, P1/P1b, Vorhersagen P2–P5 jeweils erfüllt oder nicht erfüllt, Abbruchkriterium; Übungs-Ontologien je System; erwartete Fehlalarmrate (≈ 4,8 % pro Strom)
3. **Deutung (Annahme):** getrennt, ausdrücklich als Annahme gekennzeichnet
4. Grenzen, mindestens: Abhängigkeit der Zeilen innerhalb von Episoden (Kreuzvalidierung und Permutationen nach Zeilen); „weitgehend geschlossen“ statt „vollständig“; δ_Übung = 0,01 fest gewählt
5. Pilot-Änderungen, Bestätigungslauf (500–504, ggf. 505–509) und nachträgliche Erkundungen, jeweils getrennt; die explorative Diagnose auf Seed 0 als Hintergrund

Sprachregel: „bestätigt“, „bewiesen“, „aus ersten Prinzipien“ nur bei tatsächlich erfüllter Vorhersage. Keine Verallgemeinerung über diese Welt hinaus ohne Kennzeichnung als Annahme.

---

## 12. Nicht Teil dieser Version

Anpassen der Routine; Evolution oder NEAT; Aussagen über Zeitgewinn; Ontologic-Präzisionsgate als Mechanismus.

---

## Anhang A: Änderungen gegenüber v1 und Gründe

Grundlage ist eine explorative Diagnose auf Seed 0 (nicht Teil der Vorhersagen) und zwei unabhängige Gegenprüfungen des Codes.

| Änderung | Grund (beobachtet auf Seed 0) |
|---|---|
| Übungs-Ontologie (Vor-Öffnen in Phase 1) | z kennt Wände nur teilweise (Probe 0,85 gegenüber 1,00 roh). M3-B öffnete „Wand“ auch ohne Weltänderung (+0,115 nats/Schritt), unter allen fünf geprüften Gegenmaßnahmen. Mit Vor-Öffnen und Residualisieren: nichts geöffnet auf 11/11 Puffern ohne Änderung, Farbe 0 auf 17/17 Rot-Puffern. |
| Residualisieren | Drei identische Kandidatenspalten konnten über die L2-Strafe nacheinander geöffnet werden; nur Residualisieren setzt solche Gewinne exakt auf 0. |
| Mindestverbesserung δ | Ohne Schwelle späte, kleine Zusatzöffnungen (+0,0008 bis +0,0027) gegenüber echten Farbe-0-Öffnungen (+0,008 bis +0,020). |
| Größter statt zweitgrößter Null-Wert, Null-Ströme 400 Episoden | Zweitgrößter von 20 ergibt ≈ 9,5 % Fehlalarme pro neuem Strom statt der gemeinten ≈ 5 %; Null-Ströme waren kürzer als der Einsatz. |
| P1b Geschlossenheit | P1 prüft nur Verhalten; eine farbinvariante Routine kann Farbe intern vollständig speichern. Auf Seed 0: Restanteil ≈ 7 %, Verschiebung ≈ 15 %. |
| S1 mit Übungs-Ontologie, S1-A 25.000 Permutationen | Faire Behandlung beider Verfahren; mit 1000 Permutationen konnte S1-A strukturell nie ablehnen. |
| Zuschreibung nur nach dem Wechsel | Vor dem Wechsel sind alle vier Ströme identisch; eine frühere Öffnung kann den Wechsel nicht erkannt haben. |
| Bestätigung auf Seeds 500–504 | Die neuen Regeln wurden auf einem einzigen Seed entworfen. |
| Kreuzvalidierung bleibt nach Zeilen | Teilung nach Episoden brachte in der Diagnose mehr Fehlöffnungen (2/5 gegenüber 0/5 bei `global`) und weniger Trennschärfe; δ wird mit derselben Teilung kalibriert. Abhängigkeit wird als Grenze berichtet. |
