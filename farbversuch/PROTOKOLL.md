# Protokoll der Pilot-Änderungen (Spec v2 §8.1)

Jede Änderung an `farbversuch/pilot_config.json` mit Grund und den Messwerten davor. Erlaubt sind nach Spec v2 §8.1 nur Trainings-Hyperparameter der Routine und des Vorwärtsmodells, Puffergröße und Prüfintervall.

Maschine aller Läufe: Cloud-Container, 4 Kerne, Python 3.11.15, numpy 2.4.6, BLAS-Threads 1.

**Begriff Trainingsgenauigkeit:** Anteil der Lehrer-Trainingsdaten, auf denen die Routine die Lehreraktion wählt. Gemessen wird auf denselben Daten, mit denen sie trainiert wurde. Es ist keine Test- oder Einsatzgenauigkeit. Frühere Fassungen nannten das „Trefferquote auf den Lehrerdaten“.

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

| Variante | Farbinvarianz | Restanteil | Verschiebung | Vorwärts / Häufigkeit | Trainingsgenauigkeit | Prämisse |
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

**Grund:** P1 scheiterte in der Bestätigung 500–504 an der Farbinvarianz. Sie lag dort zwischen 0,939 und 0,980. Dazu kam ein instabiles Training: Die Trainingsgenauigkeit schwankte zwischen Seeds und benachbarten Einstellungen von 0,65 bis 0,91.

**Entwicklungsdaten:** die verbrauchten Seeds 0 und 500–504. Für eine Bestätigung zählen sie nicht mehr.

**Auswahlregel, vor dem Ansehen der Ergebnisse festgelegt:** Auf allen 6 Seeds muss gelten:
- Farbinvarianz ≥ 0,96, also 0,01 Abstand zur Schwelle;
- Trainingsgenauigkeit der Routine ≥ 0,90;
- P1b erfüllt.

**Schritt 1, Raster** (nur die Prämisse, alle 6 Seeds; Daten in `results/evo/screening_wd_teacher.jsonl`). Keine Variante erfüllt die Regel.

| Variante | Prämisse | Invarianz min | Trainingsgenauigkeit min |
|---|---|---|---|
| wd 0,015 | 2/6 | 0,939 | 0,65 |
| wd 0,02 | 4/6 | 0,917 | 0,70 |
| n_teacher 8000 | 5/6 | 0,940 | 0,74 |
| n_teacher 8000 + wd 0,015 | 6/6 | 0,954 | 0,80 |

**Schritt 2, Evolution:** Vorschlag des Nutzers, freigegeben mit „wenn man schon nah dran ist lohnt evolvieren oft“. Skript, Log und alle Kandidaten liegen in `results/evo/`.
- **Verfahren:** (2+4)-Evolution, höchstens 8 Generationen.
- **Mutation:** log-normal auf `wd`, `lr`, `epochs` und `init_std`. `n_teacher_episodes` wechselt mit Wahrscheinlichkeit 0,3 zwischen 4000, 6000 und 8000.
- **Fitness (vorab festgelegt):** min über die 6 Seeds von min(Invarianz − 0,96; Trainingsgenauigkeit − 0,90). Ziel war ≥ +0,005.
- **Start:** die bisherige Konfiguration und n_teacher 8000 + wd 0,015.
- **Verlauf der besten Fitness:**

  | Generation | 0 | 1 | 3 | 4 | 6 | 8 |
  |---|---|---|---|---|---|---|
  | Fitness | −0,098 | −0,030 | −0,016 | −0,006 | +0,002 | +0,0068 |

  In Generation 8 ist das Ziel erreicht. Insgesamt wurden 34 Kandidaten bewertet.

**Sieger:** wd 0,0203, lr 0,1535, epochs 500, init_std 0,00772, n_teacher_episodes 8000.

**Volle Prämissenprüfung des Siegers auf den 6 Entwicklungs-Seeds:**

| Seed | Invarianz | Trainingsgenauigkeit | Vorwärts / Häufigkeit | Restanteil | Verschiebung | Prämisse |
|---|---|---|---|---|---|---|
| 0 | 0,974 | 0,909 | 0,634 / 1,382 | −0,017 | 0,087 | erfüllt |
| 500 | 0,977 | 0,910 | 0,717 / 1,415 | −0,040 | 0,074 | erfüllt |
| 501 | 0,973 | 0,909 | 0,672 / 1,446 | 0,014 | 0,083 | erfüllt |
| 502 | 0,967 | 0,909 | 0,602 / 1,334 | 0,045 | 0,086 | erfüllt |
| 503 | 0,967 | 0,912 | 0,603 / 1,436 | −0,025 | 0,114 | erfüllt |
| 504 | 0,975 | 0,907 | 0,639 / 1,400 | 0,046 | 0,077 | erfüllt |

