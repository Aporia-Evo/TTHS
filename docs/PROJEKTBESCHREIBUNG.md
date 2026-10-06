# Farbversuch – Projektbeschreibung (Stand 06.10.2026: v2, Hauptlauf abgeschlossen)

Bindend sind die Spezifikation v2 (`docs/superpowers/specs/2026-10-03-farb-wiederoeffnung-v2-design.md`) und der Plan v2 (`docs/superpowers/plans/2026-10-03-farb-wiederoeffnung-v2.md`). Die Dokumente der Version 1 (`…-farb-wiederoeffnung-design.md`, `…-farb-wiederoeffnung.md`) sind Geschichte. Anhang A der Spec v2 nennt, was sich gegenüber v1 geändert hat und warum. Der Plan v2 verweist für alles, was er nicht neu regelt, auf die Festlegungen des v1-Plans. Anhang B der Spec v2 ist ein datierter Review-Nachtrag vom 05.10.2026. Er präzisiert Kalibrierung, Grenzen und Auswertung und ändert keine Regel.

## Frage

Kann ein System lernen, welche Information es bei einer Routine ignorieren darf, und erkennen, wann diese Vereinfachung nicht mehr reicht?

Diese Version prüft nur **Bemerken** und **Erklären**. Die Routine wird nach dem Üben nicht mehr verändert. Umlernen ist ein späterer, eigener Versuch.

## Idee in einem Absatz

Ein Agent lernt in einer kleinen Gitterwelt, zum Ziel zu laufen. Der Boden hat vier Farben, die beim Üben nichts bedeuten. Die Routine lernt deshalb, Farbe zu ignorieren. Später wird eine Farbe (intern `C_SPECIAL`) rutschig: Wer sie betritt, rutscht mit 50 % eine Zelle weiter. Das System soll das allein bemerken (Überraschung in seiner Eigenwahrnehmung steigt) und erklären (die geschlossene Dimension „Bodenfarbe der Zielzelle“ wieder öffnen). Neuheit hilft dabei nicht, denn Farbe war im Training schon da, nur bedeutungslos.

## Aufbau

- **Welt:** 9×9-Gitter, Innenwände mit 15 %, vier Bodenfarben, 10 % Grundrutschen, höchstens 40 Schritte pro Episode. Beobachtung: egozentrisches 7×7-Fenster mit 298 Bits. Eigenwahrnehmung: tatsächliche Verschiebung als eine von 9 Klassen.
- **Routine:** imitiert einen BFS-Lehrer, Encoder z = tanh(E·x) mit k = 32, Softmax-Policy, handelt deterministisch. Die Trainingsparameter der Pilot-Konfiguration stehen in `farbversuch/pilot_config.json`: 8000 Lehrer-Episoden, lr 0,1535, 500 Epochen, wd 0,0203, init_std 0,00772. Ermittelt wurden sie über Pilot und Evolution auf Entwicklungs-Seeds, siehe `farbversuch/PROTOKOLL.md`.
- **Vorwärtsmodell:** multinomiale logistische Regression auf [z, Aktion, 1], sagt die Verschiebung vorher. Überraschung = −log p. Es liefert die Überraschung für das Bemerken, für alle Systeme gleich.
- **Übungs-Ontologie (neu in v2):** Jedes System öffnet am Ende der Übungsphase auf den letzten 2000 Schritten der Vorwärtsdaten mit seinem eigenen Erklärverfahren bis zu 8 Merkmale vor (M3: feste Mindestverbesserung 0,01 nats pro Schritt; S1: Holm-Ablehnungen). Diese Merkmale gehören zum geübten Modell. Sie gehen in das Basismodell des Erklärens ein, werden im Einsatz nie erneut getestet und zählen nie als „wieder geöffnet“. Sie wirken nur auf das Erklären, nicht auf das Bemerken.
- **Kalibrierung:** 20 Null-Ströme zu je 400 Episoden.
  - **Bemerken:** Die Schwellen von M3 und CUSUM sind über die ganzen Null-Ströme kalibriert; Schwelle ist der größte der 20 Null-Werte. Erwartete Fehlalarmrate des Bemerkens pro neuem Strom ≈ 1/21 ≈ 4,8 %.
  - **Mindestverbesserung δ** (je M3-System): größter der 20 Null-Gewinne. Jeder Null-Gewinn stammt aus einem einzigen Endpuffer des Null-Stroms (letzte `buffer_size` Schritte). Er ist die größte mittlere Verbesserung unter den Kandidaten, die in allen 5 Teilungen positiv sind, sonst 0. δ = 0 ist damit regelgemäß möglich.
  - **Keine Gesamtrate:** Eine Gesamtrate falscher Öffnungen über einen Einsatz folgt aus beidem nicht, denn erklärt wird wiederholt, und Holm gilt je Erklärrunde.
