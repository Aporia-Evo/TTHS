# Farbversuch – Projektbeschreibung (Stand v2)

Bindend sind die Spezifikation v2 (`docs/superpowers/specs/2026-10-03-farb-wiederoeffnung-v2-design.md`) und der Plan v2 (`docs/superpowers/plans/2026-10-03-farb-wiederoeffnung-v2.md`). Die Dokumente der Version 1 (`…-farb-wiederoeffnung-design.md`, `…-farb-wiederoeffnung.md`) sind Geschichte. Anhang A der Spec v2 nennt, was sich gegenüber v1 geändert hat und warum. Der Plan v2 verweist für alles, was er nicht neu regelt, auf die Festlegungen des v1-Plans.

## Frage

Kann ein System lernen, welche Information es bei einer Routine ignorieren darf, und erkennen, wann diese Vereinfachung nicht mehr reicht?

Diese Version prüft nur **Bemerken** und **Erklären**. Die Routine wird nach dem Üben nicht mehr verändert. Umlernen ist ein späterer, eigener Versuch.

## Idee in einem Absatz

Ein Agent lernt in einer kleinen Gitterwelt, zum Ziel zu laufen. Der Boden hat vier Farben, die beim Üben nichts bedeuten. Die Routine lernt deshalb, Farbe zu ignorieren. Später wird eine Farbe (intern `C_SPECIAL`) rutschig: Wer sie betritt, rutscht mit 50 % eine Zelle weiter. Das System soll das allein bemerken (Überraschung in seiner Eigenwahrnehmung steigt) und erklären (die geschlossene Dimension „Bodenfarbe der Zielzelle“ wieder öffnen). Neuheit hilft dabei nicht, denn Farbe war im Training schon da, nur bedeutungslos.

## Aufbau

- **Welt:** 9×9-Gitter, Innenwände mit 15 %, vier Bodenfarben, 10 % Grundrutschen, höchstens 40 Schritte pro Episode. Beobachtung: egozentrisches 7×7-Fenster mit 298 Bits. Eigenwahrnehmung: tatsächliche Verschiebung als eine von 9 Klassen.
- **Routine:** imitiert einen BFS-Lehrer (4000 Episoden), Encoder z = tanh(E·x) mit k = 32, Softmax-Policy, handelt deterministisch.
- **Vorwärtsmodell:** multinomiale logistische Regression auf [z, Aktion, 1], sagt die Verschiebung vorher. Überraschung = −log p. Es liefert die Überraschung für das Bemerken, für alle Systeme gleich.
- **Übungs-Ontologie (neu in v2):** Jedes System öffnet am Ende der Übungsphase auf den letzten 2000 Schritten der Vorwärtsdaten mit seinem eigenen Erklärverfahren bis zu 8 Merkmale vor (M3: feste Mindestverbesserung 0,01 nats pro Schritt; S1: Holm-Ablehnungen). Diese Merkmale gehören zum geübten Modell. Sie gehen in das Basismodell des Erklärens ein, werden im Einsatz nie erneut getestet und zählen nie als „wieder geöffnet“. Sie wirken nur auf das Erklären, nicht auf das Bemerken.
- **Kalibrierung:** 20 Null-Ströme zu je 400 Episoden. Schwellen für das Bemerken (M3 und CUSUM) sind der größte der 20 Null-Werte. Erwartete Fehlalarmrate pro neuem Strom ≈ 1/21 ≈ 4,8 %. Die **Mindestverbesserung δ** (je M3-System) ist der größte der 20 Null-Gewinne; ein Null-Gewinn ist die größte mittlere Verbesserung unter den Kandidaten, die in allen 5 Teilungen positiv sind (0, wenn keiner).
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

„Vollständig geschlossen“ wird nicht behauptet.

## Vorab festgelegte Vorhersagen (Hauptlauf Seeds 400–409)