**Deutung (Annahme):** Die Lernrate 0,5 war zu groß für Full-Batch-Training. Mit lr ≈ 0,15 und 500 Epochen konvergiert das Training gleichmäßig, die Trainingsgenauigkeit liegt auf allen Seeds bei ≈ 0,91. Doppelt so viele Lehrerdaten verringern zufällige Zusammenhänge zwischen Farbe und Aktion, der stärkere Weight Decay drückt die Farbgewichte.

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
- **M3-B unter `red`:** öffnet auf allen 5 Seeds „Farbe 0“ nach dem Wechsel, bei Episode 130, 140, 140, 130 und 130 (Seeds 510–514). Das sind 30–40 Episoden nach dem Wechsel, im Mittel 34. Zusätzlich öffnet M3-B zweimal „Ziel“ (512 und 513); das sind nach §6 Fehlzuschreibungen. (Korrigiert am 05.10.2026; vorher stand hier fälschlich „110–140 bzw. 10–40“.)
- **M3-B unter `none`:** auf keinem Seed ein Fehlalarm.
- **M3-B unter `global`:**
  - Auf 4 Seeds bemerkt M3-B die Änderung und öffnet nichts.
  - Bei 510 öffnet M3-B „Farbe 0“ bei Episode 110, eine Fehlöffnung. Damit verfehlt 510 das Kriterium 2.
- **M3-B unter `walls`:** bemerkt auf 2 Seeds. Bei 512 öffnet M3-B „Farbe 3“ und „Farbe 2“, das ist eine Fehlzuschreibung. Für die Bestätigung zählt `walls` nicht.
- **Vergleich (explorativ, korrigiert am 05.10.2026):**
  - **M3-A, Zuschreibung `red`:** 3/5 Treffer, alle drei bei Latenz 40 (Seeds 511, 512, 514). Der berichtete Mittelwert 144 enthält die zwei Nichttreffer (510, 513), zensiert am Horizont 300.
  - **Fehlzuschreibungen insgesamt nach §6:** M3-B 5, M3-A 2. Außerhalb von `red` zählen dabei nur Farbmerkmale.
    - M3-B: 2 unter `red`, 1 unter `global`, 2 unter `walls`.
    - M3-A: 1 unter `red`, 1 unter `walls`.
    - M3-A öffnet unter `global` zusätzlich 6 Merkmale, die keine Farbmerkmale sind. Die Auswertung führt sie unter „Geöffnet“, nicht als Fehlzuschreibungen. Für P3, das nur M3-B betrifft, spielt das keine Rolle.
    - Eine pauschale Fehlerüberlegenheit von M3-B lässt sich daraus nicht ableiten.
  - **S1-B, Zuschreibung `red`:** ebenfalls 5/5 Treffer, mittlere Latenz 54, dazu 6 Fehlzuschreibungen unter `red`. S1-A: 3/5 Treffer, 10 Fehlzuschreibungen unter `red`. P5 misst die Trefferquote, nicht die Präzision aller Öffnungen.
- **p_global:** 0,227–0,269, überall hit und bracketed.
- **Laufzeit je Seed:** Phase 1 1764–1813 s, Rechenzeit gesamt 4035–6735 s.

Details: `results/confirm_510_report.md`. Die Seeds 510–514 sind verbraucht. Wie es weitergeht (zusätzliche Seeds, Einfrieren, Hauptlauf), entscheidet der Nutzer.

**Einordnung:** „Bestätigt“ bezieht sich hier nur auf die vorab festgelegte gemeinsame 4/5-Regel der Bestätigung (Spec v2 §8). Die Vorhersagen P2–P5 sind nicht geprüft. Sie bleiben dem Hauptlauf auf den Seeds 400–409 vorbehalten.

## Entwicklungsgeschichte im Überblick (Stand 05.10.2026)

Alle ergebnisgeleiteten Entscheidungen vor dem Einfrieren, in zeitlicher Reihenfolge:

1. **v1 → v2 (Spec v2, Anhang A):** Übungs-Ontologie, Residualisieren, δ, Kalibrierung über den größten Null-Wert und P1b wurden nach einer explorativen Diagnose auf Seed 0 eingeführt.
   - Dazu gehört auch eine **ergebnisgeleitete Wahl:** Die Kreuzvalidierung bleibt nach Zeilen, nicht nach Episoden. In der Diagnose brachte die Teilung nach Episoden mehr Fehlöffnungen (2/5 gegenüber 0/5 bei `global`) und weniger Trennschärfe.
   - Die Abhängigkeit der Zeilen ist damit eine berichtete Grenze.
2. **Pilot Seed 0:** `wd` 0,001 → 0,01, nach einer Vorprüfung mit 4 Varianten auf Seed 0 (Abschnitt 1).
3. **Bestätigung 500–504:** nicht bestätigt, Prämisse nur 2/5.
4. **Raster und Evolution (Abschnitt 2):** auf den Entwicklungs-Seeds 0 und 500–504.
   - Raster: 4 Varianten.
   - Evolution: 34 bewertete Kandidaten über `wd`, `lr`, `epochs`, `init_std` und `n_teacher_episodes`.
   - Auswahlregel und Fitness standen vor der Suche fest; Kriterien waren Farbinvarianz und Trainingsgenauigkeit.
5. **Bestätigung 510–514:** auf frischen Seeds, mit der Sieger-Konfiguration ohne weitere Änderung. Die gemeinsame 4/5-Regel ist erfüllt.

Auf den Seeds 0 und 500–504 wurde ausgewählt. Sie sind Entwicklungsdaten. Nur 510–514 sind eine unabhängige Prüfung der gewählten Konfiguration, und auch das nur für die Bestätigungsregel, nicht für P2–P5.

## Review-Nachtrag 05.10.2026: Vorbereitung des Einfrierens

**Entscheidung des Nutzers (05.10.2026):** Die bestehende Methode wird eingefroren, ohne weitere Bestätigungsrunde (Entscheidung A).
- **Unverändert:** Algorithmen, Hyperparameter (`pilot_config.json`), Schwellen und Vorhersagen.
- **Präzisierungen:** in Spec v2, Anhang B. Sie ändern keine Regel.

**Geprüfte Angaben** (gegen `results/confirm_510/seed_*.json`, `analyze.stream_metrics`, `run.py` und `monitor.py`):
- **M3-B unter `red`:** öffnet „Farbe 0“ bei Episode 130, 140, 140, 130 und 130, also 30–40 Episoden nach dem Wechsel, im Mittel 34. Die Korrektur steht oben.
- **M3-A unter `red`:** 3 Treffer, je bei Latenz 40. Der Mittelwert 144 enthält 2 Nichttreffer am Horizont 300.
- **Fehlzuschreibungen insgesamt:** M3-A 2, M3-B 5. S1-B trifft unter `red` ebenfalls 5/5.
- **Kalibrierung:**
  - Das Bemerken ist über ganze Null-Ströme kalibriert, δ über einen Endpuffer (`buffer_size` Schritte) je Null-Strom. Eine Gesamtrate falscher Öffnungen folgt daraus nicht.
  - δ = 0 entsteht regelgemäß, wenn auf keinem der 20 Null-Puffer ein Kandidat in allen Teilungen gewinnt. Das war bei M3-B auf den Seeds 511 und 512 der Fall.
- **Fehlöffnung „Farbe 0“ unter `global`, Seed 510:**
  - Sie geschah beim ersten Erklären, Episode 110, mit Gewinn 0,0033 bei δ = 0,0019.
  - Wiederholtes Testen oder δ = 0 sind dafür keine nachgewiesene Ursache.
  - Grenzen sind die Zeilenabhängigkeit der Kreuzvalidierung und die adaptiven Zusatzöffnungen, deren Fehlerniveau nicht gesondert kalibriert ist.

**Bisherige Nutzung der Hauptlauf-Seeds 400–409:** Geprüft wurden die verfügbaren Aufzeichnungen:
- die Ergebnisordner im Repo (`results/pilot`, `confirm`, `confirm_510`, `evo`; kein `results/main`);
- die Git-Historie des Branches;
- die Befehlsprotokolle dieser Arbeitssitzung und aller ihrer Teilagenten.