- **Einsatz:** 400 Episoden, Wechsel bei Episode 100, vier Bedingungen auf denselben Karten:
  - `none`: keine Änderung
  - `red`: die Farbe wird rutschig
  - `global`: mehr Grundrutschen, mit gleicher mittlerer Überraschung wie `red`
  - `walls`: dichtere Wände
- **Vier Systeme:**

  | System | Bemerken | Erklären | Kandidaten |
  |---|---|---|---|
  | M3-B (Hauptsystem) | Mittel der Überraschung über 500 Schritte | Kreuzvalidierter Modellvergleich (5 Teilungen). Kandidaten werden gegen das Basisdesign residualisiert. Geöffnet wird bei Verbesserung in allen Teilungen und Mittel > δ. | 6 Zellmerkmale der Zielzelle |
  | M3-A | wie M3-B | wie M3-B | 1192 Rohbit×Aktion-Merkmale |
  | S1-B | CUSUM | Permutationstest (1000 Permutationen) + Holm | wie M3-B |
  | S1-A | CUSUM | Permutationstest (25.000 Permutationen, blockweise zu 1000) + Holm | wie M3-A |

  Im Einsatz sind höchstens 3 Merkmale über die Übungs-Ontologie hinaus offen.

## Voraussetzungen („weitgehend geschlossen“)

Pro Seed werden direkt nach dem Training von Routine und Vorwärtsmodell geprüft, noch vor Übungs-Ontologie und Kalibrierung, denn die Prüfungen hängen von beiden nicht ab. Scheitert eine Prüfung, entfällt der Seed als „Prämisse nicht erfüllt“; Übungs-Ontologie, Kalibrierung, δ und Einsatz werden dann nicht mehr berechnet (Entscheidung des Nutzers vom 04.10.2026):

- **P1:** Die Routine behält ihre Aktion in ≥ 95 % der Schritte, wenn die Farben neu gezogen werden. Das Vorwärtsmodell ist besser als ein Modell nur mit Klassenhäufigkeiten.
- **P1b (neu):** Die interne Darstellung z trägt nur einen kleinen Rest der Farbinformation.
  - Restanteil ≤ 0,15. Für jede der vier Nachbarzellen sagt eine multinomiale logistische Probe die Farbe vorher (nur Zeilen, in denen die Zelle frei ist; 5-fache Kreuzvalidierung mit Teilung nach Episoden), einmal aus z und einmal aus der Rohbeobachtung. Mehrheitsbasis ist die häufigste Farbe der Trainingsteilung. Restanteil = (Trefferquote aus z − Mehrheitsbasis) / (Trefferquote aus Rohbeobachtung − Mehrheitsbasis), über die Zellen gemittelt. Eine Zelle mit weniger als 20 freien Zeilen oder mit (Roh − Mehrheit) ≤ 0,05 wird ausgelassen. Bleibt keine Zelle übrig, ist der Restanteil `nan` und die Prämisse nicht erfüllt.
  - Verschiebung ≤ 0,25: mittleres ‖z − z′‖ geteilt durch mittleres ‖z‖ bei neu gezogenen Farben, über 500 Positionen.

„Vollständig geschlossen“ wird nicht behauptet. P1 und P1b operationalisieren „weitgehend ignoriert“.
- **Restanteil:** Er ist kein Informationsprozentsatz.
- **Negative Werte:** Die Probe aus z ist schlechter als die Mehrheitsbasis.

## Vorab festgelegte Vorhersagen (Hauptlauf Seeds 400–409)

- **P1:** Prämissen (P1 und P1b) in jedem Hauptlauf-Seed erfüllt. Gescheiterte Seeds werden berichtet, nicht ersetzt und zählen bei P2, P3 und beim Abbruchkriterium gegen M3-B.
- **P2:** M3-B schreibt `red` in ≥ 9/10 Seeds korrekt zu. Richtig heißt: „Farbe 0“ wird nach dem Wechsel geöffnet.
- **P3:** M3-B öffnet bei `global` in ≥ 9/10 Seeds kein Merkmal.
- **P4:** M3-A ist bei `red` langsamer oder macht insgesamt mehr Fehlzuschreibungen als M3-B. Der Abstand wird beziffert.
- **P5:** M3-B trifft bei `red` mindestens so oft wie S1-B.
- **Abbruch:** < 5/10 korrekt bei `red` oder > 3/10 Öffnungen bei `global`.

