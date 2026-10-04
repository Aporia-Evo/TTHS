# Handover Farbversuch (Stand 03.10.2026, v2 umgesetzt, Pilot steht aus)

Für die nächste Claude-Sitzung (Claude Scientific, andere Maschine). Dieses Dokument soll genügen, um ohne weitere Vorgeschichte weiterzuarbeiten. Hintergrund in `docs/PROJEKTBESCHREIBUNG.md`.

Repo `aporia-evo/tths`, Branch `claude/dreamy-wozniak-7xt321`. Es wird nur auf diesem Branch gearbeitet.

## Kurzfassung

- Der Code für die Version 2 ist fertig und getestet. Es gibt noch **keinen einzigen Lauf** mit der vollen Konfiguration: weder Pilot noch Bestätigung noch Hauptlauf.
- Nächste Schritte: Pilot Seed 0 → Bestätigung Seeds 500–504 → **Halt, Entscheidung des Nutzers** → Einfrieren → Hauptlauf Seeds 400–409.
- Die Sitzung, die dieses Dokument liest, macht Pilot und Bestätigung und hält dann an. Seeds 400–409 und `freeze write` nur nach ausdrücklicher Freigabe des Nutzers.
- Ein fertiger Prompt dafür steht unten im Abschnitt „Prompt für Claude Scientific“.

## Bindende Dokumente

- **Spezifikation v2:** `docs/superpowers/specs/2026-10-03-farb-wiederoeffnung-v2-design.md`. Sie ist eigenständig und bindend. Anhang A nennt die Änderungen gegenüber v1 mit Begründung.
- **Plan v2:** `docs/superpowers/plans/2026-10-03-farb-wiederoeffnung-v2.md`, dort die „Festlegungen“ 1–10 (RNG-Schlüssel, Residualisieren, Öffnungsregel, δ-Gewinn, P1b-Messung, Bestätigung, `total_sec`, Ergebnis-JSON). Der v1-Plan gilt mit seinen Festlegungen weiter, soweit der v2-Plan nichts anderes sagt.
- **v1 ist Geschichte:** `docs/superpowers/specs/2026-10-03-farb-wiederoeffnung-design.md` und `docs/superpowers/plans/2026-10-03-farb-wiederoeffnung.md`. Wo sie von v2 abweichen, gilt v2.
- Bei Widerspruch zwischen Doku und Code: nicht raten, den Nutzer fragen.

## Stand

- **Code:** Die Aufgaben 1–8 des Plans v2 sind umgesetzt (Commits `998f4aa` bis `8f4633e` auf dem Branch), jede einzeln geprüft. Aufgabe 9 ist diese Dokumentation.
- **Tests** (gemessen auf der Maschine der Umsetzung: 4 Kerne, Python 3.11.15, numpy 2.4.6):
  - Alle: `python -m pytest -q` gibt **285 passed** in 123 s (2:02), ohne Warnungen.
  - Ohne die langsamen: `python -m pytest -q -m "not slow"` gibt **258 passed, 27 deselected** in 4,7 s.
- **Offen:** Pilot, Bestätigung, Entscheidung des Nutzers, Einfrieren, Hauptlauf, Bericht (feste Gliederung nach Spec v2 §11, noch nicht geschrieben).
- Nicht vorhanden und noch nicht erzeugt: `farbversuch/pilot_config.json`, `farbversuch/PROTOKOLL.md`, `farbversuch/frozen_config.json`, `farbversuch/freeze.sha256`, `farbversuch/results/`.

### Was v2 gegenüber v1 ändert (Kurzfassung der Spec)

- **Übungs-Ontologie:** Am Ende der Übungsphase öffnet jedes der vier Systeme mit seinem eigenen Erklärverfahren bis zu 8 Merkmale vor (Übungspuffer = letzte 2000 Schritte der Vorwärtsdaten; M3 mit fester Mindestverbesserung 0,01, S1 mit Holm). Sie gehen ins Basismodell des Erklärens ein, werden im Einsatz nicht erneut getestet und zählen nie als „geöffnet“. Das Bemerken bleibt unverändert.
- **Residualisieren:** Jeder Kandidat wird je Teilung gegen das Basisdesign regressiert, nur der Rest zählt. Duplikate und Linearkombinationen gewinnen genau 0.
- **Mindestverbesserung δ:** Geöffnet wird nur bei Verbesserung in allen 5 Teilungen und Mittel > δ. δ je M3-System = größter der 20 Null-Gewinne.
- **Kalibrierung:** Null-Ströme haben 400 Episoden. Alle Schwellen und δ sind der **größte** der 20 Null-Werte. Erwartete Fehlalarmrate pro neuem Strom ≈ 1/21 ≈ 4,8 %.
- **P1b „weitgehend geschlossen“:** Restanteil ≤ 0,15 und Verschiebung von z ≤ 0,25 (500 Positionen). Scheitert P1 oder P1b, entfällt der Seed („Prämisse nicht erfüllt“), es laufen dann keine Bedingungen.
- **S1:** Permutationen Arm B 1000, Arm A 25.000 (blockweise zu 1000), damit S1-A bei 1192 Kandidaten überhaupt ablehnen kann.
- **Zuschreibung bei `red`** zählt nur nach dem Wechsel.
- **Bestätigung auf Seeds 500–504** vor dem Einfrieren, Auswertung mit `analyze --confirm`.
- **Paralleler Treiber** über Seeds und Bedingungen mit Fortsetzen nach Abbruch.