Ergebnis:
- **Keine Experiment- oder Prämissenrechnung mit 400–409 gefunden.**
- **Testläufe:** echte Läufe verwenden die Seeds 0, 1 und 3 mit der Mini-Konfiguration.
- **Auswertungstests:** Sie nutzen 400–409 nur als Nummern synthetischer Ergebnisdateien.
- **Einzige Ausführung mit 400–409 auf der Kommandozeile:** `analyze --confirm`, um zu prüfen, dass diese Seeds abgewiesen werden; das geschieht vor jedem Laden.
- **Übrige Rechnungen dieser Sitzung:**
  - Diagnose, Pilot und Evolution liefen auf Seed 0 und 500–504.
  - Die Bestätigungen liefen auf 500–504 und 510–514.
  - Prüf- und Testläufe der Umsetzung und der Reviews mit Mini-Konfiguration nutzten die Seeds 0–8, 900/901 und 910/911.
- **Nicht prüfbar:** Rechnungen außerhalb dieser Sitzung, etwa auf dem Rechner des Nutzers, in anderen Sitzungen oder in anderen Werkzeugen. Das Review vom 04.10.2026 (`docs/REVIEW-2026-10-04.md`) gibt an, dass dort kein Hauptlauf lief. Ein Nachweis dafür liegt nicht vor.

**Voraussetzungen für das Einfrieren und den Hauptlauf:**
1. **Hauptlauf** ausschließlich auf den Seeds 400–409, mit der eingefrorenen `pilot_config.json`. Seeds mit gescheiterter Prämisse werden berichtet und nicht ersetzt.
2. **Beim Einfrieren festhalten:**
   - die Konfiguration (`frozen_config.json`) und die Code-Prüfsummen (`freeze.sha256`), beides schreibt `freeze write`;
   - die Umgebung samt Fingerabdruck. Diese Zeile kommt mit Datum in dieses Protokoll:
     ```bash
     OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 python -c "import json; from farbversuch.run import env_block, fingerprint; print(json.dumps({'env': env_block(), 'fingerprint': fingerprint()}, indent=1))"
     ```
   - Jede Ergebnisdatei des Hauptlaufs enthält dazu ihren eigenen `env`-Block und `fingerprint`.
3. **Auswertung unverändert:**
   - P2 zählt die richtige Zuschreibung; Zusatzöffnungen heben sie nicht auf, sie zählen als Fehlzuschreibungen.
   - P4 zensiert Nichttreffer am Horizont 300.
   - P5 vergleicht Trefferquoten.
4. **Maschine:**
   - Die Bestätigung 510–514 lief vollständig auf „Intel(R) Xeon(R) Processor @ 2.80GHz“.
   - Nach den Container-Neustarts meldet der Container am 05.10.2026 „@ 2.10GHz“.
   - Der Fingerabdruck enthält die CPU. Ein Hauptlauf, der nach einem Neustart auf anderer Hardware weiterläuft, rechnet seine Zwischenstände deshalb neu, statt Ergebnisse zu mischen. Seine Laufzeit kann dadurch deutlich steigen.
   - Der Hauptlauf muss vollständig auf einer Maschine laufen (Spec v2 §8.5).

## Einfrieren (05.10.2026, 20:55)

Freigegeben durch den Nutzer am 05.10.2026: einfrieren und Hauptlauf 400–409 in diesem Container starten.

- **Code-Stand:** `9153086`. Arbeitsstand sauber, `python -m pytest -q -m "not slow"`: 333 passed, 29 deselected.
- **Befehl:** `python -m farbversuch.freeze write --config farbversuch/pilot_config.json`. Danach meldet `freeze verify` „OK“.
- **Eingefroren:**
  - `frozen_config.json`, bytegleich mit `pilot_config.json`;
  - `freeze.sha256` mit 35 Einträgen: 32 `*.py`-Dateien einschließlich Tests, dazu `requirements.txt`, `pytest.ini` und `frozen_config.json`. SHA-256 dieser Datei: `30c2657b69b58657aeeb6905d803831e9168258552db9f70ecff692c9c56fb45`.
- **Umgebung und Fingerabdruck** auf der Maschine des Hauptlaufs:

```json
{
 "env": {
  "OMP_NUM_THREADS": "1",
  "OPENBLAS_NUM_THREADS": "1",
  "MKL_NUM_THREADS": "1",
  "VECLIB_MAXIMUM_THREADS": "1",
  "BLIS_NUM_THREADS": "1",
  "numpy": "2.4.6",
  "blas": "scipy-openblas 0.3.31.188.0",
  "python": "3.11.15",
  "machine": "x86_64",
  "cpu": "Intel(R) Xeon(R) Processor @ 2.80GHz"
 },
 "fingerprint": "51ddfec05d28d488d854f04f622a16fff63660a889430e865880d8042b302c68"
}
```