Auswertungsregeln (Spec v2 §6/§7, unverändert, in Anhang B ausdrücklich festgehalten):
- **P2:** Zusätzliche Öffnungen im selben Strom heben die richtige Zuschreibung nicht auf. Sie zählen als Fehlzuschreibungen.
- **P4:** Die Zuschreibungslatenz ist bei Nichttreffern am Horizont 300 zensiert. Fehlzuschreibung heißt außerhalb von `red` nur „Farbmerkmal geöffnet“; unter `red` jede Öffnung, die keine richtige Zuschreibung ist.
- **P5:** vergleicht Trefferquoten, nicht die Präzision aller Öffnungen.
- **Seeds:** Der Hauptlauf läuft ausschließlich auf den Seeds 400–409. Gescheiterte Prämissen werden nicht ersetzt.

Urteile zu P2–P5 und zum Abbruch gibt die Auswertung nur für genau die Seeds 400–409 aus. Jede andere Seedmenge ist explorativ.

## Vorgehen

Pilot → Bestätigung → Entscheidung des Nutzers → Einfrieren → Hauptlauf → Bericht.

1. **Pilot auf Seed 0:** Fehlersuche und Erfüllung von P1 und P1b.
   - Anpassen dürfen sich nur Trainings-Hyperparameter der Routine und des Vorwärtsmodells, Puffergröße und Prüfintervall.
   - Jede Änderung steht mit Grund in `farbversuch/PROTOKOLL.md`. Die Pilot-Konfiguration liegt in `farbversuch/pilot_config.json`.
2. **Bestätigung:** volle Pipeline mit der Pilot-Konfiguration, explorativ ausgewertet.
   - **Regel:** Die Methode gilt als bestätigt, wenn es mindestens 4 von 5 Seeds gibt, in denen alle drei Bedingungen gleichzeitig gelten:
     - P1 und P1b sind erfüllt;
     - M3-B öffnet bei `none` und `global` nichts über die Übungs-Ontologie hinaus;
     - M3-B öffnet bei `red` „Farbe 0“ nach dem Wechsel.
   - Dass jede Bedingung für sich in 4 von 5 Seeds gilt, genügt nicht (Präzisierung der Spec v2 §8, Entscheidung des Nutzers vom 04.10.2026).
   - **Nicht bestätigt:** Ergebnis zurück an den Nutzer. Eine weitere Runde läuft nur auf neuen Seeds.
3. **Entscheidung des Nutzers:** Bei Bestätigung entscheidet der Nutzer, ob weitere Bestätigungs-Seeds laufen.
4. **Einfrieren:** `frozen_config.json` und SHA-256 aller Quelldateien in `freeze.sha256`. Dazu wird die Umgebung samt Fingerabdruck im Protokoll festgehalten.
5. **Hauptlauf** ausschließlich auf den Seeds 400–409, ohne Ersatz gescheiterter Prämissen. Danach Prüfsummen bestätigen und auswerten.
6. **Bericht** mit fester Gliederung (Spec v2 §11). Beobachtung und Deutung stehen getrennt. Was nach dem Hauptlauf geändert oder ergänzt wird, ist „nachträgliche Erkundung“ und muss auf frischen Seeds bestätigt werden.

Pilot, Bestätigung und Hauptlauf laufen jeweils komplett auf derselben Maschine.

## Stand der Läufe (05.10.2026)

Zahlen aus Pilot und Bestätigungsläufen sind explorativ. Die vorab festgelegten Vorhersagen wurden ausschließlich im Hauptlauf geprüft (letzter Punkt). Einzelheiten und alle Änderungen mit Begründung stehen in `farbversuch/PROTOKOLL.md`.

- **Pilot Seed 0:** Mit den Standardwerten scheitert P1 (Farbinvarianz 0,926). Mit `wd` 0,01 ist die Prämisse erfüllt.
- **Bestätigung 500–504 (wd 0,01):** nicht bestätigt, die Prämisse hält nur in 2/5 Seeds.
- **Entwicklung auf den Seeds 0 und 500–504:**
  - **Raster:** 4 Varianten.
  - **Evolution:** 34 Kandidaten über die Trainingsparameter der Routine.
  - **Auswahlregel und Fitness standen vorab fest:** Farbinvarianz ≥ 0,96 und Trainingsgenauigkeit ≥ 0,90 auf allen 6 Seeds. Trainingsgenauigkeit heißt Trefferquote auf den eigenen Lehrer-Trainingsdaten.
  - Diese Seeds sind damit Entwicklungsdaten.
