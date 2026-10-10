# Handover Farbversuch (Stand 06.10.2026: Hauptlauf 400–409 und Bericht abgeschlossen)

Für die nächste Claude-Sitzung. Dieses Dokument soll genügen, um ohne weitere Vorgeschichte weiterzuarbeiten. Hintergrund in `docs/PROJEKTBESCHREIBUNG.md`, alle Läufe und Änderungen in `farbversuch/PROTOKOLL.md`.

Repo `aporia-evo/tths`, Branch `claude/dreamy-wozniak-7xt321`. Es wird nur auf diesem Branch gearbeitet.

## Kurzfassung

**Hauptlauf abgeschlossen (06.10.2026).** Eingefroren mit Commit `b9589ce`, Hauptlauf 400–409 ohne Unterbrechung, `freeze verify` OK.
- **Vorregistriertes Ergebnis** (`farbversuch/results/main_report.md`, PROTOKOLL „Hauptlauf 400–409“):
  - P1 erfüllt (10/10), P2 erfüllt (10/10), **P3 nicht erfüllt (6/10)**, P4 erfüllt, P5 erfüllt.
  - **Abbruchkriterium ausgelöst:** M3-B öffnet bei `global` in 4/10 Seeds ein Merkmal, das Kriterium greift ab mehr als 3.
- **Bericht:** `farbversuch/BERICHT.md` (Gliederung nach Spec v2 §11).
- **Weiter:** Was jetzt noch geändert oder untersucht wird, ist nachträgliche Erkundung oder eine neue Version (v3) und muss auf frischen Seeds geprüft werden. Die Seeds 400–409 sind verbraucht.
- **Nachträgliche Diagnose und v3-Entwurf (06.10.2026):**
  - Diagnose der M3-B-Fehlöffnungen auf 400–409: `farbversuch/results/nachtrag_diagnose/`, PROTOKOLL letzter Abschnitt, BERICHT §5.
  - v3-Entwurf, nicht freigegeben: `docs/superpowers/specs/2026-10-06-farb-wiederoeffnung-v3-design.md`.
  - Die Entscheidungen E1–E8 (07.10.2026) und E10 (08.10.2026, Variante (b) nach vorab festgelegter Regel) stehen in dessen §12.
  - Entwicklungsprüfungen D1–D3 und E10: `farbversuch/results/entwicklung_v3/`.
  - E9 (10.10.2026): S1 läuft auf der z-Statistik. Damit sind alle Entscheidungen getroffen; als Nächstes folgt der Umsetzungsplan.
  - Bis zur Freigabe gilt: keine Umsetzung, keine Läufe auf frischen Seeds (vorgesehen 520–524 und 600–609), kein Einfrieren.

Die folgenden Punkte beschreiben den Stand vor dem Hauptlauf und bleiben als Referenz stehen.


- **Code:** v2 ist fertig, geprüft und unverändert seit Merge `b5d573f`.
- **Pilot und Tuning:** Der Pilot (Seed 0) und die Entwicklung der Trainingsparameter (Seeds 0, 500–504) sind abgeschlossen. Die Konfiguration steht in `farbversuch/pilot_config.json`.
- **Bestätigung:** Auf den frischen Seeds 510–514 ist die Methode nach der gemeinsamen 4/5-Regel bestätigt. Die Vorhersagen P2–P5 sind damit **nicht** geprüft; das geschieht erst im Hauptlauf.
- **Entscheidung des Nutzers vom 05.10.2026 (A):** die bestehende Methode einfrieren, ohne weitere Bestätigungsrunde. Algorithmen, Hyperparameter, Schwellen und Vorhersagen bleiben unverändert. Präzisierungen ohne Regeländerung stehen in Spec v2, Anhang B.
- **Nächste Schritte, je nur auf ausdrückliche Anweisung des Nutzers:**
  1. Einfrieren (`freeze write`) und die Umgebung festhalten.
  2. Hauptlauf auf den Seeds 400–409.
  3. Auswertung und Bericht.
- **Nicht noch einmal laufen lassen:** Pilot und Bestätigung sind erledigt. Insbesondere `pilot_config.json` **nie** mit `Config().to_json(...)` neu erzeugen. Das würde die abgestimmte Konfiguration mit den Standardwerten überschreiben.

## Bindende Dokumente

- **Spezifikation v2:** `docs/superpowers/specs/2026-10-03-farb-wiederoeffnung-v2-design.md`. Sie ist eigenständig und bindend.
  - Anhang A nennt die Änderungen gegenüber v1 mit Begründung.
  - Anhang B ist der Review-Nachtrag vom 05.10.2026: Kalibrierung, Grenzen, Aussagegrenzen und Auswertungsregeln, ohne Regeländerung.