Der Fingerabdruck ist identisch mit dem der Bestätigung 510–514 (`51ddfec…`). Code und Umgebung sind also dieselben wie dort. Die Ergebnisdateien des Hauptlaufs tragen ihn je Seed.

## Hauptlauf 400–409 (05./06.10.2026, eingefrorene Konfiguration)

**Lauf:**
- Konfiguration: `frozen_config.json`, Code-Stand `b9589ce`, `--jobs 4`.
- Laufzeit: Start 05.10. 20:56:07, Ende 06.10. 00:31:53, ohne Unterbrechung oder Neustart.
- Fingerabdruck auf allen 10 Seeds identisch (`51ddfec…`), gleich dem beim Einfrieren protokollierten. `freeze verify` nach dem Lauf: OK. `analyze` meldet keine Warnung.

**Vorregistrierte Auswertung** (`results/main_report.md`, Urteile nur für genau 400–409):

| Vorhersage | Ergebnis | Zahlen |
|---|---|---|
| P1 Prämissen | erfüllt | 10/10 (Invarianz 0,952–0,978) |
| P2 M3-B schreibt `red` richtig zu | erfüllt | 10/10 (Schwelle ≥ 9) |
| P3 M3-B öffnet bei `global` nichts | **nicht erfüllt** | 6/10 (Schwelle ≥ 9) |
| P4 M3-A langsamer oder mehr Fehlzuschreibungen | erfüllt | Latenz M3-A 182 gegen M3-B 49 Episoden (zensiert am Horizont). Fehlzuschreibungen M3-A 10, M3-B 11. |
| P5 M3-B mindestens so treffsicher wie S1-B | erfüllt | Treffer bei `red`: M3-B 10, S1-B 9 |

**Abbruchkriterium: ausgelöst.** M3-B öffnet bei `global` in 4/10 Seeds ein Merkmal; das Kriterium greift ab mehr als 3. Die richtige Zuschreibung bei `red` (10/10) liegt dagegen weit über der Abbruchgrenze (< 5).

**Beobachtungen** (reine Zahlen, ohne Deutung; jede Deutung oder Änderung ist nachträgliche Erkundung):

- **M3-B unter `red`:**
  - Zuschreibung bei Episode 110–200, also Latenz 10–100, im Mittel 49.
  - Zusätzliche Öffnungen gab es in 6 Seeds: „Ziel“ 3×, weitere Farben 4×.
- **M3-B unter `global`:**
  - Die Fehlöffnungen:

    | Seed | Merkmal | Episode | Gewinn | δ |
    |---|---|---|---|---|
    | 400 | „Farbe 2“ | 220 | 0,0017 | 0 |
    | 403 | „Ziel“ | 390 | 0,0014 | 0,0006 |
    | 405 | „Farbe 0“ | 220 | 0,0014 | 0 |
    | 409 | „Farbe 0“ | 180 | 0,0015 | 0,0011 |

  - Alle vier liegen nach dem ersten Erklären: Bemerkt wurde jeweils bei Episode 120–180.
  - Zum Vergleich: Die richtigen Öffnungen von „Farbe 0“ unter `red` hatten Gewinne von 0,004 bis 0,041.
- **M3-B unter `none` und `walls`:** Unter `none` kein Fehlalarm. Unter `walls` 1 Fehlzuschreibung.
- **Vergleichssysteme:**
  - M3-A schreibt `red` in 5/10 Seeds richtig zu.
  - S1-B schreibt in 9/10 Seeds richtig zu, macht aber 17 Fehlzuschreibungen unter `global`.
  - S1-A schreibt in 8/10 Seeds richtig zu.

An Code, Konfiguration, Schwellen und Auswertung wurde nichts geändert. Die Seeds 400–409 sind verbraucht.

## Nachträgliche Erkundung: Diagnose der M3-B-Fehlöffnungen (06.10.2026)

**Nachträgliche Erkundung nach Spec v2 §8.6** auf den verbrauchten Seeds 400–409. Am v2-Ergebnis ändert sie nichts. Code, Konfiguration und `freeze.sha256` sind unverändert; `freeze verify`: OK.

