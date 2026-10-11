# Kontextversuch (v4) – Umsetzungsplan

> **Für agentische Ausführende:** Pflicht-Unterskill: superpowers:subagent-driven-development (empfohlen) oder superpowers:executing-plans. Die Schritte nutzen Checkboxen (`- [ ]`).

**Ziel:** Paket `kontextversuch/`, das kleine Decoder auf Regel-Aufgaben im Kontext trainiert, die Farbnutzung U gegen exakte Ideal-Kurven misst und P1–P5 der Spec auswertet. Läufe sind wiederaufnehmbar und deterministisch.

**Architektur:** Kleine Module mit je einer Aufgabe:
- `tasks` erzeugt die Daten, `ideal` die exakten Vergleichskurven, `model` ist der Decoder, `train` die Trainingsschleife;
- `evaluate` misst, `run` treibt die Läufe (je Modell eine Aufgabe, parallel, Sperre, Fingerabdruck), `analyze` bewertet, `freeze` sichert den Stand.

Die Muster kommen aus `farbversuch/run.py` und `farbversuch/freeze.py`. Sie werden **übernommen, nicht importiert**: Das neue Paket hängt nicht vom eingefrorenen Farbversuch ab.

**Technik:** Python 3.11, numpy ≥ 2.0, PyTorch 2.14.1 (nur CPU), pytest.

**Spec:** `docs/superpowers/specs/2026-10-11-kontextversuch-v4-design.md`

## Globale Vorgaben