- **Bestätigung 510–514 (frische Seeds, Sieger-Konfiguration):** bestätigt. 4 von 5 Seeds erfüllen alle drei Bedingungen.
  - **Prämisse:** 5/5.
  - **M3-B unter `red`:** „Farbe 0“ geöffnet bei Episode 130, 140, 140, 130 und 130, also 30–40 Episoden nach dem Wechsel, im Mittel 34. Zusätzlich zweimal „Ziel“.
  - **M3-B unter `none`:** keine Fehlalarme.
  - **M3-B unter `global`:** eine Fehlöffnung, „Farbe 0“ bei Seed 510.
  - **Fehlzuschreibungen insgesamt nach §6:** M3-B 5, M3-A 2.
  - **M3-A unter `red`:** 3/5 Treffer, je bei Latenz 40. Der Mittelwert 144 zählt 2 Nichttreffer mit 300.
  - **S1-B unter `red`:** 5/5 Treffer.
- **Entscheidung des Nutzers vom 05.10.2026:** die bestehende Methode einfrieren (Entscheidung A), ohne weitere Bestätigungsrunde und ohne Änderung an Algorithmen, Hyperparametern, Schwellen oder Vorhersagen. Eingefroren mit Commit `b9589ce`.
- **Hauptlauf 400–409 (05./06.10.2026), vorregistrierte Auswertung:**
  - erfüllt: P1 (10/10), P2 (10/10), P4 und P5;
  - **nicht erfüllt: P3** (6/10);
  - **Abbruchkriterium ausgelöst**: M3-B öffnet bei `global` in 4/10 Seeds ein Merkmal.
  - Bericht: `farbversuch/BERICHT.md`.

## Aussagegrenzen

- **„Wiederöffnen“:** heißt Erweiterung des Erklärmodells um ein Merkmal. Routine und Encoder bleiben unverändert.
- **Strukturvorgabe von Arm B:** Arm B bekommt mit 6 Merkmalen der Zielzelle eine starke räumliche Vorgabe. Ein Vorteil von B gegenüber A ist zunächst ein Vorteil dieser Vorgabe in dieser Welt.
- **M3 gegen S1:**
  - M3 berücksichtigt im Modellvergleich die anderen Merkmale: Basisdesign und residualisierte Kandidaten.
  - S1 testet marginale Unterschiede der Überraschung. Seine Übungs-Ontologie entfernt nur Kandidaten.
  - Der Vergleich isoliert daher keine allgemeine Überlegenheit gegenüber klassischer Statistik.
- **Zeilenabhängigkeit:** Kreuzvalidierung und Permutationen arbeiten auf Zeilen, obwohl Schritte einer Episode voneinander abhängen. Die Wahl „Zeilen statt Episoden“ war ergebnisgeleitet (Spec v2, Anhang A).
- **Adaptive Zusatzöffnungen:** Nach einer Öffnung wechselt das Basismodell. Das Fehlerniveau späterer Öffnungen ist nicht gesondert kalibriert.
- **Fehlöffnung bei `global`, Seed 510:** Sie geschah beim ersten Erklären (Episode 110) mit positivem δ. Wiederholtes Testen oder δ = 0 sind dafür keine nachgewiesene Ursache.
- **„Ziel“-Öffnungen unter `red`:** Sie zählen als Fehlzuschreibungen. Ein echter Vorhersagegewinn durch ein Ersatzmerkmal ist möglich, aber ungeprüft.

## Technik und Dokumente

- Python 3, nur numpy (plus pytest).
- Code: `farbversuch/`. Läufe sind über Seeds und Bedingungen parallelisiert (`--jobs`), die BLAS-Threads sind fest auf 1 gesetzt.
- Spezifikation v2 (bindend): `docs/superpowers/specs/2026-10-03-farb-wiederoeffnung-v2-design.md`
- Plan v2 (bindend, mit Festlegungen 1–10): `docs/superpowers/plans/2026-10-03-farb-wiederoeffnung-v2.md`
- v1 als Geschichte: `docs/superpowers/specs/2026-10-03-farb-wiederoeffnung-design.md`, `docs/superpowers/plans/2026-10-03-farb-wiederoeffnung.md`
- Protokoll aller Pilot-Änderungen, der Evolution und der Bestätigungen: `farbversuch/PROTOKOLL.md`
- Übergabe an die nächste Sitzung mit Laufbefehlen für Einfrieren und Hauptlauf: `docs/HANDOVER.md`
- Review des Nutzers vom 04.10.2026 mit vier behobenen Fehlern und Hinweisen zur Deutung: `docs/REVIEW-2026-10-04.md`