- **Plan v2:** `docs/superpowers/plans/2026-10-03-farb-wiederoeffnung-v2.md`, dort die „Festlegungen“ 1–10 (RNG-Schlüssel, Residualisieren, Öffnungsregel, δ-Gewinn, P1b-Messung, Bestätigung, `total_sec`, Ergebnis-JSON). Der v1-Plan gilt mit seinen Festlegungen weiter, soweit der v2-Plan nichts anderes sagt.
- **Protokoll:** `farbversuch/PROTOKOLL.md`. Es enthält alle Pilot-Änderungen, Raster und Evolution, beide Bestätigungen, die Entwicklungsgeschichte, die Prüfung der bisherigen Nutzung der Seeds 400–409 und die Voraussetzungen fürs Einfrieren.
- **v1 ist Geschichte:** `docs/superpowers/specs/2026-10-03-farb-wiederoeffnung-design.md` und `docs/superpowers/plans/2026-10-03-farb-wiederoeffnung.md`. Wo sie von v2 abweichen, gilt v2.
- Bei Widerspruch zwischen Doku und Code: nicht raten, den Nutzer fragen.

## Stand

- **Code:**
  - Die Aufgaben 1–9 des Plans v2 sind umgesetzt, dazu die Fix-Welle nach der Abschlussprüfung (Entscheidungen D1, D2 und weitere Korrekturen).
  - Das Review des Nutzers (Commit `436c621`, `docs/REVIEW-2026-10-04.md`) ist mit Merge `b5d573f` eingeflossen.
  - Seitdem hat sich keine `*.py`-Datei mehr geändert. Siehe „Abweichungen und Festlegungen“.
- **Tests** (4 Kerne, Python 3.11.15, numpy 2.4.6):
  - `python -m pytest -q` gibt **362 passed**, ohne Warnungen.
  - `python -m pytest -q -m "not slow"` gibt **333 passed, 29 deselected**.
- **Läufe** (Einzelheiten im Protokoll):
  - `results/pilot`: Seed 0 mit wd 0,01.
  - `results/confirm`: 500–504, nicht bestätigt.
  - `results/evo`: Raster und Evolution.
  - `results/confirm_510`: 510–514, bestätigt.
- **Offen:** Einfrieren, Hauptlauf, Bericht (feste Gliederung nach Spec v2 §11). `farbversuch/frozen_config.json`, `farbversuch/freeze.sha256` und `farbversuch/results/main/` gibt es noch nicht.

### Was v2 gegenüber v1 ändert (Kurzfassung der Spec)

- **Übungs-Ontologie:** Am Ende der Übungsphase öffnet jedes der vier Systeme mit seinem eigenen Erklärverfahren bis zu 8 Merkmale vor (Übungspuffer = letzte 2000 Schritte der Vorwärtsdaten; M3 mit fester Mindestverbesserung 0,01, S1 mit Holm). Sie gehen ins Basismodell des Erklärens ein, werden im Einsatz nicht erneut getestet und zählen nie als „geöffnet“. Das Bemerken bleibt unverändert.
- **Residualisieren:** Jeder Kandidat wird je Teilung gegen das Basisdesign regressiert, nur der Rest zählt. Duplikate und Linearkombinationen gewinnen genau 0.
- **Mindestverbesserung δ:** Geöffnet wird nur bei Verbesserung in allen 5 Teilungen und Mittel > δ. δ je M3-System = größter der 20 Null-Gewinne.
- **Kalibrierung:** Null-Ströme haben 400 Episoden. Alle Schwellen und δ sind der **größte** der 20 Null-Werte. Erwartete Fehlalarmrate des **Bemerkens** pro neuem Strom ≈ 1/21 ≈ 4,8 %. Das ist keine Gesamtrate falscher Öffnungen über einen ganzen Einsatz: δ stammt je Null-Strom aus einem einzigen Puffer, im Einsatz wird aber nach dem Bemerken wiederholt erklärt, und auch Holm gilt je Erklärrunde (REVIEW-2026-10-04, Punkt 2).
- **P1b „weitgehend geschlossen“:** Restanteil ≤ 0,15 und Verschiebung von z ≤ 0,25 (500 Positionen). Scheitert P1 oder P1b, entfällt der Seed („Prämisse nicht erfüllt“). Die Prämisse wird direkt nach Routine und Vorwärtsmodell geprüft; scheitert sie, laufen weder Übungs-Ontologie, Null-Ströme und δ noch `p_global` und die Bedingungen (Entscheidung D2).
- **S1:** Permutationen Arm B 1000, Arm A 25.000 (blockweise zu 1000), damit S1-A bei 1192 Kandidaten überhaupt ablehnen kann.
- **Zuschreibung bei `red`** zählt nur nach dem Wechsel.
- **Bestätigung** vor dem Einfrieren, Auswertung mit `analyze --confirm`. Bestätigt ist die Methode, wenn in mindestens 4 von 5 Seeds alle drei Kriterien gleichzeitig gelten (Entscheidung D1). 500–504: nicht bestätigt; 510–514 (nach Entwicklung auf 0 und 500–504): bestätigt.
- **Paralleler Treiber** über Seeds und Bedingungen mit Fortsetzen nach Abbruch.

