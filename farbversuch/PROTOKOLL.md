# Protokoll der Pilot-Änderungen (Spec v2 §8.1)

Jede Änderung an `farbversuch/pilot_config.json` mit Grund und den Messwerten davor. Erlaubt sind nach Spec v2 §8.1 nur Trainings-Hyperparameter der Routine und des Vorwärtsmodells, Puffergröße und Prüfintervall.

Maschine aller Läufe: Cloud-Container, 4 Kerne, Python 3.11.15, numpy 2.4.6, BLAS-Threads 1.

## 1. `wd` 0,001 → 0,01 (04.10.2026)

**Ausgangslauf:** Pilot Seed 0 mit den Standardwerten (`Config()`), Start 07:15:34, Ende nach 83 s. Code-Stand 352092c. Die Prämisse ist nicht erfüllt, deshalb gab es keine Kalibrierung und keine Bedingungen (Entscheidung D2).

| Messgröße | Wert | Grenze | erfüllt |
|---|---|---|---|
| Farbinvarianz (P1) | 0,9258 | ≥ 0,95 | nein |
| Vorwärtsmodell / Häufigkeitsmodell (P1) | 0,5831 / 1,5912 | kleiner | ja |
| Restanteil (P1b) | 0,1117 | ≤ 0,15 | ja |
| Verschiebung (P1b) | 0,1574 | ≤ 0,25 | ja |

**Grund:** P1 scheitert allein an der Farbinvarianz. Ein stärkerer Weight Decay der Routine drückt die Gewichte der im Training bedeutungslosen Farbbits gegen null.

**Vorprüfung:** explorativ, Seed 0, außerhalb des Ergebnisordners. Gerechnet wurden `train_phase1` und `premise_checks` mit je einer geänderten Größe; alles andere ist Standard.

| Variante | Farbinvarianz | Restanteil | Verschiebung | Vorwärts / Häufigkeit | Treffer auf Lehrerdaten | Prämisse |
|---|---|---|---|---|---|---|
| wd 0,003 | 0,9319 | 0,0817 | 0,1508 | 0,5803 / 1,5729 | 0,8991 | nein |
| wd 0,01 | 0,9797 | −0,0364 | 0,1035 | 0,6182 / 1,3688 | 0,9128 | ja |
| wd 0,03 | 0,9787 | 0,1189 | 0,0556 | 0,8221 / 1,3956 | 0,7291 | ja |
| epochs 2000 | 0,8833 | 0,2280 | 0,2461 | 0,5505 / 1,5979 | 0,9475 | nein |

**Entscheidung:** `wd` = 0,01, vom Nutzer am 04.10.2026 freigegeben.
- **Gewählt:** P1 und P1b sind deutlich erfüllt, und die Routine folgt dem Lehrer fast unverändert.
- **Verworfen:** wd 0,03 schließt die Farbe ebenfalls, verschlechtert aber die Routine stark. Mehr Epochen verschlechtern die Invarianz.
- **Kopplung:** `wd` wirkt nur auf das Training der Routine. Es fließt weder in das Erklären noch in die P1b-Messung.

**Altes Ergebnis:** aus `farbversuch/results/pilot` entfernt, damit die CLI mit der neuen Konfiguration startet. Die Werte stehen oben.

**Ergebnis des nächsten Pilots** (wd 0,01, Start 07:26:53, Ende 08:41:11, `--jobs 4`):
- **Prämisse:** erfüllt. Invarianz 0,980, Vorwärts / Häufigkeit 0,618 / 1,369, Restanteil −0,036, Verschiebung 0,103.
- **Übungs-Ontologie:**
  - M3-B: Wand
  - M3-A: bit25&a3, bit23&a2, bit31&a1
  - S1-B: Farbe 3
  - S1-A: 8 Bit×Aktion-Merkmale
- **δ:** M3-B 0,00078, M3-A 0,0199.
- **Schwellen und p_global:** m3_threshold 0,851, cusum_k 1,137, cusum_h 45,2. p_global 0,248 (hit, bracketed).
- **M3-B:**
  - `red`: bemerkt bei 110, öffnet „Farbe 0“ bei 110 (Nutzbarkeit 0,0062).
  - `global`: bemerkt bei 120, öffnet nichts.
  - `none`: Fehlalarm bei 260, öffnet nichts.
  - `walls`: nicht bemerkt.
- **Laufzeit:** Phase 1 1801 s, davon δ M3-A ≈ 22,5 min. Bedingungen: none 1114 s, red 2063 s, global 2639 s, walls 1 s. M3-A dominiert.

