# Farbversuch – Projektbeschreibung

## Frage

Kann ein System lernen, welche Information es bei einer Routine ignorieren darf, und erkennen, wann diese Vereinfachung nicht mehr reicht?

Diese Version prüft nur **Bemerken** und **Erklären**. Die Routine wird nach dem Üben nicht mehr verändert. Umlernen ist ein späterer, eigener Versuch.

## Idee in einem Absatz

Ein Agent lernt in einer kleinen Gitterwelt, zum Ziel zu laufen. Der Boden hat vier Farben, die beim Üben nichts bedeuten. Die Routine lernt deshalb, Farbe zu ignorieren. Später wird eine Farbe (intern `C_SPECIAL`) rutschig: Wer sie betritt, rutscht mit 50 % eine Zelle weiter. Das System soll das allein bemerken (Überraschung in seiner Eigenwahrnehmung steigt) und erklären (die geschlossene Dimension „Bodenfarbe der Zielzelle“ wieder öffnen). Neuheit hilft dabei nicht, denn Farbe war im Training schon da, nur bedeutungslos.

## Aufbau

- **Welt:** 9×9-Gitter, Innenwände mit 15 %, vier Bodenfarben, 10 % Grundrutschen, höchstens 40 Schritte pro Episode. Beobachtung: egozentrisches 7×7-Fenster mit 298 Bits. Eigenwahrnehmung: tatsächliche Verschiebung als eine von 9 Klassen.
- **Routine:** imitiert einen BFS-Lehrer (4000 Episoden), Encoder z = tanh(E·x) mit k = 32, Softmax-Policy.
- **Vorwärtsmodell:** multinomiale logistische Regression auf [z, Aktion, 1], sagt die Verschiebung vorher. Überraschung = −log p.
- **Einsatz:** 400 Episoden, Wechsel bei Episode 100, vier Bedingungen auf denselben Karten:
  - `none`: keine Änderung
  - `red`: die Farbe wird rutschig
  - `global`: mehr Grundrutschen, mit gleicher mittlerer Überraschung wie `red`
  - `walls`: dichtere Wände
- **Vier Systeme:**

  | System | Bemerken | Erklären | Kandidaten |
  |---|---|---|---|
  | M3-B (Hauptsystem) | Mittel der Überraschung über 500 Schritte | Kreuzvalidierter Modellvergleich (5 Teilungen, Verbesserung in allen) | 6 Zellmerkmale der Zielzelle |
  | M3-A | wie M3-B | wie M3-B | 1192 Rohbit×Aktion-Merkmale |
  | S1-B | CUSUM | Permutationstest + Holm | wie M3-B |
  | S1-A | CUSUM | Permutationstest + Holm | wie M3-A |

## Vorab festgelegte Vorhersagen (Hauptlauf Seeds 400–409)

- **P1:** Prämissen erfüllt (Farbinvarianz ≥ 95 %, Vorwärtsmodell besser als reine Klassenhäufigkeiten).
- **P2:** M3-B schreibt `red` in ≥ 9/10 Seeds korrekt zu.
- **P3:** M3-B öffnet bei `global` in ≥ 9/10 Seeds kein Merkmal.
- **P4:** M3-A ist langsamer oder macht mehr Fehlzuschreibungen als M3-B.
- **P5:** M3-B trifft bei `red` mindestens so oft wie S1-B.
- **Abbruch:** < 5/10 korrekt bei `red` oder > 3/10 Öffnungen bei `global`.

## Vorgehen

Pilot auf Seed 0 (nur Fehlersuche und P1, nur Trainings-Hyperparameter, Puffergröße und Prüfintervall dürfen sich ändern). Danach werden Konfiguration und Prüfsummen eingefroren, dann folgt der Hauptlauf und der Bericht mit fester Gliederung. Beobachtung und Deutung stehen im Bericht getrennt.

## Technik und Dokumente

- Python 3, nur numpy (plus pytest).
- Code: `farbversuch/`.
- Spezifikation: `docs/superpowers/specs/2026-10-03-farb-wiederoeffnung-design.md`
- Plan: `docs/superpowers/plans/2026-10-03-farb-wiederoeffnung.md`
- Übergabe an die nächste Sitzung: `docs/HANDOVER.md` (dort auch die Abweichungen vom Plan)