### Code-Überblick

`farbversuch/`: `world.py` (Welt), `routine.py`, `forward.py` (Vorwärtsmodell), `monitor.py` (Bemerken, Erklären, Vor-Öffnen, Kalibrierhilfen), `closure.py` (P1b), `run.py` (Phase 1, Prämissen, Einsatz, CLI mit Treiber), `analyze.py` (Bericht, `--confirm`), `freeze.py`, `config.py`, `seeds.py`. Tests unter `farbversuch/tests/`. `routine.py`, `forward.py` und `monitor.py` greifen nie auf Bedingung, Wechselzeitpunkt oder `C_SPECIAL` zu (AST-Test in `test_isolation.py`).

## Nächste Schritte und Befehle

Alle Befehle im Repo-Wurzelordner.

### 0. Einrichten

```bash
git fetch origin && git checkout claude/dreamy-wozniak-7xt321 && git pull
python -m pip install -r requirements.txt        # numpy>=2.0, pytest>=8
python -m pytest -q -m "not slow"                 # erwartet: 333 passed, 29 deselected
```

Kernzahl für `--jobs` bestimmen (physische Kerne, nicht mehr; `nproc` zählt oft Hyperthreads mit):

```bash
JOBS=$(lscpu -p=CORE,SOCKET | grep -v '^#' | sort -u | wc -l)    # ohne lscpu: nproc
JOBS=$(( JOBS > 20 ? 20 : JOBS ))                                   # Bestätigung: mehr als 20 bringt nichts
```

Was `--jobs` bewirkt: Der Treiber hat drei Stufen, jede mit eigenem Prozess-Pool, und jede Stufe wartet auf alle ihre Aufgaben.

| Stufe | Aufgabe | Parallel über | Sinnvoll höchstens |
|---|---|---|---|
| 1 | Vorbereitung: Phase 1, Prämissen, `p_global` | Seeds | Zahl der Seeds (bei 500–504: 5) |
| 2 | Einsatz je Bedingung | Seed × Bedingung | 4 × Zahl der Seeds (bei 500–504: 20; Pilot: 4) |
| 3 | Ergebnisdatei je Seed | Seeds | Zahl der Seeds |

Die BLAS-Threads setzt der Code selbst auf 1. Mehr Jobs als physische Kerne bringen nichts. Der Arbeitsspeicher je Prozess ist nicht gemessen.

### 1. Erledigt: Pilot, Entwicklung, Bestätigungen

Nicht wiederholen. Ergebnisse und Begründungen stehen in `farbversuch/PROTOKOLL.md`, die Berichte in `farbversuch/results/pilot_report.md`, `confirm_report.md` und `confirm_510_report.md`.

**Verbrauchte Seeds:** 0, 500–504 und 510–514. Sie werden für keine Bestätigung und keinen Hauptlauf wiederverwendet.

**Bestätigung 510–514, berichtigte Zahlen:**
- **M3-B unter `red`:** öffnet „Farbe 0“ bei Episode 130, 140, 140, 130 und 130, also 30–40 Episoden nach dem Wechsel, im Mittel 34.
- **M3-A unter `red`:** 3/5 Treffer, je bei Latenz 40. Der Mittelwert 144 zählt 2 Nichttreffer mit 300.
- **Fehlzuschreibungen insgesamt:** M3-B 5, M3-A 2.
- **S1-B unter `red`:** ebenfalls 5/5 Treffer.

### 2. Einfrieren (nur auf ausdrückliche Anweisung des Nutzers)

Voraussetzungen und Ablauf, siehe auch PROTOKOLL, „Review-Nachtrag 05.10.2026“:

1. **Arbeitsstand prüfen:** `git status` muss sauber sein, und `python -m pytest -q -m "not slow"` muss grün sein. Keine Quelldatei ändern.
2. **Einfrieren:** Das schreibt `frozen_config.json` (gleich `pilot_config.json`) und SHA-256 aller `*.py` (auch Tests), `requirements.txt`, `pytest.ini` und `frozen_config.json` in `freeze.sha256`. Danach darf sich keine Quelldatei mehr ändern.
   ```bash
   python -m farbversuch.freeze write --config farbversuch/pilot_config.json
   python -m farbversuch.freeze verify          # muss OK ausgeben
   ```
3. **Umgebung und Fingerabdruck** auf der Maschine des Hauptlaufs festhalten und mit Datum ins Protokoll eintragen:
   ```bash
   OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 python -c "import json; from farbversuch.run import env_block, fingerprint; print(json.dumps({'env': env_block(), 'fingerprint': fingerprint()}, indent=1))"
   ```
4. **Abschluss:** `frozen_config.json`, `freeze.sha256` und `PROTOKOLL.md` committen und auf den Branch pushen.

### 3. Hauptlauf 400–409 (nur nach dem Einfrieren und auf Anweisung des Nutzers)

