# Handover Farbversuch (Stand 03.10.2026)

Für die nächste Claude-Sitzung, die das Projekt weiterführt. Hintergrund in `docs/PROJEKTBESCHREIBUNG.md`, die bindende Spezifikation in `docs/superpowers/specs/2026-10-03-farb-wiederoeffnung-design.md`, der Plan mit 17 Aufgaben und 18 „Festlegungen“ in `docs/superpowers/plans/2026-10-03-farb-wiederoeffnung.md`.

Repo `aporia-evo/tths`, Branch `claude/dreamy-wozniak-7xt321`.

## Stand

- **Code fertig:** Tasks 1–14 sind umgesetzt (subagent-gesteuert, jede Aufgabe einzeln geprüft und abgenommen) und gepusht.
- **Tests:** 125 Tests, alle grün. Ohne die langsamen: `python -m pytest -q -m "not slow"` gibt 111 passed in ca. 10 s.
- **Gesamtprüfung:** Ein Review des ganzen Branches lief zum Zeitpunkt dieser Übergabe noch. Sein Ergebnis steht nicht in diesem Dokument. Bei Fortsetzung zuerst prüfen, ob es Korrektur-Commits gab (`git log`).
- **Offen:** Task 15 (Pilot), Task 16 (Einfrieren + Hauptlauf), Task 17 (Auswertung + Bericht).

## Nächste Schritte

1. **Pilot Seed 0**, immer mit festen BLAS-Threads (sonst weichen Ergebnisse um ~1e-6 ab):
   ```bash
   export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
   python -m farbversuch.run --seeds 0 --out farbversuch/results/pilot
   ```
2. **P1 wird mit den Standardwerten scheitern:** Gemessen auf Seed 0 mit voller Konfiguration (nur Phase 1):

   | Messgröße | Wert |
   |---|---|
   | Farbinvarianz | 0,933 (Schwelle 0,95) |
   | Vorwärtsmodell | 0,575 |
   | Klassenhäufigkeiten | 1,596 |
   | Phase 1 | 43 s |
   | m3_threshold | 0,830 |
   | cusum_k | 1,060 |
   | cusum_h | 86,9 |

   Erlaubte Anpassungen: nur Trainings-Hyperparameter der Routine und des Vorwärtsmodells, Puffergröße, Prüfintervall. Sie kommen in `farbversuch/pilot_config.json`. Jede Änderung mit Grund (Fehlersuche oder P1) in `farbversuch/PROTOKOLL.md`. Vor einem neuen Pilotlauf die alte Ausgabe löschen, denn die CLI überspringt vorhandene `seed_<n>.json` stillschweigend, auch bei anderer Konfiguration.
3. **Vor dem Einfrieren mit dem Nutzer klären** (siehe unten), dann `python -m farbversuch.freeze write --config farbversuch/pilot_config.json`, committen, pushen.
4. **Hauptlauf erst nach Freigabe durch den Nutzer**, mit denselben exportierten Variablen:
   ```bash
   python -m farbversuch.run --config farbversuch/frozen_config.json --seeds 400-409 --jobs 4 --out farbversuch/results/main
   python -m farbversuch.freeze verify
   python -m farbversuch.analyze --results farbversuch/results/main --seeds 400-409
   ```
   Der Lauf lässt sich fortsetzen (fertige Seeds werden übersprungen). Laufzeit realistisch etwa 5 Stunden mit 4 Prozessen, weil M3-A pro Prüfung ~75–90 s braucht.

## Offene Entscheidungen des Nutzers (vor dem Einfrieren)

1. **S1-A kann nie etwas öffnen:** Mit 1000 Permutationen ist der kleinste p-Wert 1/1001, Holm verlangt bei 1192 Kandidaten aber ≤ 0,05/1192. Entweder so lassen und im Bericht als Grenze nennen, oder `n_perm` auf ≥ 24.000 setzen.
2. **P3-Risiko, inzwischen mit Hinweis belegt:** Das Vorwärtsmodell bekommt z und Aktion ohne Wechselwirkung. Farbbits bedeuten außerdem immer „keine Wand“.
   - Auf der Mini-Konfiguration öffnet M3-B bei `red` zuerst „Wand“, dann erst „Farbe 0“.
   - Im `none`-Strom kam es zu einem Fehlalarm mit Öffnung von „Wand“ und „Farbe 0“. Das war die kleine Testkonfiguration und ist noch nicht für die volle Konfiguration bestätigt.
   - Folge: „Wand“ könnte bei `global` geöffnet werden, P3 und das Abbruchkriterium wären gefährdet. Eine Änderung wäre eine Spec-Änderung und muss vor dem Einfrieren entschieden werden.

## Entscheidungen, die während der Umsetzung getroffen wurden

- Task 12 erwartet 7 statt 6 Tests (parametrisierter Isolationstest).
- Gesamtprüfung des Codes vor dem Pilot, nicht erst am Ende.
- Vor dem Hauptlauf anhalten und den Nutzer fragen: Der Hauptlauf ist wissenschaftlich nicht umkehrbar (Spec §8).
- Ein Test (`test_warm_start_reaches_same_optimum`) nutzt `tol=1e-8`. Der Löser bleibt bei Standard `tol=1e-6`, wegen der Laufzeit. Folge: ~1e-7 bis 5e-7 Lösungsrauschen in der Log-Likelihood. `logreg_tol` darf im Pilot angepasst werden.
- Pilot und Hauptlauf immer mit den drei Thread-Variablen auf 1.

## Bekannte kleinere Punkte (nicht behoben, Kandidaten für Nacharbeit)

- Kein Test fixiert, dass M3 genau das Mittel der **letzten** 500 Schritte nimmt und strikt „>“ vergleicht.
- `p_global.bracketed` heißt in der Ausgabe „Toleranz getroffen“, nicht „einschließbar“ wie in Festlegung 15.
- Ein nicht konvergierter Basis-Fit in M3 würde allen Kandidaten unverdiente Verbesserung geben. In keinem Lauf beobachtet, aber ungeschützt.
- Der Farbinvarianz-Test prüft nur Grenzen. Eine direkte Prüfung der P1-Metrik fehlt.
- `freeze verify` meldet „OK“ bei leerer Prüfsummendatei, und nach dem Einfrieren hinzugefügte Dateien werden nicht erkannt.

## Arbeitsweise im Projekt

Workflow nach „superpowers“: brainstorming → writing-plans → subagent-driven-development. Commits auf dem Branch oben, kein Push auf andere Branches, kein Pull Request ohne Auftrag. Bericht später mit fester Gliederung (Spec §11). „Bestätigt“ oder „bewiesen“ nur bei erfüllter Vorhersage.