### Code-Überblick

`farbversuch/`: `world.py` (Welt), `routine.py`, `forward.py` (Vorwärtsmodell), `monitor.py` (Bemerken, Erklären, Vor-Öffnen, Kalibrierhilfen), `closure.py` (P1b), `run.py` (Phase 1, Prämissen, Einsatz, CLI mit Treiber), `analyze.py` (Bericht, `--confirm`), `freeze.py`, `config.py`, `seeds.py`. Tests unter `farbversuch/tests/`. `routine.py`, `forward.py` und `monitor.py` greifen nie auf Bedingung, Wechselzeitpunkt oder `C_SPECIAL` zu (AST-Test in `test_isolation.py`).

## Nächste Schritte und Befehle

Alle Befehle im Repo-Wurzelordner.

### 0. Einrichten

```bash
git fetch origin && git checkout claude/dreamy-wozniak-7xt321 && git pull
python -m pip install -r requirements.txt        # numpy>=2.0, pytest>=8
python -m pytest -q -m "not slow"                 # erwartet: 258 passed, 27 deselected
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

### 1. Pilot auf Seed 0

`farbversuch/pilot_config.json` gibt es noch nicht. Sie wird aus den Standardwerten erzeugt:

```bash
mkdir -p farbversuch/results
python -c "from farbversuch.config import Config; Config().to_json('farbversuch/pilot_config.json')"
python -m farbversuch.run --config farbversuch/pilot_config.json --seeds 0 --jobs 4 --out farbversuch/results/pilot 2> farbversuch/results/pilot.log
python -m farbversuch.analyze --results farbversuch/results/pilot --seeds 0 > farbversuch/results/pilot_report.md
```

- Fortschrittszeilen mit Zeitstempel gehen auf stderr (hier in die Logdatei). Lange Läufe im Hintergrund starten (`nohup … &`) und das Log lesen.
- `analyze` ohne `--confirm` ist für Seed 0 eine **explorative Auswertung**: Die Urteile zu P2–P5 und zum Abbruchkriterium stehen dort als „–“. Das ist gewollt.
- Werte ansehen: Tabelle „Werte je Seed“ im Bericht (Farbinvarianz, Restanteil, Verschiebung, Übungs-Ontologien, δ, Nutzbarkeit). Das Vorwärtsmodell-Kriterium von P1 (`fwd_surprise` gegen `freq_surprise`), die Schwellen und `p_global` stehen nur in der JSON-Datei:

```bash
python -c "import json; r=json.load(open('farbversuch/results/pilot/seed_0.json')); print(json.dumps({k: r[k] for k in ('premise','calibration','practice','delta','p_global','phase1_sec','total_sec')}, indent=1, ensure_ascii=False))"
```

- `premise.ok` ist wahr, wenn Farbinvarianz ≥ 0,95, `fwd_surprise` < `freq_surprise`, Restanteil ≤ 0,15 und Verschiebung ≤ 0,25 gelten. `restanteil` oder `shift` gleich `null` heißt: nicht endlich, also nicht erfüllt. Bei `ok = false` ist `conditions` leer (`null`).
- `p_global` hat die Kennzeichen `hit` (Toleranz getroffen) und `bracketed` (Zielwert einschließbar). Auffällig ist `bracketed = false`.

**Erwartung (Annahme, nicht gemessen):** Die Routine und ihr Training sind seit der v1-Diagnose unverändert (`routine.py`, `world.py`, `forward.py` sind es seit dem v1-Stand). Dort lag die Farbinvarianz auf Seed 0 bei 0,926 (Schwelle 0,95, 1 BLAS-Thread). Mit den Standardwerten scheitert P1 im Pilot deshalb wahrscheinlich. Die damaligen Werte für Schwellen und `p_global` sind veraltet, weil Kalibrierung und Null-Ströme sich geändert haben. Die explorative Diagnose in Spec v2 Anhang A nennt für Seed 0 Restanteil ≈ 7 % und Verschiebung ≈ 15 % (explorative Diagnose, kein Ergebnis dieses Piloten).

**Scheitert P1 oder P1b:**
1. Anhalten und dem Nutzer die Werte zeigen: Farbinvarianz, `fwd_surprise` gegen `freq_surprise`, Restanteil, Verschiebung, Übungs-Ontologien.
2. Einen Vorschlag machen, aber nichts ändern, bevor der Nutzer zustimmt.
3. Erlaubte Änderungen nach Spec v2 §8: nur Trainings-Hyperparameter der Routine und des Vorwärtsmodells, Puffergröße, Prüfintervall. In der Konfiguration sind das: `lr`, `epochs`, `wd`, `init_std` (Routine), `fwd_l2`, `logreg_tol`, `logreg_max_iter` (Vorwärtsmodell), `buffer_size`, `check_interval`. Grenzfälle, die nicht ausdrücklich genannt sind (`k`, `n_teacher_episodes`, `n_forward_episodes`): nur mit Rückfrage. Alles andere (Welt, Schwellenlogik, `pre_open_delta`, `max_restanteil`, `max_shift`, `min_invariance`, `max_open`, `alpha`, Permutationszahlen, Seeds) ist tabu.
   Jeder Vorschlag nennt die Kopplungen (geprüft gegen `run.py`, `monitor.py`, `closure.py`):
   - `fwd_l2`, `logreg_tol` und `logreg_max_iter` steuern nicht nur das Vorwärtsmodell. Über `_fit_kw` in `run.py` wirken sie auch auf das Vor-Öffnen der M3-Systeme und auf die δ-Kalibrierung, im Einsatz auf die M3-Anpassungen des Monitors. Das Vorwärtsmodell selbst bestimmt die Überraschung und damit Schwellen, `p_global` und die S1-Tests. `fwd_l2` ist außerdem das L2 der P1b-Probe, also des Restanteils (`logreg_tol` und `logreg_max_iter` wirken dort nicht).
   - `buffer_size` bestimmt die Länge des Übungspuffers, der δ-Puffer und des Ringpuffers im Einsatz.
4. Naheliegend wäre ein stärkerer Weight Decay oder mehr Epochen für die Farbinvarianz (Annahme, nicht geprüft).
5. Jede Änderung mit Grund in `farbversuch/PROTOKOLL.md` festhalten, **bevor** das alte Ergebnis gelöscht wird (die alten Messwerte dort mit eintragen). Ein Eintrag: Datum, Parameter alt → neu, Grund (Messwert), Ergebnis des nächsten Pilots.
6. Altes Pilotergebnis löschen, sonst bricht die CLI ab (sie überschreibt keine Ergebnisse einer anderen Konfiguration): `rm -rf farbversuch/results/pilot farbversuch/results/pilot.log farbversuch/results/pilot_report.md`. Dann Pilot neu starten.

Sind P1 und P1b erfüllt, braucht es keine Rückfrage. Die Pilot-Konfiguration ist dann fertig, und es geht mit der Bestätigung weiter. Die Pilotergebnisse und `pilot_config.json` committen.

### 2. Bestätigung auf Seeds 500–504

Mit **derselben** `pilot_config.json`:

```bash
python -m farbversuch.run --config farbversuch/pilot_config.json --seeds 500-504 --jobs $JOBS --out farbversuch/results/confirm 2> farbversuch/results/confirm.log
python -m farbversuch.analyze --results farbversuch/results/confirm --seeds 500-504 --confirm > farbversuch/results/confirm_report.md
```

- Die Methode gilt als bestätigt, wenn es mindestens 4 von 5 Seeds gibt, in denen **alle drei** Kriterien **gleichzeitig** gelten: (1) P1 und P1b erfüllt, (2) M3-B öffnet bei `none` und `global` nichts über die Übungs-Ontologie hinaus, (3) M3-B öffnet bei `red` „Farbe 0“ nach dem Wechsel. Ein Seed mit gescheiterter Prämisse zählt bei (2) und (3) als nicht erfüllt. Entscheidend ist im Bericht die Zeile „Alle drei Kriterien gleichzeitig“; die Zählungen je Kriterium stehen dort nur zur Information (Präzisierung der Spec v2 §8, Entscheidung des Nutzers vom 04.10.2026).
- `analyze --confirm` weist Seeds aus 400–409 ab. Das ist Absicht: Hauptlauf-Seeds dürfen nicht zur Bestätigung dienen.
- Pilot und Bestätigung laufen jeweils komplett auf derselben Maschine. `analyze` verlangt über alle Seeds gleiche Konfiguration und gleiche Umgebung und bricht sonst ab.
- Ist die Bestätigung gestartet, bleibt `pilot_config.json` unverändert, und die Seeds 500–504 laufen nicht mit einer anderen Konfiguration neu: Mit dem Start sind sie verbraucht.
- Danach **anhalten** und dem Nutzer berichten (Tabelle „Bestätigung“, Werte je Seed, Laufzeiten).

### 3. Entscheidung des Nutzers, Einfrieren, Hauptlauf (nur nach ausdrücklicher Freigabe)

Das gehört nicht zum Auftrag der Sitzung, die Pilot und Bestätigung macht. Der Ablauf nach Spec v2 §8:

- **Nicht bestätigt:** Ergebnis zurück an den Nutzer. Eine weitere Runde läuft nur auf neuen Seeds (510–514 usw.). Seeds, die eine Bestätigungsrunde oder den Hauptlauf bestritten haben (500–504, 400–409, …), werden nie wiederverwendet. Seed 0 darf im Pilot nach erlaubten Änderungen erneut laufen.
- **Bestätigt:** Der Nutzer entscheidet, ob zusätzlich Seeds 505–509 laufen (gleicher Befehl mit `--seeds 505-509 --out farbversuch/results/confirm2`).
- **Einfrieren** (erst nach Freigabe): schreibt `frozen_config.json` und SHA-256 aller `*.py` (auch Tests), `requirements.txt` und `pytest.ini` in `freeze.sha256`. Danach darf sich keine Quelldatei mehr ändern.
  ```bash
  python -m farbversuch.freeze write --config farbversuch/pilot_config.json
  python -m farbversuch.freeze verify          # muss OK ausgeben
  ```
  Dann committen und pushen.
- **Hauptlauf** (erst nach Freigabe und nach dem Einfrieren), Seeds 400–409, mit der eingefrorenen Konfiguration. Stufe 1 nutzt höchstens 10, Stufe 2 höchstens 40 Jobs. `<N>` = Zahl der physischen Kerne, höchstens 40; die Zahl direkt eintragen (die Variable `JOBS` aus Abschnitt 0 ist auf 20 begrenzt und gilt nicht über Sitzungen hinweg):
  ```bash
  python -m farbversuch.run --config farbversuch/frozen_config.json --seeds 400-409 --jobs <N> --out farbversuch/results/main 2> farbversuch/results/main.log
  python -m farbversuch.freeze verify
  python -m farbversuch.analyze --results farbversuch/results/main --seeds 400-409
  ```
  Nur diese Auswertung gibt die vorregistrierten Urteile zu P2–P5 und zum Abbruchkriterium aus. Alles, was nach dem Hauptlauf geändert oder ergänzt wird, ist „nachträgliche Erkundung“ und steht im Bericht getrennt.

### Laufzeit

Für v2 mit der vollen Konfiguration gibt es **keine gemessene Laufzeit**. Eine Hochrechnung wäre geraten. Der Pilot liefert die ersten Zahlen. Wo sie stehen:

- Je Seed in der JSON-Datei: `phase1_sec` (Phase 1 mit Vor-Öffnen und Kalibrierung) und `total_sec` (Vorbereitungszeit plus **Summe** der vier Bedingungszeiten). `total_sec` ist also Rechenzeit über alle Prozesse, nicht die Wandzeit des Laufs.
- Wandzeit: Das Log (stderr) hat je Zeile `HH:MM:SS` ohne Datum und je Seed die Zeilen `seed N gestartet`, `seed N Phase 1 fertig (X s), Prämisse ok` bzw. `nicht erfüllt` und `seed N Bedingung C fertig (X s)`. X bei „Phase 1 fertig“ ist nur die Zeit von Phase 1; der Zeitstempel liegt nach der Prämissenprüfung. Stufenmarken gibt es nicht. `seed N fertig` (Stufe 3) geht auf stdout, ohne Zeitstempel, und steht nicht im Log. Die gesamte Wandzeit deshalb mit `date` vor dem Start und nach dem Ende jedes Laufs notieren.
- Im Bericht: Abschnitt „Kosten“ (Zeit je Prüfung, Gesamtzeit je System und Bedingung).
- Zum Vergleich nur ein v1-Wert, der für v2 nicht gilt: M3-A brauchte in v1 etwa 75–90 s pro Prüfung. In v2 kommen Vor-Öffnen mit 1192 Kandidaten und die δ-Kalibrierung auf 20 Puffern hinzu; M3-A und S1-A (25.000 Permutationen) sind vermutlich die teuersten Teile (Annahme).
- Beim Bericht an den Nutzer immer Kernzahl, `--jobs` und die Zeiten angeben, damit Bestätigung und Hauptlauf eingeschätzt werden können.

### Unterbrechen und Fortsetzen

Ein unterbrochener Lauf lässt sich mit **demselben Befehl** neu starten, aber mit `2>>` statt `2>` für das Log. Das hängt an und lässt die Zeitstempel des ersten Laufs stehen; `2>` würde das Log überschreiben.

- Fertige `seed_<n>.json` mit gleicher Konfiguration werden übersprungen. Liegt dort ein Ergebnis mit anderer Konfiguration, bricht die CLI ab, ohne etwas zu überschreiben.
- Zwischenstände liegen in `<out>/.work` (Vorbereitung je Seed, Ergebnis je Seed und Bedingung). Sie werden nur wiederverwendet, wenn Konfiguration **und** Herkunft übereinstimmen. Die Herkunft ist ein SHA-256 über den Quelltext aller `farbversuch/*.py` (ohne `tests/`) und die Umgebung (Threadvariablen, numpy, BLAS, Python). Anderer Code oder andere Umgebung heißt: Neuberechnung.
- Die `seed_<n>.json` entstehen erst in Stufe 3, also nachdem **alle** Seeds die Stufen 1 und 2 durchlaufen haben. Nach einem Abbruch in Stufe 1 oder 2 gibt es daher noch keine Ergebnisdateien, aber die fertigen Zwischenstände bleiben erhalten.
- Quelldateien in `farbversuch/` während eines Laufs nicht ändern.

### Ergebnisse committen

Die Ordner `farbversuch/results/<name>/.work` und `*.tmp` nicht committen. Gezielt hinzufügen:

```bash
git add farbversuch/pilot_config.json farbversuch/results/pilot/seed_*.json farbversuch/results/pilot.log farbversuch/results/pilot_report.md
git add farbversuch/PROTOKOLL.md                  # nur wenn vorhanden
git add farbversuch/results/confirm/seed_*.json farbversuch/results/confirm.log farbversuch/results/confirm_report.md
```

Die Commit-Nachricht endet mit den Attributionszeilen der jeweiligen Sitzung. Gepusht wird nur auf `claude/dreamy-wozniak-7xt321`.

## Prompt für Claude Scientific

Zum Einfügen als erste Nachricht der neuen Sitzung:

````text
Du setzt das Projekt „Farbversuch“ fort (Repo aporia-evo/tths, Branch claude/dreamy-wozniak-7xt321, Python mit numpy). Antworte auf Deutsch, knapp und sachlich. Schreibe „bestätigt“ oder „bewiesen“ nur bei erfüllter Vorhersage.

Lies zuerst vollständig: docs/HANDOVER.md, docs/PROJEKTBESCHREIBUNG.md und docs/superpowers/specs/2026-10-03-farb-wiederoeffnung-v2-design.md. Bindend sind diese Spezifikation v2 und der Plan docs/superpowers/plans/2026-10-03-farb-wiederoeffnung-v2.md.

Auftrag: Pilot auf Seed 0, danach Bestätigung auf den Seeds 500-504, Ergebnisse committen und pushen, Bericht an mich. Danach anhalten.

Harte Grenzen:
- Arbeite nur auf dem Branch claude/dreamy-wozniak-7xt321 und pushe nur dorthin. Kein Pull Request.
- Ändere keinen Code und keine Doku. Schreiben darfst du nur farbversuch/pilot_config.json, farbversuch/PROTOKOLL.md und Dateien unter farbversuch/results/. Findest du einen Fehler im Code, behebe ihn nicht: anhalten und mit Fehlertext melden.
- Lass die Seeds 400-409 NICHT laufen.
- Führe `python -m farbversuch.freeze write` NICHT aus.
- Starte keine weiteren Seeds (505-509, 510-514 usw.) ohne meine ausdrückliche Anweisung.
- Sobald die Bestätigung (Schritt 4) gestartet ist, ändere farbversuch/pilot_config.json nicht mehr und lass die Seeds 500-504 nicht mit einer anderen Konfiguration neu laufen.
- Pilot und Bestätigung laufen auf derselben Maschine. Ändere während eines Laufs keine *.py-Datei (Schreiben nach farbversuch/results/, in farbversuch/pilot_config.json und farbversuch/PROTOKOLL.md ist erlaubt).

Schritt 1: Einrichten und Tests
```bash
git fetch origin && git checkout claude/dreamy-wozniak-7xt321 && git pull
python -m pip install -r requirements.txt
python -m pytest -q -m "not slow"
```
Erwartet: 258 passed, 27 deselected. Schlägt das fehl, halte an und melde es.
Bestimme die Zahl der physischen Kerne (`lscpu -p=CORE,SOCKET | grep -v '^#' | sort -u | wc -l`, sonst `nproc`) und nenne sie als JOBS, höchstens 20.

Schritt 2: Pilot auf Seed 0
```bash
mkdir -p farbversuch/results
python -c "from farbversuch.config import Config; Config().to_json('farbversuch/pilot_config.json')"
python -m farbversuch.run --config farbversuch/pilot_config.json --seeds 0 --jobs 4 --out farbversuch/results/pilot 2> farbversuch/results/pilot.log
python -m farbversuch.analyze --results farbversuch/results/pilot --seeds 0 > farbversuch/results/pilot_report.md
```
Starte lange Läufe im Hintergrund und lies das Log. Notiere `date` vor dem Start und nach dem Ende. Der Lauf lässt sich nach einer Unterbrechung mit demselben Befehl fortsetzen, aber mit `2>>` statt `2>`, damit das Log erhalten bleibt.
Berichte mir die Werte: P1 (Farbinvarianz, Vorwärtsmodell gegen Häufigkeitsmodell), P1b (Restanteil, Verschiebung), die Übungs-Ontologie je System, δ je M3-System, die Schwellen und p_global (mit hit und bracketed). Sie stehen im Bericht und in farbversuch/results/pilot/seed_0.json (siehe HANDOVER, Abschnitt „1. Pilot auf Seed 0“).

Schritt 3: Entscheidung nach dem Pilot
- Sind P1 und P1b erfüllt (premise.ok ist wahr): ohne Rückfrage weiter mit Schritt 4. Committe farbversuch/pilot_config.json und die Pilotergebnisse (siehe HANDOVER, „Ergebnisse committen“) und pushe.
- Scheitert P1 oder P1b: HALT. Zeige mir die Werte und schlage Änderungen vor. Ändere nichts, bevor ich zustimme. Erlaubt nur lr, epochs, wd, init_std, fwd_l2, logreg_tol, logreg_max_iter, buffer_size, check_interval. k, n_teacher_episodes, n_forward_episodes nur nach Rückfrage. Alles andere ist tabu (Welt, Schwellenlogik, pre_open_delta, max_restanteil, max_shift, min_invariance, max_open, alpha, Permutationszahlen, Seeds). Nenne bei jedem Vorschlag die Kopplungen: fwd_l2, logreg_tol und logreg_max_iter wirken auch auf das Vor-Öffnen der M3-Systeme, die δ-Kalibrierung und die M3-Anpassungen im Einsatz, fwd_l2 zusätzlich auf die P1b-Probe; buffer_size bestimmt Übungspuffer, δ-Puffer und Ringpuffer. Jede Änderung mit Grund und den alten Messwerten in farbversuch/PROTOKOLL.md eintragen, dann das alte Pilotergebnis löschen (rm -rf farbversuch/results/pilot farbversuch/results/pilot.log farbversuch/results/pilot_report.md), sonst bricht die CLI ab, und den Pilot neu laufen lassen.
- Bei technischen Fehlern (Absturz, rote Tests): nichts umgehen, mit Fehlertext melden.

Schritt 4: Bestätigung auf den Seeds 500-504 mit derselben pilot_config.json
```bash
python -m farbversuch.run --config farbversuch/pilot_config.json --seeds 500-504 --jobs JOBS --out farbversuch/results/confirm 2> farbversuch/results/confirm.log
python -m farbversuch.analyze --results farbversuch/results/confirm --seeds 500-504 --confirm > farbversuch/results/confirm_report.md
```
(JOBS durch die Zahl aus Schritt 1 ersetzen. Auch hier `date` vor und nach dem Lauf notieren; beim Neustart `2>>` statt `2>`.)

Schritt 5: Committen und pushen
Füge gezielt hinzu: farbversuch/pilot_config.json, farbversuch/PROTOKOLL.md (falls vorhanden), farbversuch/results/pilot/seed_*.json, farbversuch/results/confirm/seed_*.json, die .log- und _report.md-Dateien. Nicht committen: .work-Ordner und *.tmp. Commit-Nachricht auf Deutsch, am Ende die Attributionszeilen deiner Sitzung. `git push origin claude/dreamy-wozniak-7xt321`.

Schritt 6: Bericht an mich
- Pilot: Werte wie in Schritt 2, Änderungen an der Konfiguration (mit Verweis auf PROTOKOLL.md).
- Bestätigung: die Tabelle „Bestätigung“ aus confirm_report.md (entscheidend ist die Zeile „Alle drei Kriterien gleichzeitig“, die drei Kriterien stehen zur Information darunter), die Kriterien je Seed, P1/P1b-Werte, Übungs-Ontologien und δ je Seed, bei `red` die Nutzbarkeit.
- Laufzeiten: Kernzahl, --jobs, Gesamtwandzeit (aus `date`), aus dem Log die Zeitstempel je Seed für „gestartet“, „Phase 1 fertig“ und „Bedingung … fertig“, dazu phase1_sec und total_sec je Seed.
- Getrennt: Beobachtet (Zahlen) und Deutung (ausdrücklich als Annahme).
- Auffälligkeiten: Warnungen, Abbrüche, p_global mit bracketed = false, Seeds mit gescheiterter Prämisse.

Danach STOPP. Starte nicht die Seeds 400-409 und führe nicht `freeze write` aus. Ob zusätzlich 505-509 laufen, ob eingefroren wird und wann der Hauptlauf startet, entscheide ich.
````

## Abweichungen und Festlegungen während der Umsetzung (v2)

Neu in v2 (Entscheidungen der Umsetzung, jeweils mit Auswirkung):

- **S1-Permutationstest auf Raster:** `perm_pvalues` rundet die Überraschungen auf ein Raster 2^-q (relative Abweichung etwa 5e-13 bei 2000 Schritten). Dadurch sind die p-Werte bitgleich für jede Blockgröße (`perm_chunk`), und exakte Gleichstände beim Vergleich der Permutationen hängen nicht mehr an der Reihenfolge der Gleitkommasummen. Der Zufallsstrom bleibt unverändert.
- **P1b nicht endlich:** Ist der Restanteil `nan` (keine Nachbarzelle bleibt übrig) oder die Verschiebung nicht endlich, steht in der JSON `null`, und die Prämisse gilt als nicht erfüllt.
- **Bericht, erwartete Fehlalarmrate:** Die Zeile rechnet (`max_null_alarms` + 1) / (`n_null_streams` + 1). Für v2 ergibt das 1/21 ≈ 4,8 %. Für Ergebnisse mit anderer Konfiguration stimmt die Zeile ebenfalls (v1 mit einem erlaubten Alarm: 9,5 %).
- **Fortsetzen nur bei gleicher Herkunft:** `.work`-Zwischenstände werden nur bei gleicher Konfiguration und gleichem Fingerabdruck von Code und Umgebung wiederverwendet (siehe „Unterbrechen und Fortsetzen“). Das kam aus der Prüfung von Aufgabe 7.
- **Gleiches Ergebnis in beiden Ausführungswegen:** Der parallele Treiber liefert je Seed dasselbe wie das sequentielle `run_seed` (bis auf die `_sec`-Schlüssel). Der Test rechnet die Referenz in einem frischen Prozess mit einem BLAS-Thread, weil der pytest-Prozess mehrere Threads nutzt und die Ergebnisse sich sonst ab der sechsten Stelle unterscheiden.
- **`total_sec`** ist Vorbereitungszeit plus Summe der Bedingungszeiten, in beiden Wegen gleich definiert (Plan v2, Festlegung 9). Es ist keine Wandzeit.
- **Nutzbarkeit** (Spec §6) steht als `gain` an der ersten richtigen Öffnung von M3-B unter `red`. Ergebnisse ohne `gain` zeigen „–“.

Aus v1 und weiter gültig:

- **Zuschreibung bei `red`** zählt nur, wenn die Öffnung nach dem Wechsel liegt (Episode > 100). Die Latenz ist Episode − 100. Frühere Öffnungen zählen als Fehlzuschreibung. Grund: Vor dem Wechsel sind alle vier Ströme identisch. Jetzt steht das auch in der Spec v2 §6.
- **`p_global`:** Das Ergebnis enthält die Kennzeichen `hit` (Toleranz getroffen) und `bracketed` (Zielwert einschließbar, v1-Plan Festlegung 15).
- **BLAS-Threads:** Der Code legt sie selbst auf 1 fest und schreibt Threads, numpy und BLAS in einen `env`-Block jeder Ergebnisdatei. Ergebnisse mit anderer Thread-Zahl unterscheiden sich deutlich. `evaluate` verlangt gleiche Konfiguration und gleiche Umgebung über alle Seeds.
- **Seeds werden geprüft:** Doppelte Seeds weist `parse_seeds` (CLI von `run` und `analyze`) und `evaluate` mit `ValueError` ab. Der Temp-Dateiname je Seed enthält die Prozess-ID.
- **Explorative Auswertung:** `evaluate` gibt die vorregistrierten Urteile (P2–P5, Abbruch) nur für genau die Seeds 400–409 aus (`"preregistered": True`). Bei anderen Seeds (Pilot Seed 0, Bestätigung 500–504) stehen Zahlen und Kennzahlen, die Urteile sind `None`, und der Bericht beginnt mit dem Hinweis „Explorative Auswertung“ und zeigt „–“ statt erfüllt/nicht erfüllt. Das Urteil der Bestätigung (Spec §8) gibt `--confirm` aus.
- **Abstürze im parallelen Treiber:** Das gilt weiter. Löst ein Arbeitsprozess eine Ausnahme aus, beendet das die laufende Stufe und damit den ganzen Lauf mit dem Fehlertext. Bereits fertige Zwischenstände in `<out>/.work` bleiben erhalten, und derselbe Befehl (Log mit `2>>`) setzt fort. Dann anhalten und den Nutzer fragen, nicht umgehen. Wird ein Arbeitsprozess vom System beendet (z. B. Speichermangel), kann der Pool hängen bleiben, ohne einen Fehler zu melden (nicht getestet). Dann den Lauf abbrechen und neu starten.
- **Testtoleranz:** Ein Test (`test_warm_start_reaches_same_optimum` in `test_forward.py`) nutzt `tol=1e-8`. Der Löser bleibt bei Standard `tol=1e-6`; die zulässigen Verbesserungen liegen bei ≥ 1e-5, also deutlich über dem Lösungsrauschen.

## Bekannte kleinere Punkte

Bei der Prüfung der Aufgaben bewusst offen gelassen. Sie betreffen den Betrieb:

- **Beschädigte Zwischendatei:** Eine abgeschnittene oder beschädigte Datei in `<out>/.work` (z. B. nach vollem Datenträger) bricht den Neustart ab, statt neu zu rechnen. Abhilfe: `<out>/.work` löschen und den Befehl wiederholen. Dasselbe, wenn zwischen Abbruch und Neustart der Code geändert wurde (ein Zwischenstand wird vor der Herkunftsprüfung geladen und kann dann fehlschlagen).
- **Ein Fehler beendet den Lauf:** Ein fehlschlagender Arbeitsprozess beendet den Pool (siehe oben). Fertige Seeds warten in Stufe 3 auf die übrigen, also erscheinen die `seed_<n>.json` erst am Ende der Stufen 1 und 2.
- **Quelldateien während eines Laufs:** Der Fingerabdruck wird am Anfang bzw. Ende eines Auftrags von der Platte gelesen. Wer Code während eines laufenden Laufs ändert, bekommt Zwischenstände mit falscher Herkunft. Nicht tun.
- **M3-A im Lauftest:** Die Lauf-Tests (`TINY`) lassen M3-A weg. Vor-Öffnen und δ-Kalibrierung für M3-A (1192 Kandidaten) in `phase1` laufen in den Tests nicht durch; der Pilot ist der erste volle Lauf damit. Ein Fehler dort wird gemeldet, nicht umgangen.
- **Testlücken ohne bekannte Code-Fehler:** Kein Test legt fest, dass der Rest der Testzeilen mit den **Trainings**koeffizienten berechnet wird (Plan v2, Festlegung 3; der Code tut es). Die P1b-Tests prüfen nicht gegen Informationslecks (z. B. eine Darstellung, die Episoden auswendig lernt). Die Prüfung, dass die Kriterien 2 und 3 der Bestätigung nur M3-B zählen, fehlt als eigener Test.
- **Bestätigung aus v1-Ergebnissen:** `analyze --confirm` übernimmt `premise.ok` aus der Ergebnisdatei. Ergebnisse im v1-Format (ohne Restanteil und Verschiebung) würden P1b als erfüllt zählen. Solche Ergebnisse liegen nicht im Repo; für neue Läufe ist das kein Thema.

## Arbeitsweise im Projekt

Workflow nach „superpowers“: brainstorming → writing-plans → subagent-driven-development. Commits auf dem Branch oben, kein Push auf andere Branches, kein Pull Request ohne Auftrag. Bericht später mit fester Gliederung (Spec v2 §11). „Bestätigt“ oder „bewiesen“ nur bei erfüllter Vorhersage. Seeds aus Bestätigungsrunden und Hauptlauf nie wiederverwenden (Seed 0 darf im Pilot erneut laufen).