- **Sprache:** Kommentare, Docstrings, Meldungen und Commit-Nachrichten auf Deutsch, im Stil des Repos.
- **Commits** enden mit `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` und `Claude-Session: https://claude.ai/code/session_017cegdxf8JunDX1KudRUctm`. Gepusht wird nur auf `claude/dreamy-wozniak-7xt321`.
- **Rechnen:** nur CPU, ein Thread je Prozess:
  - `torch.set_num_threads(1)`, `torch.use_deterministic_algorithms(True)`;
  - die Thread-Variablen `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, `VECLIB_MAXIMUM_THREADS`, `BLIS_NUM_THREADS` = 1, gesetzt vor dem Start der Arbeitsprozesse.
- **Aufgabenkonstanten,** nicht konfigurierbar:
  - A = 4 Eigenschaften (0 Form, 1 Größe, 2 Position, 3 Farbe), V = 4 Werte, L = 4 Antworten, K = 8 Beispiele;
  - Token einer Eigenschaft a mit Wert v: a·4 + v (0–15); Antworten 16–19; „?“ = 20; Wortschatz 21;
  - Beispiel = [4 Eigenschafts-Tokens, „?“, Antwort], also 6 Tokens; Sequenz T = 48;
  - „?“-Positionen: k·6 + 4.
- **Standardkonfiguration** (Spec §3, §4):

  | Bereich | Werte |
  |---|---|
  | Modell | d_model 64, n_layers 3, n_heads 4, d_ff 256 |
  | Optimierung | lr 0,001, weight_decay 0,01, warmup 500, steps 30.000, batch 128 |
  | Starthilfe und Auswertung | p_repeat 0,3, eval_every 5000, n_test 2000 |
  | Stufen | (0,0, 0,01, 0,10, 0,25) |
  | Schwellen und Messungen | premise_min 0,80, probe_l2 1e-3, probe_folds 5, detect_quantile 0,95 |

- **Seeds:**
  - Entwicklung 4000–4001, Bestätigung 4100–4102, Hauptlauf 4200–4209;
  - Prüfsätze: Farbregeln 9001, bekannte Eigenschaften 9002;
  - Page-Test: Seed 4999, 100.000 Permutationen.
- **Kein Lauf auf Bestätigungs- oder Hauptlauf-Seeds** ohne ausdrückliche Freigabe des Nutzers.

## Präzisierung gegenüber der Spec (beim Schreiben des Plans gefunden)

- **Problem:** Spec §4.3 sagt, U_bekannt werde „mit denselben Kurven für diesen Satz“ berechnet. Auf bekannten Regeln ist aber a_ohne ≥ a_mit; der Nenner wäre ≤ 0, und U_bekannt wäre undefiniert.
- **Festlegung:**
  - U_bekannt = Σ_{k=2..8} (a_M(k) − 0,25) / Σ_{k=2..8} (a_mit(k) − 0,25) auf dem Prüfsatz mit bekannten Eigenschaften. Das ist der Anteil der idealen Leistung über dem Raten.
  - U_bekannt ist nur beschreibend.
  - Task 9 trägt das in Spec §4.3 nach.

## Prüffokus

1. **Paarung über die Stufen:** Würde eine Zufallsziehung nur bei Bedarf gemacht (etwa die Ersatz-Eigenschaft nur bei u ≥ p), wären die Stufen nicht mehr gepaart. Test in Task 2: Zwei Stufen mit gleichem Seed und gleichem Schritt erzeugen identische Tokens, außer in Sequenzen mit u < p.
2. **Gleiches Modell in zwei Prozessen:** Gleicher (Seed, p) in zwei gestarteten Prozessen muss dasselbe Ergebnis-JSON liefern (bis auf Laufzeiten). Test in Task 7.
3. **Abbruch mitten im Lauf:**
   - Keine halbe Ergebnisdatei.
   - Fertige Modelle werden übersprungen.
   - Ein fremder Fingerabdruck oder eine fremde Konfiguration bricht ab, ohne zu überschreiben.
   - Test in Task 7.
4. **Unvollständige Daten in der Auswertung:** Modelle mit nicht erfüllter Prämisse, Stufen mit weniger als 2 gültigen Modellen, unvollständige Seed-Blöcke für den Page-Test. Die Auswertung darf nicht abstürzen, sondern zeigt „–“ bzw. „nicht bewertbar“. Test in Task 8.
5. **Dateinamen je Stufe:** 0,1 und 0,10 müssen dieselbe Datei ergeben, 0,01 und 0,1 verschiedene. Das Format ist `p{p:.2f}_s{seed}.json`. Test in Task 7.

---

### Task 1: Vorbereitung, Tag und Konfiguration

**Dateien:**
- Neu: `kontextversuch/__init__.py`, `kontextversuch/requirements.txt`, `kontextversuch/config.py`, `kontextversuch/tests/__init__.py`, `kontextversuch/tests/helpers.py`, `kontextversuch/tests/test_config.py`
- Ändern: `pytest.ini`

**Schnittstellen:**
- Liefert: `Config` (frozen dataclass mit den Feldern und Standardwerten aus „Globale Vorgaben“), `Config.as_dict() -> dict` (Tupel als Liste), `Config.to_json(path)`, `Config.from_json(path) -> Config` (fehlende Schlüssel nehmen den Standard; ein unbekannter Schlüssel ist ein `ValueError`, der ihn nennt).
- Liefert: `tests/helpers.TINY = Config(d_model=32, n_layers=2, n_heads=2, d_ff=64, steps=200, batch=32, warmup=20, eval_every=100, n_test=200)`.

- [ ] **Schritt 1: Tag setzen, bevor neuer Code entsteht**
  - Es gibt keine `.py`-Änderung seit `c5c73e9`. Prüfen mit `python -m farbversuch.freeze verify`; erwartet wird `OK`.
  - Danach `git tag -a farbversuch-v2-final -m "Farbversuch v2: letzter Stand mit gültigem Freeze"` und `git push origin farbversuch-v2-final`.
- [ ] **Schritt 2: Abhängigkeiten**
  - `kontextversuch/requirements.txt` mit `numpy>=2.0` und `torch==2.14.1`.
  - Installieren mit `pip install -r kontextversuch/requirements.txt`.
  - Prüfen: `python -c "import torch; print(torch.__version__)"` gibt `2.14.1…` aus.
- [ ] **Schritt 3: `pytest.ini`** – `testpaths = farbversuch/tests kontextversuch/tests`.
- [ ] **Schritt 4: Fehlschlagende Tests** in `test_config.py`:
  - `test_defaults` prüft d_model 64, n_layers 3, steps 30000, stages (0.0, 0.01, 0.10, 0.25), premise_min 0.80.
  - `test_json_roundtrip` (tmp_path): `from_json(to_json(c)) == c`, die Stufen kommen als Tupel zurück.
  - `test_unknown_key_rejected`: `{"foo": 1}` ergibt einen `ValueError` mit „foo“.
- [ ] **Schritt 5:** `pytest kontextversuch/tests/test_config.py -v` schlägt fehl (ImportError).
- [ ] **Schritt 6:** `kontextversuch/config.py` umsetzen, nach dem Muster von `farbversuch/config.py`.
- [ ] **Schritt 7:**
  - `pytest -q` ist grün, der Farbversuch eingeschlossen.
  - `python -m farbversuch.freeze verify` meldet jetzt neue Dateien und das geänderte `pytest.ini`. Das ist erwartet, der Farbversuch ist über das Tag prüfbar.
- [ ] **Schritt 8: Commit** – `kontextversuch: Gerüst, Konfiguration, PyTorch-Abhängigkeit`.

### Task 2: Aufgaben (`tasks.py`)

**Dateien:** Neu: `kontextversuch/tasks.py`, `kontextversuch/tests/test_tasks.py`

**Schnittstellen:**
- Liefert die Konstanten `A, V, L, K, COLOR, Q, VOCAB, EX_LEN, T, Q_POS` (np.ndarray der „?“-Positionen), die Zufalls-Tags `DATA = 1, INIT = 2, PROBE = 3` und `TEST_SEEDS = {"color": 9001, "known": 9002}`.
- Liefert `@dataclass Batch`:
  - `tokens` (n, T) int64;
  - `objs` (n, K, A) int64, Werte je Eigenschaft;
  - `labels` (n, K) int64 in 0..3;
  - `rule_attr` (n,) int64;
  - `u` (n,) float64.
- Liefert `sample_batch(rng: np.random.Generator, n: int, p_color: float, p_repeat: float) -> Batch`.
- Liefert `train_batch(seed: int, step: int, n: int, p_color: float, p_repeat: float) -> Batch` mit `rng = np.random.default_rng([seed, DATA, step])`.
- Liefert `test_set(kind: str, n: int) -> Batch`:
  - `"color"`: Seed 9001, p_color = 1,0, p_repeat = 0;
  - `"known"`: Seed 9002, p_color = 0,0, p_repeat = 0;
  - jede andere Art ist ein `ValueError`.

- [ ] **Schritt 1: Fehlschlagende Tests:**
  - `test_labels_follow_rule`: Für jede Sequenz und jedes k gilt `labels[i,k] == perm_i[objs[i,k,rule_attr[i]]]`. π wird aus Paaren (Wert, Antwort) rekonstruiert und muss eine Bijektion sein.
  - `test_p0_never_color_p1_always`: Für 2000 Sequenzen gilt `rule_attr != 3` bei p_color = 0 und `== 3` bei p_color = 1.
  - `test_tokens_layout`: Position k·6 + 4 ist 20. Position k·6 + 5 ist 16 + labels. Die 4 Tokens davor sind genau {a·4 + objs[i,k,a] für a = 0..3}.
  - `test_order_uniform`: Über 4000 Beispiele steht jede Eigenschaft an jeder der 4 Stellen mit Anteil 0,25 ± 0,03.
  - `test_repeats_only_with_p_repeat`:
    - Bei p_repeat = 0,3 ist der Anteil der Beispiele k ≥ 1, deren Objekt einem früheren gleicht, ≥ 0,3. Er liegt etwas höher als 0,3, weil auch zufällige Gleichheiten mitzählen.
    - Bei p_repeat = 0 liegt er beim Zufallsniveau von höchstens 0,03.
  - `test_pairing_across_stages`: `train_batch(7, 3, 512, 0.0, 0.3)` und `train_batch(7, 3, 512, 0.25, 0.3)` haben gleiche `objs` und `u`. Die Tokens sind gleich in allen Sequenzen mit `u >= 0.25`, in den übrigen ist `rule_attr == 3`. **(Prüffokus 1)**
  - `test_test_sets_reproducible_and_distinct`: `test_set("color", 200)` zweimal ergibt gleiche Tokens; bei Farbe gilt `rule_attr == 3`, bei bekannt `rule_attr < 3`; `test_set("x", 1)` ist ein `ValueError`.
- [ ] **Schritt 2:** Die Tests schlagen fehl.
- [ ] **Schritt 3: `sample_batch` umsetzen.** Spec §3 nennt getrennte Zufallsströme. Der Plan erreicht dieselbe Paarung mit einem Strom je Schritt und fester Ziehungsreihenfolge. Die Ziehungen erfolgen **immer alle und in dieser Reihenfolge**, unabhängig von p_color und p_repeat:
  1. `objs = rng.integers(0, V, (n, K, A))`
  2. `rep = rng.random((n, K)) < p_repeat`, dann `rep[:, 0] = False`
  3. `src_u = rng.random((n, K))`. Für k = 1..K−1 nacheinander gilt: wo `rep[:, k]`, wird `objs[:, k] = objs[:, floor(src_u[:, k] · k)]` gesetzt.
  4. `order = np.argsort(rng.random((n, K, A)), axis=2)`
  5. `perm = np.argsort(rng.random((n, V)), axis=1)`
  6. `u = rng.random(n)`
  7. `other = rng.integers(0, A − 1, n)`; `rule_attr = np.where(u < p_color, COLOR, other)`
- [ ] **Schritt 4:** `pytest kontextversuch/tests/test_tasks.py -v` ist grün.
- [ ] **Schritt 5: Commit** – `kontextversuch: Regel-Aufgaben mit gemischter Reihenfolge, Starthilfe und gepaarten Seeds`.

### Task 3: Ideale Vergleichskurven (`ideal.py`)

**Dateien:** Neu: `kontextversuch/ideal.py`, `kontextversuch/tests/test_ideal.py`

**Schnittstellen:**
- Verwendet `Batch`, `A, V, L, K` aus Task 2.
- Liefert `ideal_curve(objs: np.ndarray, labels: np.ndarray, attrs: Sequence[int]) -> np.ndarray` mit der Form (K,) und der erwarteten Trefferquote je k nach Spec §4.2:
  - Hypothesen sind alle (a ∈ attrs, π ∈ 24 Permutationen).
  - Bei Gleichstand gilt 1/|M|.
  - Passt keine Hypothese mehr, gilt 0,25.
- Liefert `WITH_COLOR = (0, 1, 2, 3)` und `WITHOUT_COLOR = (0, 1, 2)`.

- [ ] **Schritt 1: Fehlschlagende Tests:**
  - `test_first_example_is_chance`: Der Wert bei k = 1 ist 0,25 für beide Hypothesenmengen.
  - `test_hand_case`: eine Sequenz, Regel Form, vier Beispiele mit verschiedenen Formwerten, alle anderen Eigenschaften überall gleich.
    - Nach Beispiel 1 sind nur noch Hypothesen mit π(Form₁) = y₁ und für Größe, Position, Farbe solche mit π(gemeinsamer Wert) = y₁ übrig.
    - Für Beispiel 2 (neuer Formwert, gleiche andere Werte) sagen die Form-Hypothesen eine der 3 übrigen Antworten voraus, die anderen y₁. Die Zahl der Hypothesen ist 6 für y₁ gegen je 2 für die übrigen Antworten; vorhergesagt wird also y₁.
    - Der erwartete Wert ist 0, weil die richtige Antwort ≠ y₁ ist.
    - Das wird ausgerechnet und festgehalten.
  - `test_with_ge_without_on_color_rules`: Auf `test_set("color", 500)` gilt `ideal_curve(..., WITH_COLOR) >= ideal_curve(..., WITHOUT_COLOR) - 1e-12` für alle k und ist bei k = 8 > 0,8.
  - `test_without_ge_with_on_known_rules`: Auf `test_set("known", 500)` gilt die umgekehrte Ungleichung.
  - `test_no_consistent_hypothesis_gives_chance`: Konstruiert ist eine Farbregel, bei der Beispiel 1 und 2 in Form, Größe und Position gleich sind, aber verschiedene Antworten haben. Dann gilt `ideal_curve(..., WITHOUT_COLOR)[2] == 0.25`.
- [ ] **Schritt 2:** Die Tests schlagen fehl.
- [ ] **Schritt 3: Umsetzen.**
  - Vorhersage-Tensor `pred[n, a, π, k] = π[objs[n, k, a]]`.
  - Passend bis k: `cumprod` der Gleichheit mit `labels` über die vorherigen Beispiele.
  - Stimmen je Antwort zählen und M bestimmen, alles vektorisiert mit numpy.
- [ ] **Schritt 4:** Die Tests sind grün.
- [ ] **Schritt 5: Commit** – `kontextversuch: exakte ideale Vergleichskurven mit und ohne Farbe`.

### Task 4: Decoder (`model.py`)

**Dateien:** Neu: `kontextversuch/model.py`, `kontextversuch/tests/test_model.py`

**Schnittstellen:**
- Verwendet `Config`, `VOCAB, T, Q_POS, A, V, L, INIT`.
- Liefert `class Decoder(nn.Module)`, gebaut als `Decoder(d_model, n_layers, n_heads, d_ff)`:
  - Token-Einbettung (21) plus gelernte Positions-Einbettung (48);
  - `nn.TransformerEncoder` aus `nn.TransformerEncoderLayer(d_model, n_heads, d_ff, dropout=0.0, batch_first=True, norm_first=True)` mit `enable_nested_tensor=False`, kausale Maske (`is_causal=True`), ohne abschließende Normierung;
  - `nn.Linear(d_model, 21)`.
  - Methoden: `hidden(tokens) -> (B, T, d)` (Ausgabe der Blöcke) und `forward(tokens) -> (B, T, 21)`.
- Liefert `label_logits(logits) -> (B, K, L)`, also `logits[:, Q_POS, 16:20]`.
- Liefert `build_model(cfg: Config, seed: int) -> Decoder`:
  - `torch.manual_seed(int(np.random.default_rng([seed, INIT]).integers(2**31)))` vor dem Bauen;
  - damit hängt die Initialisierung nur vom Seed ab.

- [ ] **Schritt 1: Fehlschlagende Tests:**
  - `test_param_count`: `build_model(Config(), 0)` hat genau 155.733 Parameter. Der Wert ist im Testlauf gemessen.
  - `test_shapes`: Bei 3 Sequenzen hat `forward` die Form (3, 48, 21) und `label_logits` die Form (3, 8, 4).
  - `test_causal` **(Leck-Schutz):** Für jedes k = 0..7 werden alle Tokens ab Position k·6 + 5 (Antwort von Beispiel k und alles danach) zufällig ersetzt. `label_logits[:, :k+1]` bleibt gleich (`torch.allclose`, atol 1e-6, rtol 0). Ein echtes Leck verändert die Werte weit stärker.
  - `test_init_depends_only_on_seed`: Zwei Aufrufe mit Seed 5 ergeben bitgleiche Gewichte, Seed 6 ergibt andere.
- [ ] **Schritt 2:** Die Tests schlagen fehl.
- [ ] **Schritt 3: Umsetzen.**
- [ ] **Schritt 4:** Die Tests sind grün.
- [ ] **Schritt 5: Commit** – `kontextversuch: kleiner Decoder mit kausaler Maske`.

### Task 5: Training (`train.py`)

**Dateien:** Neu: `kontextversuch/train.py`, `kontextversuch/tests/test_train.py`

**Schnittstellen:**
- Verwendet `build_model`, `label_logits`, `train_batch`; im Test `sample_batch`.
- Liefert `set_determinism() -> None` mit `torch.set_num_threads(1)` und `torch.use_deterministic_algorithms(True)`.
- Liefert `train_model(cfg: Config, seed: int, p_color: float, on_eval: Callable[[int, Decoder], None] | None = None) -> Decoder`:
  - für step = 1…cfg.steps: Batch aus `train_batch(seed, step, cfg.batch, p_color, cfg.p_repeat)`;
  - Fehler: `cross_entropy(label_logits(model(tokens)).reshape(-1, 4), labels.reshape(-1))`;
  - Optimierer: `AdamW(lr, weight_decay)` mit `LambdaLR(lambda s: min(1.0, (s + 1) / cfg.warmup))`;
  - nach jedem Schritt mit `step % eval_every == 0`: `on_eval(step, model)` im Modus eval und unter `no_grad`, danach zurück in train.

- [ ] **Schritt 1: Fehlschlagende Tests:**
  - `test_bitidentical`: `train_model(replace(TINY, steps=20), 3, 0.25)` zweimal im selben Prozess ergibt bitgleiche `state_dict`s.
  - `test_eval_callback_steps`: Bei steps 200 und eval_every 100 wird `on_eval` mit 100 und 200 aufgerufen.
  - `test_stage_and_seed_change_training`: Nach 20 Schritten ergeben Seed 3 mit p 0 und p 0,25 verschiedene Gewichte, ebenso Seed 3 und Seed 4 bei gleichem p.
  - `test_tiny_learns_easy_variant` (`slow`):
    - `replace(TINY, steps=1500, batch=64, p_repeat=0.5)` mit Seed 0 und p 0,25.
    - Die leichte Variante ist das Kopieren wiederholter Objekte. Geprüft wird auf `sample_batch(np.random.default_rng(0), 500, 0.25, 0.5)`: Die mittlere Trefferquote über k = 2..8 ist > 0,45 (Raten 0,25).
    - Im Kurztest vom 11.10.2026 (Wegwerf, Arbeitsordner) erreichte diese Mini-Konfiguration 0,50 schon nach 500 Schritten. Auf Regeln ohne Wiederholungen lag sie nach 3000 Schritten erst bei 0,32 (k = 8). Deshalb prüft der Test nicht die volle Aufgabe.
- [ ] **Schritt 2:** Die Tests schlagen fehl.
- [ ] **Schritt 3: Umsetzen.**
- [ ] **Schritt 4:** `pytest kontextversuch/tests/test_train.py -v -m "not slow"` und danach mit `slow` sind grün.
- [ ] **Schritt 5: Commit** – `kontextversuch: deterministische Trainingsschleife mit Aufwärmen und Zwischenständen`.

### Task 6: Messungen (`evaluate.py`)

**Dateien:** Neu: `kontextversuch/evaluate.py`, `kontextversuch/tests/test_evaluate.py`

**Schnittstellen:**
- Verwendet `test_set`, `ideal_curve`, `WITH_COLOR`, `WITHOUT_COLOR`, `label_logits`, `Q_POS`, `PROBE`.

Liefert:
- `accuracy_curve(model, batch) -> np.ndarray` mit der Form (K,): argmax über die 4 Antwort-Logits, gemittelt über die Sequenzen.
- `farbnutzung(a_m, a_mit, a_ohne) -> float`: Summen über die Indizes 1..7 (k = 2..8). Ein Nenner ≤ 0 ist ein `ValueError("Nenner ≤ 0 …")`.
- `u_known(a_m, a_mit) -> float`: Σ(a_m − 0,25)/Σ(a_mit − 0,25) über die Indizes 1..7, nach der Präzisierung oben.
- `sequence_stat(model, batch) -> np.ndarray` mit der Form (n,): mittlere Kreuzentropie über die 4 Antwort-Logits an den Indizes 2..7 (k = 3..8).
- `detection(stat_null, stat_test, q) -> dict`:
  - `threshold = np.quantile(stat_null, q)`;
  - `rate = mean(stat_test > threshold)`;
  - `null_rate = mean(stat_null > threshold)`.
- `group_folds(groups: np.ndarray, folds: int, seed: int) -> list[np.ndarray]`: Zeilenindizes je Testteil. Die Gruppen-IDs werden mit `default_rng([seed, PROBE])` permutiert und mit `array_split` auf `folds` Teile verteilt.
- `probe_accuracy(features, targets, groups, l2, folds, seed) -> float`:
  - multinomiale logistische Regression, Gewichte mit Bias, Strafe `l2/2·‖W‖²`;
  - Optimierung mit `torch.optim.LBFGS`, `max_iter = 500`, `line_search_fn = "strong_wolfe"`, ganzer Batch;
  - Teilungen über `group_folds`;
  - Rückgabe: mittlere Treffer auf den Testteilen.
- `reference(cfg) -> dict`: für `"color"` und `"known"` jeweils `{"batch": test_set(kind, cfg.n_test), "mit": ideal_curve(..., WITH_COLOR), "ohne": ideal_curve(..., WITHOUT_COLOR)}`.
- `checkpoint_metrics(model, ref) -> dict` mit den Schlüsseln `acc_color`, `acc_known` (Listen der Länge 8), `U`, `U_known`.
- `final_metrics(model, ref, cfg, seed) -> dict`:
  - alles aus `checkpoint_metrics`;
  - `premise_ok` (acc_known[7] ≥ cfg.premise_min);
  - `probe` (ein Wert je Eigenschaft `"Form"`, `"Größe"`, `"Position"`, `"Farbe"`, auf dem bekannten Satz, Merkmale `model.hidden(tokens)[:, Q_POS]`, Ziele `objs[:, :, a]`, Gruppen = Sequenznummer);
  - `detection` mit Nullstatistik aus dem bekannten Satz und Teststatistik aus dem Farbsatz;
  - `ideal`, also die Kurven `mit` und `ohne` beider Sätze als Listen.

- [ ] **Schritt 1: Fehlschlagende Tests:**
  - `test_farbnutzung_values`:
    - a_m = a_ohne ergibt 0;
    - a_m = a_mit ergibt 1;
    - die Hälfte dazwischen ergibt 0,5;
    - a_mit = a_ohne ergibt einen `ValueError`.
  - `test_u_known_values`: a_m = a_mit ergibt 1; a_m durchgehend 0,25 ergibt 0.
  - `test_detection_null_rate` mit 10.000 Normalwerten: `null_rate` liegt bei 0,05 ± 0,005; ein um +3 verschobener Testsatz hat `rate` > 0,9.
  - `test_probe_separable_and_random`:
    - Klassen linear trennbar (Merkmal = One-Hot der Klasse plus kleines Rauschen) ergibt > 0,95;
    - Zufallsmerkmale ergeben 0,25 ± 0,05;
    - `group_folds` legt jede Gruppe vollständig in genau einen Testteil, und die Teile decken alle Zeilen genau einmal ab.
  - `test_metrics_shapes_tiny`: Ein ungelerntes `TINY`-Modell liefert über `final_metrics` alle Schlüssel. Die Treffer liegen bei 0,25 ± 0,08, die Probe für die Farbe liegt in [0, 1].
- [ ] **Schritt 2:** Die Tests schlagen fehl.
- [ ] **Schritt 3: Umsetzen.**
- [ ] **Schritt 4:** Die Tests sind grün.
- [ ] **Schritt 5: Commit** – `kontextversuch: Farbnutzung, Prämisse, Probe und Bemerken`.

### Task 7: Treiber (`run.py`)

**Dateien:** Neu: `kontextversuch/run.py`, `kontextversuch/tests/test_run.py`

**Schnittstellen:**
- Verwendet `train_model`, `set_determinism`, `reference`, `checkpoint_metrics`, `final_metrics`, `Config`.

Liefert:
- `THREAD_VARS` (die fünf Variablen aus „Globale Vorgaben“).
- `env_block() -> dict`: Thread-Variablen, numpy- und torch-Version, Python, Maschine, CPU (Muster `farbversuch/run.py`).
- `fingerprint() -> str`: SHA-256 über alle `kontextversuch/*.py` (ohne `tests/`) und `env_block()`.
- `result_path(out: Path, p: float, seed: int) -> Path`, Name `f"p{p:.2f}_s{seed}.json"`.
- `run_model(seed: int, p: float, cfg: Config) -> dict` mit den Schlüsseln `seed`, `p`, `config`, `env`, `fingerprint`, `checkpoints` (Liste aus `{"step", **checkpoint_metrics}`), `final` (`final_metrics`) und `sec`.
- `parse_seeds(s: str) -> list[int]`: Format wie im Farbversuch, doppelte Seeds sind ein Fehler.
- `main(argv)` mit den Optionen `--seeds`, `--out`, `--config`, `--jobs` und `--stages` (Standard: `cfg.stages`).
  - Aufgaben sind alle (p, Seed) ohne vorhandenes Ergebnis.
  - Ein vorhandenes Ergebnis mit gleicher Konfiguration und gleichem Fingerabdruck wird übersprungen. Ein fremdes führt zu `SystemExit` mit Begründung, nichts wird überschrieben.
  - Sperre `<out>/.lock` wie in `farbversuch/run.py`.
  - Arbeitsprozesse im Pool `ProcessPoolExecutor(spawn)`. Ein `BrokenProcessPool` ergibt einen `SystemExit` mit dem Befehl zum Fortsetzen.
  - Jedes Ergebnis wird atomar geschrieben (fsync + `os.replace`).
  - Zeilen auf stderr: Start und Ende je Modell mit U und `premise_ok`.

- [ ] **Schritt 1: Fehlschlagende Tests,** mit `TINY` und steps 40, eval_every 20, n_test 100:
  - `test_result_path_format`: 0,1 und 0,10 ergeben denselben Pfad `p0.10_s4.json`, 0,01 ergibt `p0.01_s4.json`. **(Prüffokus 5)**
  - `test_run_model_keys`: Alle Schlüssel sind da, `len(checkpoints) == 2`.
  - `test_same_result_in_two_processes` (`slow`): `run_model(4, 0.25, cfg)` in zwei per `spawn` gestarteten Prozessen liefert gleiche JSONs, wenn `sec` und `env` entfernt werden. **(Prüffokus 2)**
  - `test_main_skips_and_refuses_foreign` (tmp_path):
    - Ein erster Lauf über 2 Seeds und 2 Stufen schreibt 4 Dateien.
    - Ein zweiter Lauf überspringt alle (Meldung auf stderr).
    - Eine Datei mit geändertem `fingerprint` führt zu `SystemExit`, und die Datei bleibt unverändert. **(Prüffokus 3)**
  - `test_no_partial_file` (`monkeypatch`): `_write_atomic` hinterlässt bei Ausnahme vor `os.replace` keine Ergebnisdatei.
  - `test_lock` (Muster aus den Farbversuch-Tests):
    - Eine lebende Sperre führt zum Abbruch.
    - Eine verwaiste Sperre wird übernommen.
    - Nach dem Lauf ist die Sperre entfernt.
  - `test_parse_seeds`: `"4000-4001"` ergibt [4000, 4001]; `"1,1"` ist ein Fehler.
- [ ] **Schritt 2:** Die Tests schlagen fehl.
- [ ] **Schritt 3: Umsetzen.** Muster sind `farbversuch/run.py`: `_write_atomic`, `_acquire_lock`, `_release_lock`, `_stage` und `parse_seeds`, übernommen und angepasst.
- [ ] **Schritt 4:** Die Tests sind grün, mit und ohne `slow`.
- [ ] **Schritt 5: Commit** – `kontextversuch: Treiber mit Wiederaufnahme, Sperre und Fingerabdruck`.

### Task 8: Auswertung (`analyze.py`)

**Dateien:** Neu: `kontextversuch/analyze.py`, `kontextversuch/tests/test_analyze.py`

**Schnittstellen:**
- Verwendet die Ergebnis-JSONs aus Task 7.

Liefert:
- `MAIN_SEEDS = tuple(range(4200, 4210))`, `CONFIRM_MIN_SEED = 4100`.
- `T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086, 21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042}`. Eine Tabelle, damit scipy nicht nötig ist; df > 30 ist ein Fehler.
- `t_interval(values) -> tuple[float, float] | None`: None bei weniger als 2 Werten.
- `category(values) -> str`:
  - `"geschlossen"`, wenn die obere Grenze < 0,2;
  - `"offen"`, wenn die untere Grenze > 0,5;
  - `"teilweise"` sonst;
  - `"–"` bei weniger als 2 Werten.
- `page_test(U: np.ndarray, n_perm: int = 100_000, seed: int = 4999) -> dict`:
  - U hat die Form (Seeds, m Stufen in steigender Reihenfolge); im Versuch ist m = 4, der Test nutzt auch m = 3.
  - Ränge je Zeile aufsteigend, mittlere Ränge bei Gleichstand.
  - L = Σ_j j·R_j mit j = 1..m.
  - p = (1 + #{L_perm ≥ L}) / (1 + n_perm), Vertauschung innerhalb jeder Zeile.
  - Rückgabe `{"L", "p", "n_blocks"}`. Bei weniger als 2 Zeilen ist sie `{"L": None, "p": None, "n_blocks": n}`.
- `load_results(out: Path) -> list[dict]`.
- `evaluate(results, seeds) -> dict`:
  - Gleiche Konfiguration und gleicher Fingerabdruck über alle Ergebnisse, sonst ein `ValueError`.
  - Jede Kombination aus Stufe und Seed muss da sein, sonst ein `ValueError`, der sie nennt.
  - Inhalt: P1–P5 nach Spec §5, Urteile nur bei `set(seeds) == set(MAIN_SEEDS)`, sonst None.
  - Je Stufe: U-Mittel, t-Intervall und Bootstrap-Intervall (10.000 Ziehungen, Seed 4998).
  - Der Page-Test nimmt nur Seeds, deren 4 Modelle alle `premise_ok` sind.
  - Bei Abbruch nach P1 werden P2–P5 als beschreibend gekennzeichnet. Ohne P2 gelten P3–P5 als „nicht deutbar“.
- `evaluate_confirmation(results, seeds) -> dict`:
  - Seeds unter 4100 oder aus `MAIN_SEEDS` sind ein `ValueError`.
  - `confirmed` heißt: alle Modelle `premise_ok` und das U-Mittel bei p = 0,25 ≥ 0,8.
- `report_markdown(ev) -> str` und `main(argv)` mit den Optionen `--out`, `--seeds` und `--confirm`.

- [ ] **Schritt 1: Fehlschlagende Tests,** mit Kunstergebnissen über eine Hilfsfunktion `fake_result(seed, p, U, premise_ok=True)`:
  - `test_page_matches_enumeration`:
    - Bei 3 Seeds mit 3 Stufen stimmt der p-Wert aus n_perm = 200.000 mit der vollständigen Aufzählung (6³ = 216 Fälle) auf ±0,01 überein.
    - Bei 4 Stufen ergibt sich dasselbe mit einer kleinen festen Matrix gegen 24² = 576 Fälle bei 2 Seeds.
  - `test_page_monotone_small_p`: 10 Seeds mit streng steigendem U ergeben p < 0,001.
  - `test_category_boundaries`: Werte mit oberer Grenze 0,19 ergeben „geschlossen“, mit unterer Grenze 0,51 „offen“, sonst „teilweise“; ein einzelner Wert ergibt „–“.
  - `test_t975_values`: `T975[9] == 2.262`, und `t_interval([0, 1])` liefert [0,5 − 12,706·0,5, 0,5 + 12,706·0,5] mit der Standardabweichung mit ddof = 1.
  - `test_p1_abort_and_descriptive`: 2 von 10 Modellen einer Stufe ohne Prämisse ergeben P1 nicht erfüllt; der Abbruch ist ausgelöst; P2–P5 sind als beschreibend gekennzeichnet; nichts stürzt ab. **(Prüffokus 4)**
  - `test_incomplete_blocks`: Fehlt die Prämisse bei einem Modell von Seed 4203, hat der Page-Test `n_blocks == 9`.
  - `test_verdicts_only_main`: Seeds 4000–4001 ergeben `fulfilled is None` überall.
  - `test_confirmation_rule`:
    - 12 Modelle mit U(0,25) = 0,85 und alle mit Prämisse ergeben „bestätigt“.
    - Eines ohne Prämisse ergibt „nicht bestätigt“.
    - Seeds 4200–4202 ergeben einen `ValueError`.
  - `test_mixed_fingerprint_rejected`.
- [ ] **Schritt 2:** Die Tests schlagen fehl.
- [ ] **Schritt 3: Umsetzen.**
- [ ] **Schritt 4:** Die Tests sind grün.
- [ ] **Schritt 5: Commit** – `kontextversuch: Auswertung P1–P5 mit Page-Test und Bestätigungsregel`.

### Task 9: Freeze, Dokumentation, Spec-Nachtrag

**Dateien:**
- Neu: `kontextversuch/freeze.py`, `kontextversuch/tests/test_freeze.py`, `kontextversuch/README.md`, `kontextversuch/PROTOKOLL.md`
- Ändern: `kontextversuch/analyze.py`, `kontextversuch/run.py`, `kontextversuch/tests/test_analyze.py`, `kontextversuch/tests/test_run.py`, `docs/superpowers/specs/2026-10-11-kontextversuch-v4-design.md` (§4.3), `docs/HANDOVER.md`

**Schnittstellen:**
- Liefert `source_files(root: Path) -> list[Path]`: alle `kontextversuch/**/*.py` (ohne `__pycache__`) und `kontextversuch/requirements.txt`, relativ zu root.
- Liefert `write_freeze(root, cfg)`: schreibt `kontextversuch/frozen_config.json` und `kontextversuch/freeze.sha256`.
- Liefert `verify_freeze(root) -> list[str]`: Problempfade, [] heißt in Ordnung. Dazu `main(argv)` mit `write` und `verify`.
- Die Logik ist die von `farbversuch/freeze.py`, mit der Wurzel `kontextversuch/`.
- Liefert `freeze_problems(results, root) -> list[str]` in `analyze.py` (Muster `farbversuch/analyze.py`): Prüfsummen und `frozen_config.json` gegen die Konfiguration der Ergebnisse.
  - `analyze.main` mit `set(seeds) == set(MAIN_SEEDS)` setzt bei Problemen eine Zeile „WARNUNG …“ an den Anfang des Berichts und berichtet trotzdem.
  - `run.main` lehnt Seeds aus `MAIN_SEEDS` ab, solange `verify_freeze` nicht leer ist oder die Konfiguration von `frozen_config.json` abweicht (`SystemExit` mit Begründung). Das ist eine zusätzliche Sperre gegen einen versehentlichen Hauptlauf.

- [ ] **Schritt 1: Fehlschlagende Tests** (tmp_path mit kopierter Mini-Struktur):
  - `test_write_then_verify_ok`;
  - `test_changed_file_reported`;
  - `test_new_file_reported`;
  - `test_farbversuch_files_ignored`: Eine Änderung unter `farbversuch/` stört die Prüfung nicht.
  - in `test_analyze.py`: `test_main_seeds_warn_without_freeze` und `test_other_seeds_do_not_check_freeze` (Muster der Farbversuch-Tests mit `monkeypatch` auf `freeze.REPO_ROOT`).
  - in `test_run.py`: `test_main_seeds_refused_without_freeze`; die Entwicklungs-Seeds laufen ohne Freeze.
- [ ] **Schritt 2:** Die Tests schlagen fehl.
- [ ] **Schritt 3:** Umsetzen. Danach sind die Tests grün.
- [ ] **Schritt 4: Dokumentation:**
  - `kontextversuch/README.md`: Zweck, Installation (`pip install -r kontextversuch/requirements.txt`), die Befehle `run`, `analyze` und `freeze`, Laufzeiten, das Git-Tag für den Farbversuch.
  - `kontextversuch/PROTOKOLL.md`: die Testläufe vom 11.10.2026 (Tabelle aus Spec §10) und die Präzisierung zu U_bekannt.
  - Spec §4.3: die Präzisierung zu U_bekannt eintragen.
  - `docs/HANDOVER.md`: ein Abschnitt „Kontextversuch (v4)“ mit dem Stand und den nächsten Schritten.
- [ ] **Schritt 5:** `pytest -q` (alles) und `pytest -q -m "not slow"` sind grün. Die echten Zahlen kommen ins Protokoll.
- [ ] **Schritt 6: Commit und Push** – `kontextversuch: Freeze, Dokumentation, Präzisierung U_bekannt`.

### Task 10: Entwicklungsrunde (Seeds 4000–4001)

**Dateien:** Neu: `kontextversuch/results/dev1/` (Ergebnisse); Ändern: `kontextversuch/PROTOKOLL.md`

- [ ] **Schritt 1: Nichtnutzung nachweisen.**
  - Ergebnisordner, Git-Historie und Befehlsprotokolle der Sitzung auf die Seeds 4000–4209 durchsuchen.
  - Das Ergebnis kommt ins Protokoll.
  - Erwartet wird: nur Erwähnungen in Spec, Plan und Doku.
- [ ] **Schritt 2: Lauf.**
  - Befehl: `python -m kontextversuch.run --seeds 4000-4001 --out kontextversuch/results/dev1 --jobs 4 2>> kontextversuch/results/dev1.log`, im Hintergrund.
  - Dauer etwa 3 h.
  - Nach einem Abbruch denselben Befehl erneut starten.
- [ ] **Schritt 3: Auswertung.**
  - Befehl: `python -m kontextversuch.analyze --out kontextversuch/results/dev1 --seeds 4000-4001` (explorativ).
  - Ins Protokoll kommen Prämisse und U je Modell sowie die Zwischenstände.
  - **Entschieden wird nur nach Prämisse und Positivkontrolle (U bei p = 0,25).** U bei p = 0 und p = 0,01 wird notiert und nicht für Entscheidungen genutzt.
- [ ] **Schritt 4: Commit und Push** der Ergebnisse und des Protokolls.
- [ ] **Schritt 5: Halt.** Dem Nutzer das Ergebnis berichten.
  - Bei erfüllter Prämisse und Positivkontrolle: Vorschlag, die Bestätigung 4100–4102 laufen zu lassen.
  - Sonst ein Vorschlag für Änderungen im Rahmen der erlaubten Größen (Spec §6).
  - Keine Bestätigung ohne Freigabe.