- **Seeds:** ausschließlich 400–409, mit der eingefrorenen Konfiguration. Seeds mit gescheiterter Prämisse werden berichtet und **nicht ersetzt** (Spec v2 §7). Kein weiterer Seed, keine Wiederholung mit anderer Konfiguration.
- **Maschine:** Der ganze Lauf auf einer Maschine (Spec v2 §8.5).
  - Der Fingerabdruck enthält CPU und Umgebung.
  - Wechselt die Hardware nach einem Container-Neustart, wird neu gerechnet statt gemischt. Am 05.10.2026 meldete der Container nach Neustarts eine andere CPU (2,10 statt 2,80 GHz).
- **Jobs:** Stufe 1 nutzt höchstens 10, Stufe 2 höchstens 40 Jobs. `<N>` = Zahl der physischen Kerne, höchstens 40; die Zahl direkt eintragen.
  ```bash
  setsid nohup python -m farbversuch.run --config farbversuch/frozen_config.json --seeds 400-409 --jobs <N> --out farbversuch/results/main < /dev/null > farbversuch/results/main.stdout 2> farbversuch/results/main.log &
  # nach dem Ende:
  python -m farbversuch.freeze verify
  python -m farbversuch.analyze --results farbversuch/results/main --seeds 400-409 > farbversuch/results/main_report.md
  ```
- **Auswertung:** Nur diese Auswertung gibt die vorregistrierten Urteile zu P2–P5 und zum Abbruchkriterium aus.
  - `analyze` prüft dabei das Einfrieren. Fehlt etwas, steht oben im Bericht und auf stderr eine **WARNUNG**.
  - Die Auswertungsregeln sind unverändert (Spec v2 §6/§7, Anhang B.4): Zusatzöffnungen heben P2 nicht auf, P4 zensiert am Horizont 300, und P5 vergleicht Trefferquoten.
- **Danach:** Alles, was nach dem Hauptlauf geändert oder ergänzt wird, ist „nachträgliche Erkundung“ und steht im Bericht getrennt.

### Laufzeit

Gemessen auf 4 Kernen (Intel Xeon, `--jobs 4`) mit der Pilot-Konfiguration, Bestätigung 510–514:
- **Phase 1 je Seed** (Training, Prämisse, Vor-Öffnen, 20 Null-Ströme, δ): 1764–1813 s. Den Großteil davon braucht die δ-Kalibrierung von M3-A, etwa 22 Minuten.
- **Bedingungen je Seed:** `none` und `walls` meist wenige Sekunden. Bemerkt dort ein System etwas, sind es bis etwa 23 Minuten. `red` 3,5–40 Minuten, `global` 33–44 Minuten. M3-A dominiert.
- **Rechenzeit gesamt je Seed** (`total_sec`): 4035–6735 s.
- **Wandzeit für 5 Seeds auf 4 Kernen:** 3 h 27 min, einschließlich zweier Container-Neustarts mit verlorener Arbeit.
- **Schätzung Hauptlauf (10 Seeds, 4 Kerne):** etwa 5–6 Stunden ohne Neustarts.
  - Stufe 1: 3 Runden zu je ~30 min.
  - Stufe 2: ~10,5 Rechenstunden, verteilt auf 4 Kerne.
  - Jeder Container-Neustart kostet die gerade laufenden Aufgaben, bis zu ~45 min.

Wo die Zahlen stehen:
- Je Seed in der JSON-Datei: `phase1_sec` und `total_sec`. `total_sec` ist die Summe über die Prozesse, nicht die Wandzeit.
- Wandzeit: aus den Zeitstempeln im Log (`HH:MM:SS`, ohne Datum) und mit `date` vor dem Start und nach dem Ende notieren.
- Im Bericht: Abschnitt „Kosten“.


### Unterbrechen und Fortsetzen

Ein unterbrochener Lauf lässt sich mit **demselben Befehl** neu starten, aber mit `2>>` statt `2>` für das Log. Das hängt an und lässt die Zeitstempel des ersten Laufs stehen; `2>` würde das Log überschreiben.