**Ablauf:**
- **Skript:** `results/nachtrag_diagnose/diag.py.txt`. Es ändert nichts am Repo.
- **Lauf:** im Arbeitsordner, je Seed ein Prozess mit einem BLAS-Thread, bis zu 4 gleichzeitig, je etwa 16 Minuten.
- **Neu gerechnet:** Phase 1 nur für M3-B, also Routine, Vorwärtsmodell, Übungs-Ontologie, Null-Ströme, δ und `p_global`, alles deterministisch mit den Seeds des Hauptlaufs. Ein neues Training mit anderen Einstellungen ist das nicht.
- **Neue Zufallsströme** gab es nur für den Großtest, mit eigenem Tag 99.

**Ergebnis (Rohdaten `results/nachtrag_diagnose/out_*.json`):**
- **Nachbau exakt:** Übungs-Ontologie, δ, `p_global` und jede Öffnung unter `global` und `red` nach Merkmal, Episode und Gewinn.
- **Großtest `global`** (3000 Episoden je Seed): Kein Kandidat ist in allen Teilungen positiv, der größte mittlere Gewinn ist 0,00011.
- **Erzwungenes Erklären** auf den 20 Null-Strömen von E = 110 bis 400:
  - Mit dem v2-δ öffnen 5–17 von 20 Strömen etwas (Teilung nach Zeilen), bei Teilung nach Episoden 11–18.
  - Serien-δ: Zeilen 0,0023–0,0037, Episoden 0,0037–0,0068.
- **Adaptive Nachspielung mit Serien-δ**, bei gleicher Teilung für Gewinn und Schwelle:
  - `global`: 0/10 Seeds mit Öffnung;
  - `red`: 10/10 erste Öffnung „Farbe 0“, keine Zusatzöffnung;
  - Latenz im Mittel 49 (Zeilen) bzw. 54 (Episoden).
- **Nicht gerechnet:**
  - Prüfpunkte vor E = 110, zulässig wären 37–38 je Strom ab E = 30/40;
  - `walls` und `none`;
  - M3-A, S1-B und S1-A;
  - Zusatzöffnungen mit eigener Basis.

**Einordnung:** Die Regel wurde auf denselben Seeds abgeleitet und angesehen. Das ist keine Evidenz für eine v3.

**Korrektur einer früheren mündlichen Aussage:** Der Vergleich „Episodenteilung macht δ doppelt so groß (0,0062) und verfehlt damit den kleinsten echten Gewinn (0,0041)“ verglich Größen aus verschiedenen Teilungen. Er ist ungültig.

**Weiter:**
- Entwurf `docs/superpowers/specs/2026-10-06-farb-wiederoeffnung-v3-design.md`; Entscheidungen dort in §12.
- Für eine v3 vorgesehen: 520–524 (Bestätigung) und 600–609 (Hauptlauf).
- Nichtnutzung am 06.10.2026 geprüft:
  - Ergebnisordner, Git-Historie, alle Befehlsprotokolle dieser Sitzung und ihrer Teilagenten sowie der Arbeitsordner;
  - beide Bereiche kommen nur als vorgeschlagene Nummern in Texten vor.

## Entscheidungen zu v3 (07.10.2026)

Der Nutzer hat die Entscheidungen E1–E8 des v3-Entwurfs getroffen, alle wie empfohlen. Einzelheiten stehen in Spec v3, §12.
- **Kern:** Serienkalibrierung (E1). Die Teilung bleibt bestätigend nach Zeilen, die Teilung nach Episoden läuft als Nebenauswertung mit (E2).
- **Bewertung:** Nur die erste Öffnung zählt (E3). S1 öffnet höchstens ein Merkmal je Runde (E8).
- **Systeme:**
  - M3-A nur im Hauptlauf (E4);
  - S1-A nur beschreibend mit der unkalibrierten v2-Regel (E5).
- **Seeds:** Bestätigung 520–524, Hauptlauf 600–609 (E7).
- **Nächster Schritt:** Entwicklungsprüfungen D1–D3 auf verbrauchten Seeds (E6). Ihr Ergebnis ist keine Evidenz. Es darf die Varianten nur mit erneuter Entscheidung des Nutzers ändern.

## Entwicklungsprüfungen D1–D3 für v3 (07.10.2026)

