# Handover Farbversuch (Stand 03.10.2026, nach Gesamtprüfung)

Für die nächste Claude-Sitzung, die das Projekt weiterführt. Hintergrund in `docs/PROJEKTBESCHREIBUNG.md`, die bindende Spezifikation in `docs/superpowers/specs/2026-10-03-farb-wiederoeffnung-design.md`, der Plan mit 17 Aufgaben und 18 „Festlegungen“ in `docs/superpowers/plans/2026-10-03-farb-wiederoeffnung.md`.

Repo `aporia-evo/tths`, Branch `claude/dreamy-wozniak-7xt321`.

## Stand

- **Code fertig:** Tasks 1–14 sind umgesetzt (subagent-gesteuert, jede Aufgabe einzeln geprüft und abgenommen).
- **Gesamtprüfung und Korrekturrunde:** Danach lief eine Gesamtprüfung des Branches. Sie fand 0 kritische und 3 wichtige Punkte; alle sind korrigiert und nachgeprüft (sechs Commits `1a95e1b`…`495fe60`).
- **Tests:** 189 Tests, alle grün und ohne Warnungen. Ohne die langsamen: `python -m pytest -q -m "not slow"` gibt 173 passed in ca. 2 s.
- **Offen:** Task 15 (Pilot), Task 16 (Einfrieren + Hauptlauf), Task 17 (Auswertung + Bericht).
- **Bewusst angehalten:** Vor dem Pilot stehen Entscheidungen des Nutzers an (siehe unten). Eine Spec-Änderung würde einen jetzt gelaufenen Pilot entwerten.

## Offene Entscheidungen des Nutzers (vor dem Pilot)

1. **P3-Risiko, inzwischen auf Seed 0 mit voller Konfiguration belegt:**
   - **Wand ohne Änderung:** M3-B öffnet „Wand“ schon auf einem Puffer ohne jede Änderung. Der kreuzvalidierte Gewinn liegt bei +0,137 nats pro Schritt, in der schlechtesten Teilung bei +0,118.
   - **Ursache:** Die Routine läuft in 24 % der Schritte gegen eine Wand. Sie stimmt im eigenen Lauf nur zu 56 % mit dem Lehrer überein (93,5 % auf den Lehrerdaten), und 16 % der Episoden laufen in die Zeitgrenze. Das Vorwärtsmodell hat keine Wechselwirkung zwischen z und Aktion und kann „Wand in gewählter Richtung“ nicht ausdrücken.
   - **Folge für `global`:** Die Rot-Überraschung liegt bei 1,24 gegenüber 0,57 ohne Änderung, die M3-Schwelle bei 0,849. `global` wird also fast sicher bemerkt, M3-B öffnet „Wand“, P3 scheitert, und das Abbruchkriterium (> 3/10) löst sehr wahrscheinlich aus.
   - **Folge für `red`:** „Wand“ (0,1121) und „Farbe 0“ (0,1120) liegen gleichauf, „Farbe 0“ wird als zweites geöffnet. P2 sieht damit machbar aus.
   - **Folge für M3-A:** Wandbits liegen vor den Farbe-0-Bits. M3-A verbraucht seine drei Öffnungen wahrscheinlich auf Wandbits, P4 würde dann von diesem Artefakt entschieden.
   - **Optionen (Spec-Ebene):** das Vorwärtsmodell um eine Wechselwirkung zwischen z und Aktion ergänzen oder das Wandbit der Zielzelle hinzunehmen; die Routine aus ihrer Softmax ziehen lassen statt argmax; besseres Training über die erlaubten Pilot-Parameter (mildert vermutlich nur); oder so lassen und berichten.
2. **S1-A kann nie etwas öffnen:** Mit 1000 Permutationen ist der kleinste p-Wert 1/1001, Holm verlangt bei 1192 Kandidaten aber ≤ 0,05/1192. Entweder als Grenze berichten oder `n_perm` ≥ 24.000.
3. **Bestätigen:** Eine Öffnung von „Farbe 0“ vor dem Wechsel zählt bei `red` jetzt nicht als Treffer, sondern als Fehlzuschreibung (Abweichung vom Plan, siehe unten).

## Nächste Schritte nach den Entscheidungen

1. **Pilot Seed 0:**
   ```bash
   python -m farbversuch.run --seeds 0 --out farbversuch/results/pilot
   ```
   Der Code legt die BLAS-Threads jetzt selbst auf 1 fest und schreibt sie in einen `env`-Block jeder Ergebnisdatei. Fortschrittszeilen gehen auf stderr.