Keine weitere Änderung. Die Pilot-Konfiguration ist damit fertig.

## Bestätigung 500–504 (04.10.2026, keine Konfigurationsänderung)

**Lauf:** mit derselben `pilot_config.json` (wd 0,01), `--jobs 4`, Start 08:41:51, Ende 10:01:25.

**Ergebnis: nicht bestätigt.** Nur 2 von 5 Seeds erfüllen alle drei Kriterien gleichzeitig, nötig sind 4.
- **Prämisse:** erfüllt bei 500 (Invarianz 0,967) und 502 (0,980). Gescheitert an P1 bei 501 (0,939), 503 (0,941) und 504 (0,946). P1b ist auf allen fünf Seeds erfüllt (Restanteil ≤ 0,065, Verschiebung ≤ 0,104).
- **Seeds 500 und 502:**
  - M3-B öffnet bei `none` und `global` nichts.
  - Bei `red` öffnet M3-B „Farbe 0“ nach dem Wechsel (bei 130 bzw. 140).
  - Bei 500 öffnet M3-B unter `red` zusätzlich „Farbe 3“ (Gewinn 0,0005, knapp über δ 0,0005).

Die Seeds 500–504 sind verbraucht. Eine weitere Runde läuft nur auf neuen Seeds (510–514 usw.). Details: `results/confirm_report.md`.

## 2. Routine-Training per Evolution: wd, lr, epochs, init_std, n_teacher_episodes (04./05.10.2026)

**Grund:** P1 scheiterte in der Bestätigung 500–504 an der Farbinvarianz. Sie lag dort zwischen 0,939 und 0,980. Dazu kam ein instabiles Training: Die Trefferquote auf den Lehrerdaten schwankte zwischen Seeds und benachbarten Einstellungen von 0,65 bis 0,91.

**Entwicklungsdaten:** die verbrauchten Seeds 0 und 500–504. Für eine Bestätigung zählen sie nicht mehr.

**Auswahlregel, vor dem Ansehen der Ergebnisse festgelegt:** Auf allen 6 Seeds muss gelten:
- Farbinvarianz ≥ 0,96, also 0,01 Abstand zur Schwelle;
- Trefferquote der Routine auf den Lehrerdaten ≥ 0,90;
- P1b erfüllt.

**Schritt 1, Raster** (nur die Prämisse, alle 6 Seeds; Daten in `results/evo/screening_wd_teacher.jsonl`). Keine Variante erfüllt die Regel.

| Variante | Prämisse | Invarianz min | Trefferquote min |
|---|---|---|---|
| wd 0,015 | 2/6 | 0,939 | 0,65 |
| wd 0,02 | 4/6 | 0,917 | 0,70 |
| n_teacher 8000 | 5/6 | 0,940 | 0,74 |
| n_teacher 8000 + wd 0,015 | 6/6 | 0,954 | 0,80 |

**Schritt 2, Evolution:** Vorschlag des Nutzers, freigegeben mit „wenn man schon nah dran ist lohnt evolvieren oft“. Skript, Log und alle Kandidaten liegen in `results/evo/`.
- **Verfahren:** (2+4)-Evolution, höchstens 8 Generationen.
- **Mutation:** log-normal auf `wd`, `lr`, `epochs` und `init_std`. `n_teacher_episodes` wechselt mit Wahrscheinlichkeit 0,3 zwischen 4000, 6000 und 8000.
- **Fitness (vorab festgelegt):** min über die 6 Seeds von min(Invarianz − 0,96; Trefferquote − 0,90). Ziel war ≥ +0,005.
- **Start:** die bisherige Konfiguration und n_teacher 8000 + wd 0,015.
- **Verlauf der besten Fitness:**

  | Generation | 0 | 1 | 3 | 4 | 6 | 8 |
  |---|---|---|---|---|---|---|
  | Fitness | −0,098 | −0,030 | −0,016 | −0,006 | +0,002 | +0,0068 |

  In Generation 8 ist das Ziel erreicht. Insgesamt wurden 34 Kandidaten bewertet.

**Sieger:** wd 0,0203, lr 0,1535, epochs 500, init_std 0,00772, n_teacher_episodes 8000.

**Volle Prämissenprüfung des Siegers auf den 6 Entwicklungs-Seeds:**