Freigegeben mit E6. Gerechnet auf den verbrauchten Seeds 400–409 und 510–514. Das sind Entwicklungsdaten, keine Evidenz. Daten, Skript und Auswertung: `results/entwicklung_v3/`. Code und Freeze von v2 sind unverändert; `freeze verify`: OK.

**Prüfgerüst:** Es baut v2 auf allen 15 Seeds in allen vier Bedingungen exakt nach, Bemerken und Öffnungen von M3-B und S1-B.

**Ergebnis:**
- **M3-B mit Serien-δ₁:**
  - `red`: 15/15 richtig.
  - `global`: Zeilen 1/15 falsch (Seed 510), Episoden 0/15.
  - `walls` und `none`: 0.
  - Zusatzöffnungen: 0.
  - Latenz 400–409: 51 (Zeilen) bzw. 63 (Episoden).
- **Abstände:**
  - δ₁ wird meist von frühen Runden mit kleinem Puffer bestimmt (E = 30–90).
  - Die knappste richtige Öffnung liegt beim 1,09-Fachen (Zeilen) bzw. 1,06-Fachen (Episoden) von δ₁.
- **S1-B:**
  - Holm-p als Serienstatistik ist unbrauchbar: Die Schwelle liegt auf der Untergrenze der Permutationen, S1 öffnet nie.
  - Die stetige z-Variante gibt `red` 14/15 und `global` 0/15.
- **D3, M3-A:** etwa 39 min je Null-Strom, also etwa 13 CPU-Stunden je Seed.

**Offen, Entscheidung des Nutzers nötig:**
- E9: S1 auf der z-Statistik statt auf Holm-p.
- E10: Umgang mit kleinen Puffern: so lassen, erst bei vollem Puffer erklären, oder den Gewinn auf die Puffergröße normieren.
- E2 erneut ansehen, angesichts von Seed 510.

## E10: Auswahlregel, festgelegt vor dem Rechnen (08.10.2026)

Auftrag des Nutzers vom 08.10.2026:
- E10(b) und E10(c) auf allen 15 verbrauchten Seeds nachrechnen, mit beiden Teilungen und allen vier Bedingungen. Die bisherige Regel (a) bleibt Referenz.
- Dazu werden berichtet: Pufferfüllzeit, erste Öffnung, Latenz seit dem Wechsel und der Verlauf des richtigen Kandidaten bei unveränderter Übungs-Ontologie.
- E10 wird für M3-A und M3-B einheitlich spezifiziert.
- Es kommen keine weiteren Varianten dazu, und es werden keine frischen Seeds benutzt.

**Varianten**, jeweils in Kalibrierung und Einsatz gleich. n ist die Zahl der Pufferschritte im Prüfpunkt:

| Variante | Erklären bei | Statistik | Schwelle | Öffnen, wenn (alle Teilungen > 0 und) |
|---|---|---|---|---|
| (a) | n ≥ 500 | G | δ₁ = Maximum von G über Runden und Ströme | Mittel > δ₁ |
| (b) | nur bei vollem Puffer, n = 2000 | G | δ₁ = Maximum von G über diese Runden | Mittel > δ₁ |
| (c) | n ≥ 500 | n · G | κ₁ = Maximum von n · G | n · Mittel > κ₁, also Mittel > κ₁/n |

Das Bemerken ist in allen drei Varianten unverändert.

**Auswahlregel.** Gewählt wird unter den 6 Kombinationen aus Variante und Teilung, nur auf den 15 Entwicklungs-Seeds, bewertet nach Spec v3 §8 (erste Öffnung):
1. **Zulässig** ist eine Kombination nur mit:
   - `red` richtig in mindestens 14/15 Seeds;
   - `global` mit Öffnung in höchstens 1/15;
   - `walls` mit Öffnung in höchstens 1/15;
   - `none` mit Öffnung in 0/15.
2. **Unter den zulässigen gewinnt der größte kleinste Abstand** der richtigen ersten Öffnung unter `red`. Abstand heißt: Gewinn geteilt durch die Schwelle in der Öffnungsrunde, gemessen wird das Minimum über die Seeds.
3. **Gleichstand innerhalb von 10 %** des besten Werts aus Schritt 2 wird nacheinander so aufgelöst:
   - weniger Öffnungen unter `global`;
   - kleinerer größter Abstand unter `global`, also bester Gewinn geteilt durch die Schwelle, maximal über Seeds und Runden;
   - kleinere mittlere Latenz unter `red`;
   - Zeilen vor Episoden;
   - (a) vor (c) vor (b).