- **Vor dem Fortsetzen** prüfen, dass nichts mehr läuft: `pgrep -af farbversuch.run` (Hauptprozess) und `pgrep -af multiprocessing.spawn` (Arbeitsprozesse, auch verwaiste).
- **Lauf im Hintergrund beenden:** `kill -- -<PGID>` beendet den Hauptprozess und alle seine Arbeitsprozesse. Mit `setsid` gestartet, ist die PGID die PID des Hauptprozesses (sie steht auch in `<out>/.lock`); sonst liefert `ps -o pgid= -p <PID>` die PGID. `pkill -f farbversuch.run` trifft nur den Hauptprozess: Die Arbeitsprozesse (Kommandozeile mit `multiprocessing.spawn`) rechnen dann ihre Aufgabe zu Ende und bleiben danach verwaist hängen (so beobachtet). Sie dann ebenfalls mit `kill -- -<PGID>` beenden.
- **Sperre:** Jeder Lauf legt `<out>/.lock` an (PID und Rechnername) und löscht sie am Ende, auch nach einem Fehler. Ein zweiter Lauf auf denselben Ausgabeordner bricht ab und nennt die PID des ersten. Nach `kill`, Absturz oder Neustart der Maschine bleibt die Sperre liegen; sie ist dann **verwaist**: Der nächste Start sieht, dass die PID nicht mehr lebt, übernimmt die Sperre und meldet das auf stderr. Eine Sperre von einem anderen Rechner oder eine unlesbare Sperre lässt sich nicht prüfen; dann bricht der Start ab, und die Datei darf nur von Hand gelöscht werden, wenn sicher kein Lauf mehr auf diesen Ordner schreibt.
- Fertige `seed_<n>.json` mit gleicher Konfiguration **und** gleichem Fingerabdruck werden übersprungen. Liegt dort ein Ergebnis mit anderer Konfiguration oder mit anderem oder fehlendem Fingerabdruck (anderer Code, andere Umgebung), bricht die CLI ab, ohne etwas zu überschreiben, und nennt den Grund je Datei. Eine unlesbare `seed_<n>.json` beendet den Start mit der Aufforderung, sie zu verschieben oder zu löschen.
- Zwischenstände liegen in `<out>/.work` (Vorbereitung je Seed, Ergebnis je Seed und Bedingung). Sie werden nur wiederverwendet, wenn Konfiguration **und** Herkunft übereinstimmen. Die Herkunft ist ein SHA-256 über den Quelltext aller `farbversuch/*.py` (ohne `tests/`) und die Umgebung (Threadvariablen, numpy, BLAS, Python, Maschine, CPU). Anderer Code oder andere Umgebung heißt: Neuberechnung. Eine unlesbare, beschädigte oder unvollständige Zwischendatei (auch ein fremdes Objekt im Pickle, ein anderer Seed oder ein Bedingungsergebnis ohne `result` oder `sec`) zählt als fehlend und wird ebenfalls neu berechnet. Wer `<out>/.work` von Hand löscht (z. B. um Platz zu schaffen), startet danach denselben Befehl, ebenfalls mit `2>>`.
- **Abgestürzter Arbeitsprozess:** Beendet das System einen Arbeitsprozess (Speichermangel, `kill -9`), bricht der Lauf sofort mit einer Meldung und Exitcode 1 ab und nennt den Befehl zum Fortsetzen; fertige Zwischenstände bleiben. Wirft eine Aufgabe eine Ausnahme, startet keine weitere Aufgabe, laufende rechnen zu Ende, dann endet der Lauf mit dem Fehlertext. In beiden Fällen anhalten und den Nutzer fragen, nicht umgehen.
- Die `seed_<n>.json` entstehen erst in Stufe 3, also nachdem **alle** Seeds die Stufen 1 und 2 durchlaufen haben. Nach einem Abbruch in Stufe 1 oder 2 gibt es daher noch keine Ergebnisdateien, aber die fertigen Zwischenstände bleiben erhalten.
- Quelldateien in `farbversuch/` während eines Laufs nicht ändern.

### Ergebnisse committen

Die Ordner `farbversuch/results/<name>/.work`, `*.tmp` (beide stehen in `.gitignore`), `.lock` und `*.stdout` nicht committen. Für den Hauptlauf gezielt hinzufügen:

```bash
git add farbversuch/frozen_config.json farbversuch/freeze.sha256 farbversuch/PROTOKOLL.md
git add farbversuch/results/main/seed_*.json farbversuch/results/main.log farbversuch/results/main_report.md
```

Die Commit-Nachricht endet mit den Attributionszeilen der jeweiligen Sitzung. Gepusht wird nur auf `claude/dreamy-wozniak-7xt321`.

## Früherer Prompt für Claude Scientific (erledigt, nicht mehr verwenden)

Der Prompt für Pilot und Bestätigung 500–504 stand bis Commit `d2134c0` in diesem Dokument. Er ist erledigt und wurde entfernt. Er würde `pilot_config.json` mit Standardwerten neu erzeugen und verbrauchte Seeds wiederverwenden. Für Einfrieren und Hauptlauf gelten die Abschnitte 2 und 3 oben.


## Abweichungen und Festlegungen während der Umsetzung (v2)

Review-Nachtrag vom 05.10.2026, vor dem Einfrieren (Entscheidung A des Nutzers):

- **Keine Änderung** an Code, Algorithmen, Hyperparametern, Schwellen oder Vorhersagen.
- **Berichtigt:** die Zahlen der Bestätigung 510–514 (siehe Abschnitt 1 oben und PROTOKOLL).
- **Begriff:** „Trefferquote auf den Lehrerdaten“ heißt jetzt „Trainingsgenauigkeit“.
- **Neu dokumentiert:** die Entwicklungsgeschichte, einschließlich der ergebnisgeleiteten Wahl der Kreuzvalidierung nach Zeilen. Ebenso die Kalibrierungsgrenzen, die Aussagegrenzen und die Voraussetzungen fürs Einfrieren (Spec v2, Anhang B; PROTOKOLL).