| Seed | Invarianz | Trefferquote | Vorwärts / Häufigkeit | Restanteil | Verschiebung | Prämisse |
|---|---|---|---|---|---|---|
| 0 | 0,974 | 0,909 | 0,634 / 1,382 | −0,017 | 0,087 | erfüllt |
| 500 | 0,977 | 0,910 | 0,717 / 1,415 | −0,040 | 0,074 | erfüllt |
| 501 | 0,973 | 0,909 | 0,672 / 1,446 | 0,014 | 0,083 | erfüllt |
| 502 | 0,967 | 0,909 | 0,602 / 1,334 | 0,045 | 0,086 | erfüllt |
| 503 | 0,967 | 0,912 | 0,603 / 1,436 | −0,025 | 0,114 | erfüllt |
| 504 | 0,975 | 0,907 | 0,639 / 1,400 | 0,046 | 0,077 | erfüllt |

**Deutung (Annahme):** Die Lernrate 0,5 war zu groß für Full-Batch-Training. Mit lr ≈ 0,15 und 500 Epochen konvergiert das Training gleichmäßig, die Trefferquote liegt auf allen Seeds bei ≈ 0,91. Doppelt so viele Lehrerdaten verringern zufällige Zusammenhänge zwischen Farbe und Aktion, der stärkere Weight Decay drückt die Farbgewichte.

**Kopplung:** Alle fünf Größen wirken nur auf das Training der Routine, nicht auf das Erklären und nicht auf die P1b-Messung.

**Freigabe:** `n_teacher_episodes` gehört zu den Größen, die nur nach Rückfrage geändert werden; der Nutzer hat es freigegeben. Die Übernahme und die Bestätigung auf den Seeds 510–514 hat der Nutzer am 05.10.2026 freigegeben.

**Offener Punkt (Idee des Nutzers):** Für eine Invarianz von 1,0 fehlt dem Modell ein Sparsamkeitsdruck, zum Beispiel Gruppen-Lasso je Eingabebit. Das wäre eine Codeänderung und ist nicht Teil dieser Konfiguration.

## Bestätigung 510–514 (05.10.2026, Konfiguration aus Abschnitt 2)

**Lauf:** `--jobs 4`, Start 09:24:22, Ende 12:51:37.
- Der Container wurde zweimal neu gestartet, um etwa 11:00 und etwa 11:25.
- Fortgesetzt wurde jeweils mit demselben Befehl. Vorbereitung und fertige Bedingungen wurden übernommen, nur laufende Bedingungen wurden neu gerechnet.
- Die Ergebnisse hängen nicht von der Laufreihenfolge ab.

**Ergebnis: bestätigt.** 4 von 5 Seeds erfüllen alle drei Kriterien gleichzeitig, nötig sind 4.
- **Prämisse:** auf allen 5 Seeds erfüllt (Invarianz 0,964–0,984, Restanteil ≤ 0,056, Verschiebung ≤ 0,083).
- **M3-B unter `red`:** öffnet auf allen 5 Seeds „Farbe 0“ nach dem Wechsel, bei 110–140 bzw. 10–40 Episoden danach. Zusätzlich gibt es 2 Fehlzuschreibungen: „Ziel“ bei 512 und 513.
- **M3-B unter `none`:** auf keinem Seed ein Fehlalarm.
- **M3-B unter `global`:**
  - Auf 4 Seeds bemerkt M3-B die Änderung und öffnet nichts.
  - Bei 510 öffnet M3-B „Farbe 0“ bei Episode 110, eine Fehlöffnung. Damit verfehlt 510 das Kriterium 2.
- **M3-B unter `walls`:** bemerkt auf 2 Seeds. Bei 512 öffnet M3-B „Farbe 3“ und „Farbe 2“, das ist eine Fehlzuschreibung. Für die Bestätigung zählt `walls` nicht.
- **Vergleich (explorativ):**
  - M3-A schreibt `red` auf 3/5 Seeds richtig zu, im Mittel erst nach 144 Episoden, und öffnet unter `global` 6 Merkmale.
  - S1-B und S1-A haben deutlich mehr Fehlzuschreibungen: unter `red` 6 bzw. 10.
- **p_global:** 0,227–0,269, überall hit und bracketed.
- **Laufzeit je Seed:** Phase 1 1764–1813 s, Rechenzeit gesamt 4035–6735 s.

Details: `results/confirm_510_report.md`. Die Seeds 510–514 sind verbraucht. Wie es weitergeht (zusätzliche Seeds, Einfrieren, Hauptlauf), entscheidet der Nutzer.