- **P1:** Prämissen (P1 und P1b) in jedem Hauptlauf-Seed erfüllt. Gescheiterte Seeds werden berichtet, nicht ersetzt und zählen bei P2, P3 und beim Abbruchkriterium gegen M3-B.
- **P2:** M3-B schreibt `red` in ≥ 9/10 Seeds korrekt zu. Richtig heißt: „Farbe 0“ wird nach dem Wechsel geöffnet.
- **P3:** M3-B öffnet bei `global` in ≥ 9/10 Seeds kein Merkmal.
- **P4:** M3-A ist bei `red` langsamer oder macht insgesamt mehr Fehlzuschreibungen als M3-B. Der Abstand wird beziffert.
- **P5:** M3-B trifft bei `red` mindestens so oft wie S1-B.
- **Abbruch:** < 5/10 korrekt bei `red` oder > 3/10 Öffnungen bei `global`.

Urteile zu P2–P5 und zum Abbruch gibt die Auswertung nur für genau die Seeds 400–409 aus. Jede andere Seedmenge ist explorativ.

## Vorgehen

Pilot → Bestätigung → Entscheidung des Nutzers → Einfrieren → Hauptlauf → Bericht.

1. **Pilot auf Seed 0:** Fehlersuche und Erfüllung von P1 und P1b. Anpassen dürfen sich nur Trainings-Hyperparameter der Routine und des Vorwärtsmodells, Puffergröße und Prüfintervall. Jede Änderung steht mit Grund in `farbversuch/PROTOKOLL.md`. Die Pilot-Konfiguration liegt in `farbversuch/pilot_config.json`.
2. **Bestätigung auf Seeds 500–504:** volle Pipeline mit der Pilot-Konfiguration, explorativ ausgewertet. Die Methode gilt als bestätigt, wenn es mindestens 4 von 5 Seeds gibt, in denen alle drei Bedingungen gleichzeitig gelten: (1) P1 und P1b erfüllt, (2) M3-B öffnet bei `none` und `global` nichts über die Übungs-Ontologie hinaus, (3) M3-B öffnet bei `red` „Farbe 0“ nach dem Wechsel. Dass jede Bedingung für sich in 4 von 5 Seeds gilt, genügt nicht (Präzisierung der Spec v2 §8, Entscheidung des Nutzers vom 04.10.2026). Nicht bestätigt: Ergebnis zurück an den Nutzer; eine weitere Runde läuft nur auf neuen Seeds (510–514 usw.).
3. **Entscheidung des Nutzers:** Bei Bestätigung entscheidet der Nutzer, ob zusätzlich die Seeds 505–509 laufen.
4. **Einfrieren:** `frozen_config.json` und SHA-256 aller Quelldateien in `freeze.sha256`.
5. **Hauptlauf** auf Seeds 400–409, danach Prüfsummen bestätigen und auswerten.
6. **Bericht** mit fester Gliederung (Spec v2 §11). Beobachtung und Deutung stehen getrennt. Was nach dem Hauptlauf geändert oder ergänzt wird, ist „nachträgliche Erkundung“ und muss auf frischen Seeds bestätigt werden.

Pilot, Bestätigung und Hauptlauf laufen jeweils komplett auf derselben Maschine.

## Technik und Dokumente

- Python 3, nur numpy (plus pytest).
- Code: `farbversuch/`. Läufe sind über Seeds und Bedingungen parallelisiert (`--jobs`), die BLAS-Threads sind fest auf 1 gesetzt.
- Spezifikation v2 (bindend): `docs/superpowers/specs/2026-10-03-farb-wiederoeffnung-v2-design.md`
- Plan v2 (bindend, mit Festlegungen 1–10): `docs/superpowers/plans/2026-10-03-farb-wiederoeffnung-v2.md`
- v1 als Geschichte: `docs/superpowers/specs/2026-10-03-farb-wiederoeffnung-design.md`, `docs/superpowers/plans/2026-10-03-farb-wiederoeffnung.md`
- Übergabe an die nächste Sitzung, mit Laufbefehlen und Prompt: `docs/HANDOVER.md`