Review des Nutzers vom 04.10.2026 (Commit `436c621`, Begründung und Reproduktionen in `docs/REVIEW-2026-10-04.md`), zusammengeführt mit der Fix-Welle:

- **Prämisse aus Messwerten (`analyze._premise_ok`):** Die Auswertung zählt P1 und P1b nur als erfüllt, wenn `ok` wahr ist **und** alle fünf Messwerte endliche Zahlen sind und die Grenzen der gespeicherten Konfiguration einhalten (fehlende Grenzen: Standardwerte). Ein altes oder widersprüchliches `ok` allein genügt nicht; v1-Ergebnisse ohne P1b-Werte können daher weder die Bestätigung noch die Hauptauswertung bestehen. Das gilt überall, auch für die gemeinsame Bestätigung (D1) und die Nutzbarkeit. Nicht endliche Werte erscheinen im Bericht als „–“.
- **Einfrieren verlangt `frozen_config.json` im Manifest:** Fehlt der Eintrag in `freeze.sha256`, meldet `freeze verify` die Datei (vorher: Erfolg, auch bei geänderter oder gelöschter Konfiguration). Davon profitiert auch die WARNUNG für 400–409 (M5).
- **Wiederaufnahme mit unbrauchbaren Zwischenständen:** Leere, abgeschnittene, unlesbare oder unvollständige `.work`-Dateien werden neu berechnet; Rechenfehler bleiben sichtbar. Im Merge mit M9 zu einem Ladeweg zusammengefasst.
- **M3-Kalibrierung mit derselben Reduktion wie der Monitor:** `m3_trace` mittelt das Fenster direkt statt über kumulative Summen. Vorher konnte die Schwelle in der letzten Stelle unter dem Monitorwert desselben Null-Stroms liegen (Reproduktion: 1.1618018614563417 gegen 1.1618018614563452) und einen Null-Alarm auslösen. Auf `TINY` verschiebt das `m3_threshold` um 4e-16 bis 3e-15; alle anderen Werte sind bitgleich.
- **Review-Punkt 1 (Bestätigungskriterium uneindeutig)** ist durch die Entscheidung des Nutzers D1 vom 04.10.2026 erledigt: gezählt werden Seeds, in denen alle drei Kriterien gleichzeitig gelten.
- **Review-Punkt 2:** Die ≈ 4,8 % gelten für das Bemerken pro Strom, nicht als Gesamtrate falscher Öffnungen über einen ganzen Einsatz (siehe „Was v2 gegenüber v1 ändert“).

Fix-Welle nach der Abschlussprüfung (04.10.2026):

- **D1 Bestätigung zählt gemeinsam (Entscheidung des Nutzers):** Ein Seed zählt nur, wenn alle drei Kriterien zugleich gelten; bestätigt ist die Methode bei mindestens 4 von 5 solchen Seeds. Die Zählungen je Kriterium stehen im Bericht nur zur Information. Spec v2 §8 (mit Zeile in Anhang A) und Plan-Festlegung 8 sind entsprechend präzisiert. Folge: strenger als die Lesart je Kriterium; 5/4/4 je Kriterium kann „nicht bestätigt“ heißen.
- **D2 Prämisse zuerst (Entscheidung des Nutzers):** P1 und P1b werden direkt nach Routine und Vorwärtsmodell geprüft, denn sie hängen nicht von Übungs-Ontologie, δ oder Null-Strömen ab. Scheitert die Prämisse, entfallen Vor-Öffnen, Null-Ströme, Schwellen, δ, `p_global` und die Bedingungen; in der JSON stehen sie als `null`. Ein gescheiterter Pilot ist dadurch schneller fertig. Bei erfüllter Prämisse sind die Ergebnisse bitgleich zu vorher (geprüft auf `TINY` mit Seed 0 und 1).
- **I2 Abgestürzter Arbeitsprozess:** Der Treiber nutzt `ProcessPoolExecutor` statt `multiprocessing.Pool`. Stirbt ein Arbeitsprozess, bricht der Lauf sofort mit Meldung und Fortsetzungsbefehl ab, statt still zu hängen. Bei einer gewöhnlichen Ausnahme rechnen laufende Aufgaben zu Ende (ihre Zwischenstände bleiben), dann endet der Lauf.
- **M3 Fingerabdruck im Ergebnis:** Jede `seed_<n>.json` enthält `fingerprint`. Beim Fortsetzen gelten nur Ergebnisse mit gleicher Konfiguration und gleichem Fingerabdruck als fertig, sonst Abbruch ohne Überschreiben. `analyze` verlangt gleiche Fingerabdrücke über alle Seeds. Folge: Nach einer Änderung von Code oder Umgebung (auch Python-, numpy- oder Maschinenwechsel) lassen sich alte und neue Ergebnisse nicht mischen.
- **M4 Strengere Bestätigung:** `--confirm` verlangt mindestens 5 Seeds, alle ab 500, und nennt sonst die Seeds.
- **M5 Hauptlauf nur eingefroren:** Bei genau den Seeds 400–409 warnt `analyze` laut (oben im Bericht und auf stderr), wenn `freeze verify` Abweichungen meldet oder `frozen_config.json` fehlt oder nicht zur Konfiguration der Ergebnisse passt. Es bricht nicht ab.
- **M6 Sperre:** `<out>/.lock` verhindert zwei Läufe auf demselben Ausgabeordner; eine verwaiste Sperre wird übernommen (siehe „Unterbrechen und Fortsetzen“).
- **M8 Threads und Maschine:** Auch `VECLIB_MAXIMUM_THREADS` und `BLIS_NUM_THREADS` werden auf 1 gesetzt. Der `env`-Block nennt zusätzlich `machine` und `cpu`; beides geht in den Fingerabdruck ein.
- **M9 Dateien:** Ergebnisse und Zwischenstände werden mit `fsync` geschrieben, bevor sie ihren Namen bekommen. Eine beschädigte Zwischendatei wird neu berechnet (Hinweis auf stderr); eine unlesbare `seed_<n>.json` stoppt den Start mit einer klaren Meldung.
- **Kleineres:** mehr Fortschrittszeilen im Log (siehe „Laufzeit“); ein Übungs- oder δ-Puffer kürzer als `buffer_size` ist ein Fehler statt eines still kürzeren Puffers; Nutzbarkeit auch für M3-A; `.work/` und `*.tmp` in `.gitignore`.