2. **P1 wird mit den Standardwerten scheitern.** Werte auf Seed 0 mit 1 Thread (gültige Referenz; frühere Notizen mit 3 Threads sind veraltet):

   | Messgröße | Wert |
   |---|---|
   | Farbinvarianz | 0,926 (Schwelle 0,95) |
   | m3_threshold | 0,849 |
   | cusum_k | 1,071 |
   | cusum_h | 57,2 |
   | p_global | 0,381 (in 6 Auswertungen gefunden) |

   Erlaubte Anpassungen: nur Trainings-Hyperparameter der Routine und des Vorwärtsmodells, Puffergröße, Prüfintervall. Sie kommen in `farbversuch/pilot_config.json`. Jede Änderung mit Grund (Fehlersuche oder P1) in `farbversuch/PROTOKOLL.md`. Liegt im Ausgabeordner schon ein Ergebnis mit anderer Konfiguration, bricht die CLI ab: alte Pilotdatei vorher löschen.
3. **Einfrieren:** `python -m farbversuch.freeze write --config farbversuch/pilot_config.json`, dann `verify`, committen, pushen.
4. **Hauptlauf erst nach Freigabe durch den Nutzer:**
   ```bash
   python -m farbversuch.run --config farbversuch/frozen_config.json --seeds 400-409 --jobs 4 --out farbversuch/results/main
   python -m farbversuch.freeze verify
   python -m farbversuch.analyze --results farbversuch/results/main --seeds 400-409
   ```
   Der Lauf lässt sich fortsetzen; nur Ergebnisse mit gleicher Konfiguration werden übersprungen. Laufzeit schätzungsweise unter 5 Stunden. M3-A braucht ~75–90 s pro Prüfung, erreicht seine Obergrenze von 3 Öffnungen aber schnell.

## Abweichungen vom Plan (durch Entscheidungen während der Umsetzung)

- **Zuschreibung bei `red`:** zählt nur, wenn die Öffnung nach dem Wechsel liegt (E > 100). Die Latenz ist dann E − 100. Frühere Öffnungen zählen als Fehlzuschreibung. Der Plan hatte max(0, E − 100). Grund: Vor dem Wechsel sind alle vier Ströme identisch, eine frühere Öffnung kann den Wechsel also nicht erkannt haben.
- **`p_global`:** Das Ergebnis enthält jetzt zwei Kennzeichen. `hit` heißt Toleranz getroffen. `bracketed` folgt Festlegung 15 und ist nur false, wenn der Zielwert nicht einschließbar ist.
- **BLAS-Threads:** Der Code legt sie fest, statt sich auf die Shell zu verlassen. Ergebnisse mit anderer Thread-Zahl unterscheiden sich deutlich. `evaluate` verlangt gleiche Konfiguration und gleiche Umgebung über alle Seeds.
- **Testtoleranz:** Ein Test (`test_warm_start_reaches_same_optimum`) nutzt `tol=1e-8`. Der Löser bleibt bei Standard `tol=1e-6`; die zulässigen Verbesserungen liegen bei ≥ 1e-5, also deutlich über dem Lösungsrauschen.
- **Commit-Kennung:** Commits nennen das Modell, das sie geschrieben hat.

## Bekannte kleinere Punkte (bewusst gelassen)

- **Seeds werden geprüft:** Doppelte Seeds weist `parse_seeds` (CLI von `run` und `analyze`) und `evaluate` mit `ValueError` ab; der Temp-Dateiname je Seed enthält die Prozess-ID.
- **Explorative Auswertung:** Die vorregistrierten Urteile (P2–P5, Abbruch) gibt `evaluate` nur für genau die Seeds 400–409 aus (`"preregistered": True`). Bei anderen Seeds (z. B. Pilot Seed 0) stehen Zahlen und Kennzahlen, aber die Urteile sind `None`; der Bericht beginnt mit dem Hinweis „Explorative Auswertung“ und zeigt „–“ statt erfüllt/nicht erfüllt.
- Stürzt ein Seed im Hauptlauf ab, beendet das auch die parallel laufenden Seeds. Dann anhalten und den Nutzer fragen.
- Plan- und Spec-Text zeigen bei den Punkten oben noch den alten Stand. Maßgeblich sind die Abweichungen in diesem Dokument.

## Arbeitsweise im Projekt

Workflow nach „superpowers“: brainstorming → writing-plans → subagent-driven-development. Commits auf dem Branch oben, kein Push auf andere Branches, kein Pull Request ohne Auftrag. Bericht später mit fester Gliederung (Spec §11). „Bestätigt“ oder „bewiesen“ nur bei erfüllter Vorhersage.