4. **Ist keine Kombination zulässig,** bleibt (a) mit Zeilen, und der Nutzer entscheidet.

E9 (Statistik für S1) ist nicht Teil dieser Auswahl.

## E10: Ergebnis und Variantenwahl (08.10.2026)

Gerechnet nach der vorab festgelegten Regel (Abschnitt oben, Commit `1c02884`) auf den 15 verbrauchten Seeds, mit beiden Teilungen und allen vier Bedingungen. Daten und Einzelheiten: `results/entwicklung_v3/e10/`. Entwicklungsdaten, keine Evidenz.

**Nachbau:** auf allen Seeds und Bedingungen exakt. v2 baut nach, und (a) liefert die D1-Öffnungen.

| Kombination | `red` richtig | Latenz | kleinster Abstand `red` | `global` | `walls`/`none` |
|---|---|---|---|---|---|
| (a) Zeilen | 15/15 | 45,3 | 1,09 | 1 | 0/0 |
| (a) Episoden | 15/15 | 54,0 | 1,06 | 0 | 0/0 |
| (b) Zeilen | 15/15 | 46,0 | 1,93 | 1 | 0/0 |
| (b) Episoden | 15/15 | 48,0 | 1,19 | 0 | 0/0 |
| (c) Zeilen | 15/15 | 44,0 | 1,45 | 1 | 0/0 |
| (c) Episoden | 15/15 | 48,0 | 1,19 | 0 | 0/0 |

**Weitere Befunde:**
- **Pufferfüllzeit:** Die Null-Ströme sind voll ab E = 100–150 (Median 130), die Einsatzströme ab E = 110–140 (Median 120).
- **Latenz:** Sie wird überwiegend vom Bemerken bestimmt. Nur in 2–8 von 15 Seeds liegt die erste Öffnung 10–50 Episoden nach dem Bemerken.
- **Verlauf von „Farbe 0“ unter `red`** (Basis = Übungs-Ontologie, Zeilen):
  - erstmals in allen Teilungen positiv bei E = 110–150;
  - bei E = 200 bei 0,027–0,062;
  - vor dem Wechsel −0,010 bis 0,0033.
- **Seed 510, `global`:** Die Öffnung bei E = 110 kommt in allen Zeilen-Varianten vor. Ihr Gewinn steckt schon in den gemeinsamen Daten vor dem Wechsel; das ist ein null-artiger Ausreißer im Rahmen der Grenze von §4.

**Auswahl:**
- Alle 6 Kombinationen sind zulässig.
- Den größten kleinsten `red`-Abstand hat (b) Zeilen mit 1,93. Keine andere Kombination liegt innerhalb von 10 % (Grenze 1,73).
- **Gewählt: E10(b), Teilung nach Zeilen.** E2 bleibt damit unverändert.
- Eingetragen in Spec v3 §3.3, einheitlich für M3-A und M3-B, sowie in §12.

**Nebenwirkung:** Die Serienkalibrierung von M3-A sinkt auf etwa 10 CPU-h je Seed, vorher etwa 13.

**Festgehalten zur Transparenz:**
- Die Regel gewichtet den `red`-Abstand vor der Zahl der `global`-Öffnungen.
- Die Episoden-Varianten hätten Seed 510 vermieden, haben aber kleinere `red`-Abstände (1,06–1,19).

**Offen:** E9.

## E9: Statistik für S1 (10.10.2026)

**Entscheidung des Nutzers:** S1-B läuft in v3 auf dem standardisierten Unterschied z, über die Serie kalibriert (z₁ = Maximum der 20 Null-Ströme), nicht auf dem Holm-adjustierten p-Wert. Es öffnet höchstens ein Merkmal je Runde, das mit dem größten z, und nur bei z > z₁.

**Grund** (Entwicklungsbefund D2):
- Der Holm-p-Wert liegt auf den Null-Strömen meist an der Untergrenze der Permutationen. S1 hätte nie geöffnet (`red` 0/15).
- Die z-Statistik: `red` 14/15, `global`, `walls` und `none` je 0.

**Unverändert bleiben** das Vor-Öffnen von S1 (v2-Permutationstest, 1000 Permutationen) und S1-A, unkalibriert und nur beschreibend (E5).

Eingetragen in Spec v3 §7.1, §10 und §12. Damit sind E1–E10 entschieden. Als Nächstes folgt der Umsetzungsplan.