Neu in v2 (Entscheidungen der Umsetzung, jeweils mit Auswirkung):

- **S1-Permutationstest auf Raster:** `perm_pvalues` rundet die Überraschungen auf ein Raster 2^-q (relative Abweichung etwa 5e-13 bei 2000 Schritten). Dadurch sind die p-Werte bitgleich für jede Blockgröße (`perm_chunk`), und exakte Gleichstände beim Vergleich der Permutationen hängen nicht mehr an der Reihenfolge der Gleitkommasummen. Der Zufallsstrom bleibt unverändert.
- **P1b nicht endlich:** Ist der Restanteil `nan` (keine Nachbarzelle bleibt übrig) oder die Verschiebung nicht endlich, steht in der JSON `null`, und die Prämisse gilt als nicht erfüllt.
- **Bericht, erwartete Fehlalarmrate:** Die Zeile rechnet (`max_null_alarms` + 1) / (`n_null_streams` + 1). Für v2 ergibt das 1/21 ≈ 4,8 %, die Rate für das Bemerken pro Strom (keine Gesamtrate falscher Öffnungen). Für Ergebnisse mit anderer Konfiguration stimmt die Zeile ebenfalls (v1 mit einem erlaubten Alarm: 9,5 %).
- **Fortsetzen nur bei gleicher Herkunft:** `.work`-Zwischenstände werden nur bei gleicher Konfiguration und gleichem Fingerabdruck von Code und Umgebung wiederverwendet (siehe „Unterbrechen und Fortsetzen“). Das kam aus der Prüfung von Aufgabe 7.
- **Gleiches Ergebnis in beiden Ausführungswegen:** Der parallele Treiber liefert je Seed dasselbe wie das sequentielle `run_seed` (bis auf die `_sec`-Schlüssel). Der Test rechnet die Referenz in einem frischen Prozess mit einem BLAS-Thread, weil der pytest-Prozess mehrere Threads nutzt und die Ergebnisse sich sonst ab der sechsten Stelle unterscheiden.
- **`total_sec`** ist Vorbereitungszeit plus Summe der Bedingungszeiten, in beiden Wegen gleich definiert (Plan v2, Festlegung 9). Es ist keine Wandzeit.
- **Nutzbarkeit** (Spec §6) steht als `gain` an der ersten richtigen Öffnung eines M3-Systems unter `red`; der Bericht zeigt sie je M3-System (M3-B und M3-A). Ergebnisse ohne `gain` zeigen „–“.

Aus v1 und weiter gültig:

- **Zuschreibung bei `red`** zählt nur, wenn die Öffnung nach dem Wechsel liegt (Episode > 100). Die Latenz ist Episode − 100. Frühere Öffnungen zählen als Fehlzuschreibung. Grund: Vor dem Wechsel sind alle vier Ströme identisch. Jetzt steht das auch in der Spec v2 §6.
- **`p_global`:** Das Ergebnis enthält die Kennzeichen `hit` (Toleranz getroffen) und `bracketed` (Zielwert einschließbar, v1-Plan Festlegung 15).
- **BLAS-Threads:** Der Code legt sie selbst auf 1 fest und schreibt Threads, numpy, BLAS, Python, Maschine und CPU in einen `env`-Block jeder Ergebnisdatei. Ergebnisse mit anderer Thread-Zahl unterscheiden sich deutlich. `evaluate` verlangt gleiche Konfiguration und gleiche Umgebung über alle Seeds.
- **Seeds werden geprüft:** Doppelte Seeds weist `parse_seeds` (CLI von `run` und `analyze`) und `evaluate` mit `ValueError` ab. Der Temp-Dateiname je Seed enthält die Prozess-ID.
- **Explorative Auswertung:** `evaluate` gibt die vorregistrierten Urteile (P2–P5, Abbruch) nur für genau die Seeds 400–409 aus (`"preregistered": True`). Bei anderen Seeds (Pilot Seed 0, Bestätigung 500–504) stehen Zahlen und Kennzahlen, die Urteile sind `None`, und der Bericht beginnt mit dem Hinweis „Explorative Auswertung“ und zeigt „–“ statt erfüllt/nicht erfüllt. Das Urteil der Bestätigung (Spec §8) gibt `--confirm` aus.
- **Abstürze im parallelen Treiber:** Löst ein Arbeitsprozess eine Ausnahme aus, startet keine weitere Aufgabe; laufende rechnen zu Ende, dann endet der Lauf mit dem Fehlertext. Wird ein Arbeitsprozess vom System beendet (z. B. Speichermangel, `kill -9`), bricht der Lauf sofort mit Meldung, Exitcode 1 und dem Befehl zum Fortsetzen ab (getestet, Fix-Welle I2). Bereits fertige Zwischenstände in `<out>/.work` bleiben erhalten, und derselbe Befehl (Log mit `2>>`) setzt fort. In beiden Fällen anhalten und den Nutzer fragen, nicht umgehen.
- **Testtoleranz:** Ein Test (`test_warm_start_reaches_same_optimum` in `test_forward.py`) nutzt `tol=1e-8`. Der Löser bleibt bei Standard `tol=1e-6`; die zulässigen Verbesserungen liegen bei ≥ 1e-5, also deutlich über dem Lösungsrauschen.

## Bekannte kleinere Punkte

Bei der Prüfung der Aufgaben bewusst offen gelassen. Sie betreffen den Betrieb:

- **Ergebnisdateien erst am Ende:** Ein Fehler beendet den Lauf (siehe oben). Fertige Seeds warten in Stufe 3 auf die übrigen, also erscheinen die `seed_<n>.json` erst am Ende der Stufen 1 und 2.
- **Quelldateien während eines Laufs:** Der Fingerabdruck wird am Anfang bzw. Ende eines Auftrags von der Platte gelesen. Wer Code während eines laufenden Laufs ändert, bekommt Zwischenstände mit falscher Herkunft. Nicht tun.
- **M3-A im Lauftest:** Die Lauf-Tests (`TINY`) lassen M3-A weg. In den echten Läufen (Pilot, 500–504, 510–514) liefen Vor-Öffnen und δ-Kalibrierung für M3-A fehlerfrei durch.
- **Container-Neustarts:** Während der Bestätigung 510–514 wurde der Container zweimal neu gestartet. Die Fortsetzung mit demselben Befehl hat Vorbereitung und fertige Bedingungen übernommen.
  - Nach den Neustarts meldete der Container eine andere CPU.
  - Läuft der Hauptlauf auf anderer Hardware weiter, verhindert der Fingerabdruck ein Mischen, die Arbeit wird neu gerechnet.
  - Den Hauptlauf daher möglichst auf einer stabilen Maschine starten.
- **Testlücke ohne bekannten Code-Fehler:** Die P1b-Tests prüfen nicht gegen Informationslecks (z. B. eine Darstellung, die Episoden auswendig lernt). Dass der Rest der Testzeilen mit den **Trainings**koeffizienten berechnet wird (Plan v2, Festlegung 3) und dass die Kriterien 2 und 3 der Bestätigung nur M3-B zählen, legen seit der Fix-Welle eigene Tests fest.
- **Aufräumtest in anderer Umgebung:** `test_staged_run_resumes_from_partial_work_files` (langsam) scheiterte in der Umgebung des Nutzers (Python 3.12, numpy 2.5.3) an wieder auftauchenden Dateien in `.work`, auch auf dem Ausgangscommit (REVIEW-2026-10-04). Hier (Python 3.11.15, numpy 2.4.6) besteht er wiederholt, mit altem und neuem Treiber; eine Ursache im Code ist nicht gefunden (kein Arbeitsprozess überlebt eine Stufe). Tritt so etwas bei einem echten Lauf auf: anhalten und melden.

## Arbeitsweise im Projekt

Workflow nach „superpowers“: brainstorming → writing-plans → subagent-driven-development. Commits auf dem Branch oben, kein Push auf andere Branches, kein Pull Request ohne Auftrag. Bericht später mit fester Gliederung (Spec v2 §11). „Bestätigt“ oder „bewiesen“ nur bei erfüllter Vorhersage. Seeds aus Bestätigungsrunden und Hauptlauf nie wiederverwenden (Seed 0 darf im Pilot erneut laufen).
