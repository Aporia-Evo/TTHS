# Farbversuch v2 – Implementierungsplan (Delta auf die v1-Umsetzung)

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die bestehende v1-Umsetzung auf Spec v2 bringen: Übungs-Ontologie, residualisierter Modellvergleich mit Mindestverbesserung δ, P1b-Geschlossenheit, strengere Kalibrierung, S1-A mit 25.000 Permutationen, Bestätigungsauswertung und parallele Läufe über Seeds und Bedingungen.

**Architecture:** Neue Mechanik bleibt in `monitor.py` (Erklären, Vor-Öffnen) und einem neuen kleinen Modul `closure.py` (P1b-Messung). `run.py` orchestriert Phase 1 v2 und bekommt einen gestuften Parallel-Treiber. `analyze.py` berichtet die neuen Größen und wertet die Bestätigung aus. Das Bemerken bleibt unverändert.

**Tech Stack:** Python 3.11, numpy ≥ 2.0, pytest ≥ 8.

**Spec:** `docs/superpowers/specs/2026-10-03-farb-wiederoeffnung-v2-design.md` (bindend). Ausgangspunkt ist der Code auf `claude/dreamy-wozniak-7xt321` ab `9ee2f93`. Der v1-Plan (`docs/superpowers/plans/2026-10-03-farb-wiederoeffnung.md`) gilt mit seinen Festlegungen weiter, soweit dieser Plan nichts anderes sagt.

## Global Constraints

- Python 3, nur numpy (plus pytest).
- `routine.py`, `forward.py`, `monitor.py` greifen nie auf Bedingung, Wechselzeitpunkt oder `C_SPECIAL` zu; der bestehende AST-Isolationstest muss grün bleiben.
- Das Bemerken (Überraschung aus dem Phase-1-Vorwärtsmodell, Schwellen, CUSUM) ist für alle Systeme gleich und wird durch v2 nicht verändert. Die Übungs-Ontologie wirkt nur auf das Erklären.
- Alle Null-Schwellen und δ: **größter** der 20 Null-Werte (`max_null_alarms = 0`); Null-Ströme haben **400** Episoden.
- Vor-Öffnen: höchstens **8** Merkmale; M3 mit fester Mindestverbesserung **0,01**; Übungspuffer = letzte `buffer_size` (2000) Schritte der Phase-1-Vorwärtsdaten.
- Im Einsatz: höchstens **3** wieder geöffnete Merkmale über die Übungs-Ontologie hinaus; Merkmale der Übungs-Ontologie werden nie erneut getestet und zählen nie als „geöffnet“.
- P1b: Restanteil ≤ **0,15**, Verschiebung ≤ **0,25**, Verschiebung über **500** Positionen.
- S1-Permutationen: Arm B **1000**, Arm A **25.000**, blockweise zu **1000**.
- Gleicher Seed, gleiche Ergebnisse (außer `_sec`), auch zwischen sequentiellem `run_seed` und dem parallelen Treiber.
- Rechnen nur mit festen BLAS-Threads (bestehendes Verhalten von `main`).

## Festlegungen (wo die Spec v2 offen ist)

1. Der Übungspuffer und die δ-Puffer der Null-Ströme haben die Länge `cfg.buffer_size`; es gibt kein eigenes Längenfeld.
2. RNG-Schlüssel: Vor-Öffnen M3 Runde r: `rng(seed, PREOPEN, i, r)`; Vor-Öffnen S1: `rng(seed, PREOPEN, i, 0)`; δ-Puffer j: `rng(seed, DELTA, i, j)`; P1b-Probe: `rng(seed, PROBE)`. Dabei ist `i = SYSTEMS.index(name)`. Neue Tags: `PREOPEN, DELTA, PROBE = 12, 13, 14`.
3. Residualisieren je Teilung vektorisiert über alle Kandidaten: `B = lstsq(Xb_tr, F_tr)`, `R_tr = F_tr − Xb_tr·B`, `R_te = F_te − Xb_te·B`. Ein Kandidat mit `‖R_tr‖ < 1e-8·‖F_tr‖` (auch Nullspalten und konstante Spalten) hat Verbesserung genau 0, ohne Anpassung. Das ersetzt die bisherige Konstantenprüfung.
4. Öffnungsregel: alle Teilungen > 0 **und** Mittel > δ (strikt). δ = 0 ergibt die v1-Regel.
5. δ-Gewinn eines Null-Puffers = größte mittlere Verbesserung unter den Kandidaten mit allen Teilungen > 0, sonst 0,0.
6. P1b-Restanteil: je Nachbarzelle (4 Richtungen) nur Zeilen, in denen die Zelle frei ist. Ziel ist der Farbindex. Probe: `fit_logreg` mit Bias auf z bzw. auf der Rohbeobachtung, `l2 = cfg.fwd_l2`, 5 Teilungen nach Episoden. Mehrheitsbasis = häufigste Farbe der Trainingsteilung. Eine Zelle wird ausgelassen, wenn sie < 20 freie Zeilen hat oder (Roh − Mehrheit) ≤ 0,05. Restanteil = Mittel der Zellwerte. Bleibt keine Zelle übrig, ist er `nan` und die Prämisse gilt als nicht erfüllt.
7. P1b-Verschiebung: die ersten 500 Positionen der Farbinvarianz-Läufe (gleiche Karten und Umfärbung wie P1). Wert = mittleres ‖z − z′‖ / mittleres ‖z‖.
8. Bestätigung (Spec §8): jedes der drei Kriterien einzeln mit ≥ ⌈0,8·n⌉ Seeds, bei n = 5 also 4. Ein Seed mit gescheiterter Prämisse zählt bei den Kriterien 2 und 3 als nicht erfüllt. Eine Bestätigungsauswertung mit Seeds aus 400–409 ist ein Fehler.
9. `total_sec` = Vorbereitungszeit + Summe der Bedingungszeiten, in beiden Ausführungswegen gleich definiert.
10. Ergebnis-JSON v2 ergänzt: `"practice": {system: [{"cand", "name"}]}`, `"delta": {M3-System: float}`, in `"premise"` zusätzlich `"restanteil"` und `"shift"`. Je System in `"conditions"` zusätzlich `"practice"` und `"delta"` (bei S1 `None`). `"opened"` enthält nur Wiederöffnungen; jeder Eintrag hat zusätzlich `"gain"` (bei M3 die mittlere Verbesserung des geöffneten Kandidaten, bei S1 `None`). Die Nutzbarkeit (Spec §6) ist der `gain` der ersten richtigen Öffnung von M3 unter `red`.

## Review Focus

1. **Arm A schöpft beim Vor-Öffnen die Obergrenze 8 aus,** etwa durch Rauschbits. Erwartet: Abbruch bei 8, kein Fehler. Test: `test_pre_open_m3_cap_and_determinism` (Task 2).
2. **Kein Null-Puffer hat einen zulässigen Kandidaten:** δ ist dann genau 0,0, und die Regel fällt auf „alle Teilungen > 0“ zurück. Test: `test_m3_null_gain_zero_without_eligible` (Task 2).
3. **P1b mit entarteten Zellen** (immer Wand oder immer dieselbe Farbe): Die Zelle wird ausgelassen, bei keiner gültigen Zelle ist das Ergebnis `nan`, ohne Absturz. Test: `test_restanteil_degenerate_is_nan` (Task 5).
4. **Fortsetzen nach Abbruch, während eine Zwischendatei einer anderen Konfiguration im Arbeitsordner liegt:** Erwartet wird Neuberechnung, keine Wiederverwendung. Test: `test_stale_prep_is_not_reused` (Task 7).
5. **Gescheiterte Prämisse im parallelen Treiber:** Es werden keine Bedingungsjobs gestartet, und `conditions` ist `null`. Test: `test_staged_premise_failure` (Task 7).

## Dateien

```
farbversuch/config.py    neue Felder, Standardwerte v2
farbversuch/seeds.py     Tags PREOPEN, DELTA, PROBE
farbversuch/monitor.py   m3_improvements, select_m3(delta), m3_null_gain, pre_open_m3, perm_pvalues(chunk), s1_explain(max_new), pre_open_s1, Monitor(practice, deltas, n_perm_A, perm_chunk)
farbversuch/closure.py   NEU: color_restanteil, representation_shift
farbversuch/run.py       Phase 1 v2, premise P1b, deploy v2, prepare_seed/result_json, gestufter Treiber
farbversuch/analyze.py   Bericht v2, evaluate_confirmation, --confirm
docs/HANDOVER.md, docs/PROJEKTBESCHREIBUNG.md
```
Testbefehl: `python -m pytest -q` (schnell: `-m "not slow"`). Importe in Testblöcken sind weggelassen.

---

### Task 1: Konfiguration und Seed-Tags v2

**Files:**
- Modify: `farbversuch/config.py`, `farbversuch/seeds.py`, `farbversuch/tests/helpers.py` (TINY), `farbversuch/tests/test_run_phase1.py` (bestehender Defaults-Test)
- Test: `farbversuch/tests/test_config_v2.py`

**Interfaces:**
- Produces (`Config`):
  - Geänderte Standardwerte: `n_null_episodes = 400`, `max_null_alarms = 0`.
  - Neue Felder: `n_perm_A: int = 25000`, `perm_chunk: int = 1000`, `pre_open_delta: float = 0.01`, `max_pre_open: int = 8`, `max_restanteil: float = 0.15`, `max_shift: float = 0.25`, `n_shift_positions: int = 500`.
  - `n_perm` (1000) gilt für Arm B.
- Produces (`seeds.py`): `PREOPEN, DELTA, PROBE = 12, 13, 14`
- Produces (`TINY`): zusätzlich `n_perm_A=400, max_restanteil=1.0, max_shift=10.0` (die Mini-Routine soll P1b nicht zum Abbruch bringen).

- [ ] **Step 1: Failing tests**

```python
def test_config_v2_defaults():
    c = Config()
    assert (c.n_null_streams, c.n_null_episodes, c.max_null_alarms) == (20, 400, 0)
    assert (c.n_perm, c.n_perm_A, c.perm_chunk) == (1000, 25000, 1000)
    assert (c.pre_open_delta, c.max_pre_open) == (0.01, 8)
    assert (c.max_restanteil, c.max_shift, c.n_shift_positions) == (0.15, 0.25, 500)

def test_seed_tags_unique():
    tags = [TEACHER, INIT, FORWARD, NULL, INVARIANCE, RECOLOR, PREMISE_FWD, PGLOBAL, DEPLOY, CV, PERM, PREOPEN, DELTA, PROBE]
    assert len(set(tags)) == 14 and (PREOPEN, DELTA, PROBE) == (12, 13, 14)
```
Im bestehenden `test_config_defaults_match_spec` die Erwartung `(1000, 20, 300, 1)` auf `(1000, 20, 400, 0)` ändern.

- [ ] **Step 2: RED** · `python -m pytest farbversuch/tests/test_config_v2.py farbversuch/tests/test_run_phase1.py -q -m "not slow"` · Expected: FAIL (fehlende Felder/Tags)
- [ ] **Step 3: Felder, Tags und TINY ergänzen**
- [ ] **Step 4: GREEN** und dann die ganze Suite (`python -m pytest -q`) · Expected: alles grün
- [ ] **Step 5: Commit** · `git commit -m "feat(config): v2-Felder und Seed-Tags"`

---

### Task 2: M3 – Residualisieren, Mindestverbesserung, Vor-Öffnen

**Files:**
- Modify: `farbversuch/monitor.py`
- Test: `farbversuch/tests/test_explain_m3.py` (ergänzen)

**Interfaces:**
- Consumes: `fit_logreg`, `mean_loglik`, `fwd_design`, `cv_folds`, `FitStats`
- Produces (`monitor.py`):
```python
def m3_improvements(Z, A, D, F, opened: Sequence[int], rng: np.random.Generator, l2: float = 1e-3, n_folds: int = 5,
                    tol: float = 1e-6, max_iter: int = 500, stats: FitStats | None = None) -> tuple[np.ndarray, np.ndarray]
    # (imp (len(candidates), n_folds), candidates) – residualisiert (Festlegung 3); rng nur für die Teilung
def select_m3(imp: np.ndarray, candidates: Sequence[int], delta: float = 0.0) -> int | None   # alle > 0 und Mittel > delta
def m3_explain(..., delta: float = 0.0, stats=None, info: dict | None = None) -> int | None
    # = select_m3(*m3_improvements(...), delta); bei einer Öffnung info["gain"] = deren mittlere Verbesserung
def m3_null_gain(Z, A, D, F, opened, rng, **fit_kw) -> float          # Festlegung 5
def pre_open_m3(Z, A, D, F, rng_for_round: Callable[[int], np.random.Generator], delta: float,
                max_open: int = 8, **fit_kw) -> list[int]           # greedy über m3_explain (Modul-Global), Runde r mit rng_for_round(r)
```

- [ ] **Step 1: Failing tests** (nutzt das vorhandene `slide_data()`)

```python
def test_select_m3_requires_mean_above_delta():
    assert select_m3(np.array([[.004] * 5, [.02] * 5]), [0, 1], delta=.01) == 1
    assert select_m3(np.array([[.004] * 5]), [0], delta=.01) is None

def test_duplicates_and_base_copies_give_exact_zero_without_fit():
    Z, A, D, F = slide_data(); st = FitStats()
    Fx = np.stack([F[:, 0], F[:, 0], 1 - F[:, 0], (A == 0).astype(np.uint8)], 1)   # Signal, Duplikat, Komplement, Basisspalte
    imp, cands = m3_improvements(Z, A, D, Fx, [0], np.random.default_rng(1), stats=st)
    assert list(cands) == [1, 2, 3] and (imp == 0).all() and st.n_fits == 5          # nur die Basismodelle

def test_three_identical_copies_open_at_most_once():
    Z, A, D, F = slide_data()
    F4 = np.stack([F[:, 0]] * 3 + [F[:, 1]], 1)
    assert pre_open_m3(Z, A, D, F4, lambda r: np.random.default_rng(r), delta=0.0) == [0]

def test_m3_null_gain_zero_without_eligible():                 # Review Focus 2
    Z, A, D, F = slide_data()
    assert m3_null_gain(Z, A, D, F, [], np.random.default_rng(1)) > 0.05
    assert m3_null_gain(Z, A, D, F, [0], np.random.default_rng(1)) < 0.005
    assert m3_null_gain(Z, A, D, np.zeros((len(A), 1), np.uint8), [], np.random.default_rng(1)) == 0.0

def test_m3_explain_reports_gain():
    Z, A, D, F = slide_data(); info = {}
    assert m3_explain(Z, A, D, F, [], np.random.default_rng(1), info=info) == 0 and info["gain"] > 0.05

def test_pre_open_m3_cap_and_determinism(monkeypatch):         # Review Focus 1
    calls = iter(range(100))
    monkeypatch.setattr(monitor, "m3_explain", lambda *a, **k: next(calls))
    assert pre_open_m3(None, None, None, None, lambda r: None, delta=.01) == list(range(8))
    monkeypatch.undo()
    Z, A, D, F = slide_data()
    r1 = pre_open_m3(Z, A, D, F, lambda r: np.random.default_rng(r), delta=.01)
    assert r1 == pre_open_m3(Z, A, D, F, lambda r: np.random.default_rng(r), delta=.01) == [0]
```
Die bestehenden M3-Tests bleiben unverändert grün, auch `test_m3_skips_constant_column_without_fit` mit 15 Anpassungen.

- [ ] **Step 2: RED** · `python -m pytest farbversuch/tests/test_explain_m3.py -q` · Expected: FAIL (ImportError `m3_improvements`)
- [ ] **Step 3: Implementieren** (Festlegungen 3–5). `pre_open_m3` ruft `m3_explain` als Modul-Global auf, mit den bisher geöffneten als `opened`. Es stoppt bei `None` oder bei `max_open`.
- [ ] **Step 4: GREEN**, dazu `test_leak.py` und `test_isolation.py` · Expected: grün
- [ ] **Step 5: Commit** · `git commit -m "feat(monitor): M3 residualisiert, Mindestverbesserung, Vor-Öffnen"`

---

### Task 3: S1 – blockweise Permutationen, max_new, Vor-Öffnen

**Files:**
- Modify: `farbversuch/monitor.py`
- Test: `farbversuch/tests/test_explain_s1.py` (ergänzen und anpassen)

**Interfaces:**
- Produces:
```python
def perm_pvalues(S, F, rng, n_perm: int = 1000, chunk: int = 1000) -> tuple[np.ndarray, np.ndarray]
    # zieht dieselbe Folge von n_perm Permutationen wie bisher, aber in Blöcken von höchstens chunk; Ergebnis unabhängig von chunk
def s1_explain(S, F, opened, rng, n_perm: int = 1000, alpha: float = 0.05, max_new: int = 3, chunk: int = 1000) -> list[int]
    # testet alle Kandidaten außerhalb opened; liefert höchstens max_new neue
def pre_open_s1(S, F, rng, n_perm: int, alpha: float = 0.05, max_open: int = 8, chunk: int = 1000) -> list[int]
    # = s1_explain(S, F, [], rng, n_perm, alpha, max_new=max_open, chunk=chunk)
```

- [ ] **Step 1: Failing tests**

```python
def test_perm_chunked_equals_unchunked():
    rng = np.random.default_rng(0); F = (rng.random((300, 7)) < .3).astype(np.uint8)
    S = 1. + 2. * F[:, 2] + rng.normal(0, 1, 300)
    a = perm_pvalues(S, F, np.random.default_rng(3), n_perm=2500, chunk=1000)
    b = perm_pvalues(S, F, np.random.default_rng(3), n_perm=2500, chunk=2500)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])

def test_s1_arm_a_can_reject_with_25000_perms():
    rng = np.random.default_rng(0); F = (rng.random((300, 1192)) < .3).astype(np.uint8)
    S = 1. + 3. * F[:, 5] + rng.normal(0, .1, 300)
    assert s1_explain(S, F, [], np.random.default_rng(1), n_perm=25000) == [5]

def test_s1_max_new_counts_only_new():
    rng = np.random.default_rng(0); F = (rng.random((400, 5)) < .3).astype(np.uint8)
    S = 1. + F[:, :4] @ np.array([3., 3., 5., 3.]) + rng.normal(0, .1, 400)
    assert s1_explain(S, F, [0, 1], np.random.default_rng(1), max_new=1) == [2]
    assert set(s1_explain(S, F, [0, 1], np.random.default_rng(1), max_new=3)) >= {2, 3}

def test_pre_open_s1_caps_at_max_open():
    rng = np.random.default_rng(0); F = (rng.random((400, 12)) < .3).astype(np.uint8)
    S = 1. + F.sum(1) * 3. + rng.normal(0, .1, 400)
    assert len(pre_open_s1(S, F, np.random.default_rng(1), n_perm=1000, max_open=8)) == 8
```
Den bestehenden `test_s1_respects_cap_and_opened` auf `max_new=1` umstellen. `test_s1_arm_a_cannot_reject` bleibt, mit dem Standardwert 1000.

- [ ] **Step 2: RED** · `python -m pytest farbversuch/tests/test_explain_s1.py -q` · Expected: FAIL
- [ ] **Step 3: Implementieren.** Die Permutationen kommen in derselben Reihenfolge aus `rng` wie bisher. Der Speicher hängt höchstens von `chunk` ab.
- [ ] **Step 4: GREEN**, dazu `test_leak.py` · Expected: grün
- [ ] **Step 5: Commit** · `git commit -m "feat(monitor): S1 blockweise Permutationen, max_new, Vor-Öffnen"`

---

### Task 4: Monitor mit Übungs-Ontologie und δ

**Files:**
- Modify: `farbversuch/monitor.py` (`_SystemState`, `Monitor`)
- Test: `farbversuch/tests/test_monitor.py` (ergänzen)

**Interfaces:**
- Consumes: Tasks 2–3
- Produces:
  - `Monitor.__init__(..., practice: Mapping[str, Sequence[int]] | None = None, deltas: Mapping[str, float] | None = None, n_perm_A: int = 25000, perm_chunk: int = 1000)`. Fehlende Einträge bedeuten leere Übungs-Ontologie bzw. δ = 0,0.
  - Je System gilt `known = practice + wieder geöffnet`.
  - M3 ruft `m3_explain(..., known, ..., delta=deltas[name])`.
  - S1 ruft `s1_explain(..., known, ..., n_perm=(n_perm if arm=="B" else n_perm_A), max_new=max_open − len(wieder geöffnet), chunk=perm_chunk)`.
  - Erklärt wird nur, solange `len(wieder geöffnet) < max_open`.
  - `results()[name]` bekommt zusätzlich `"practice": [{"cand", "name"}]` und `"delta": float | None` (bei S1 `None`).
  - `"opened"` enthält nur Wiederöffnungen, jeder Eintrag mit `"gain"`: M3 übergibt `info={}` an `m3_explain` und trägt `info.get("gain")` ein, S1 `None`.

- [ ] **Step 1: Failing tests** (Helfer `make`/`feed` aus der Datei; `make` reicht `**kw` an `Monitor` weiter)

```python
def test_practice_not_retested_not_counted(monkeypatch):
    seen = []
    monkeypatch.setattr(monitor, "m3_explain", lambda Z, A, D, F, opened, rng, **k: seen.append(list(opened)) or None)
    m = make(systems=("M3-B",), practice={"M3-B": [4]}); feed(m, 10)
    r = m.results()["M3-B"]
    assert seen == [[4]] and r["opened"] == [] and r["practice"] == [{"cand": 4, "name": "Wand"}]

def test_cap_counts_only_reopened(monkeypatch):
    nxt = iter([0, 1, 2, 3]); monkeypatch.setattr(monitor, "m3_explain", lambda *a, **k: next(nxt))
    m = make(systems=("M3-B",), practice={"M3-B": [4, 5]}); feed(m, 60)
    assert [o["cand"] for o in m.results()["M3-B"]["opened"]] == [0, 1, 2]

def test_delta_and_perms_per_system(monkeypatch):
    got = {}
    monkeypatch.setattr(monitor, "m3_explain", lambda *a, **k: got.setdefault("delta", k["delta"]) and None)
    monkeypatch.setattr(monitor, "s1_explain", lambda *a, **k: got.setdefault(k["n_perm"], k["max_new"]) and [])
    m = make(deltas={"M3-B": .02, "M3-A": .03}, n_perm_A=25000); feed(m, 10)
    assert got["delta"] == .02 and got[1000] == 3 and got[25000] == 3
    assert m.results()["S1-B"]["delta"] is None and m.results()["M3-A"]["delta"] == .03

def test_opened_records_gain(monkeypatch):
    def fake(*a, info=None, **k):
        info["gain"] = .07
        return 0
    monkeypatch.setattr(monitor, "m3_explain", fake)
    m = make(systems=("M3-B",)); feed(m, 10)
    assert m.results()["M3-B"]["opened"][0]["gain"] == .07
```

- [ ] **Step 2: RED** · `python -m pytest farbversuch/tests/test_monitor.py -q` · Expected: FAIL
- [ ] **Step 3: Implementieren**
- [ ] **Step 4: GREEN**, ganze Suite · Expected: grün (die bestehenden Monitor-Tests laufen ohne `practice`/`deltas` wie bisher)
- [ ] **Step 5: Commit** · `git commit -m "feat(monitor): Übungs-Ontologie und δ je System"`

---

### Task 5: P1b-Messung (closure.py)

**Files:**
- Create: `farbversuch/closure.py`
- Test: `farbversuch/tests/test_closure.py`

**Interfaces:**
- Consumes: `fit_logreg`, `fwd_design`-unabhängig; `DELTAS`, `CH_WALL`, `CH_COLOR`, `obs_index` aus `world`
- Produces:
```python
def color_restanteil(Z: np.ndarray, obs: np.ndarray, episode_ids: np.ndarray, rng: np.random.Generator,
                     l2: float = 1e-3, n_folds: int = 5, min_rows: int = 20, min_gap: float = 0.05) -> float   # Festlegung 6
def representation_shift(Z: np.ndarray, Z_recolored: np.ndarray) -> float                                     # Festlegung 7
```
Teilung nach Episoden: eindeutige Episoden-IDs mit `rng` permutieren und mit `np.array_split` in `n_folds` Gruppen teilen.

- [ ] **Step 1: Failing tests**

```python
def probe_data(n_maps=300, seed=0):
    rng = np.random.default_rng(seed); obs, eps = [], []
    for e in range(n_maps):
        m = make_map(rng, .15)
        for pos in [m.start, m.goal]:
            obs.append(observe(m, pos)); eps.append(e)
    return np.array(obs), np.array(eps)

def test_restanteil_colour_blind_is_near_zero():
    obs, eps = probe_data(); Z = obs[:, :49].astype(float)          # nur Wandkanal
    assert color_restanteil(Z, obs, eps, np.random.default_rng(1)) < .05

def test_restanteil_copying_is_near_one():
    obs, eps = probe_data()
    assert color_restanteil(obs.astype(float), obs, eps, np.random.default_rng(1)) > .95

def test_restanteil_degenerate_is_nan():                          # Review Focus 3
    obs, eps = probe_data(20); obs = obs.copy()
    for dr, dc in DELTAS:
        obs[:, obs_index(CH_WALL, dr, dc)] = 1
        for ch in CH_COLOR: obs[:, obs_index(ch, dr, dc)] = 0
    assert np.isnan(color_restanteil(obs.astype(float), obs, eps, np.random.default_rng(1)))

def test_representation_shift():
    Z = np.ones((10, 2))
    assert representation_shift(Z, Z) == 0. and np.isclose(representation_shift(Z, np.zeros((10, 2))), 1.)
```

- [ ] **Step 2: RED** · `python -m pytest farbversuch/tests/test_closure.py -q` · Expected: FAIL (ModuleNotFoundError)
- [ ] **Step 3: Implementieren**
- [ ] **Step 4: GREEN** · Expected: 4 passed
- [ ] **Step 5: Commit** · `git commit -m "feat(closure): P1b Restanteil und Verschiebung"`

---

### Task 6: Phase 1 v2, Prämisse P1b, Einsatz v2

**Files:**
- Modify: `farbversuch/run.py`
- Test: `farbversuch/tests/test_run_phase1.py`, `farbversuch/tests/test_run_deploy.py` (ergänzen)

**Interfaces:**
- Consumes: Tasks 1–5, `candidates_A`, `candidates_B`, `SYSTEMS`, `null_threshold`
- Produces:
  - `Phase1` bekommt die Felder:
    - `practice_obs`, `practice_actions`, `practice_disps`, `practice_episodes`: der Übungspuffer, letzte `buffer_size` Schritte der Vorwärtsdaten, mit Episoden-IDs.
    - `practice: dict[str, list[int]]` für jedes System in `cfg.systems`.
    - `deltas: dict[str, float]` für jedes M3-System in `cfg.systems`.
  - `invariance_and_shift(seed, cfg, routine) -> tuple[float, float]` ersetzt `color_invariance`; derselbe Lauf, Verschiebung aus den ersten `n_shift_positions` Positionen.
  - `premise_checks` bekommt zusätzlich `"restanteil"` und `"shift"`; `ok` umfasst `restanteil <= max_restanteil` und `shift <= max_shift`, wobei `nan` als nicht erfüllt gilt.
  - `deploy` übergibt `practice=p1.practice, deltas=p1.deltas, n_perm_A=cfg.n_perm_A, perm_chunk=cfg.perm_chunk`.
  - `run_seed` ergänzt das Ergebnis um `"practice"` und `"delta"` (Festlegung 10).
- Ablauf in `phase1`:
  1. Routine trainieren.
  2. Vorwärtsdaten erzeugen und das Vorwärtsmodell anpassen.
  3. Übungspuffer bilden.
  4. Vor-Öffnen je System mit den Schlüsseln aus Festlegung 2:
     - M3: `pre_open_m3(..., delta=cfg.pre_open_delta, max_open=cfg.max_pre_open)`.
     - S1: `pre_open_s1` auf der Überraschung des Übungspuffers, Permutationen je Arm.
  5. Null-Ströme mit `cfg.n_null_episodes`. Dabei werden zusätzlich die letzten `buffer_size` Schritte jedes Stroms behalten.
  6. Schwellen setzen, mit `max_alarms = cfg.max_null_alarms`.
  7. δ je M3-System: `null_threshold([m3_null_gain(...) für jeden Null-Puffer j], cfg.max_null_alarms)`.

- [ ] **Step 1: Failing tests**

```python
@pytest.mark.slow
def test_phase1_v2_tiny(tiny_phase1):
    p = tiny_phase1
    assert set(p.practice) == set(TINY.systems) and all(len(v) <= TINY.max_pre_open for v in p.practice.values())
    assert set(p.deltas) == {s for s in TINY.systems if s.startswith("M3")} and all(d >= 0 for d in p.deltas.values())
    assert len(p.practice_obs) == len(p.practice_episodes) == TINY.buffer_size

def test_delta_is_max_of_null_gains(monkeypatch):
    gains = iter([.1, .5, .2, .4, .3])
    monkeypatch.setattr(run, "m3_null_gain", lambda *a, **k: next(gains))
    assert run.calibrate_delta([(None, None, None, None)] * 5, [], lambda j: None, max_alarms=0) == .5

@pytest.mark.slow
def test_premise_has_p1b(tiny_phase1):
    r = premise_checks(0, TINY, tiny_phase1)
    assert isinstance(r["restanteil"], float) and r["shift"] >= 0.
    assert r["ok"] == bool(r["color_invariance"] >= TINY.min_invariance and r["fwd_surprise"] < r["freq_surprise"]
                           and r["restanteil"] <= TINY.max_restanteil and r["shift"] <= TINY.max_shift)

@pytest.mark.slow
def test_run_seed_v2_schema():
    r = run_seed(0, TINY)
    assert set(r["practice"]) == set(TINY.systems) and set(r["delta"]) == {"M3-B"}
    assert {"practice", "delta"} <= set(r["conditions"]["red"]["M3-B"]) and json.loads(json.dumps(r)) == r
```
- `calibrate_delta(buffers: Sequence[tuple], opened: Sequence[int], rng_for_buffer: Callable[[int], np.random.Generator], max_alarms: int, **fit_kw) -> float` wird als kleine Hilfsfunktion in `run.py` eingeführt. `buffers[j] = (Z, A, D, F)`. Sie ruft `m3_null_gain(*buffers[j], opened, rng_for_buffer(j), **fit_kw)` als Modul-Global auf und liefert `null_threshold(gains, max_alarms)`.
- Die Isolations-, Leck- und Determinismustests bleiben grün.

- [ ] **Step 2: RED** · `python -m pytest farbversuch/tests/test_run_phase1.py farbversuch/tests/test_run_deploy.py -q` · Expected: FAIL
- [ ] **Step 3: Implementieren**
- [ ] **Step 4: GREEN**, ganze Suite · Expected: grün. Die Laufzeit von `run_seed(0, TINY)` im Bericht nennen.
- [ ] **Step 5: Commit** · `git commit -m "feat(run): Phase 1 v2 mit Übungs-Ontologie, δ und P1b"`

---

### Task 7: Paralleler Treiber über Seeds und Bedingungen

**Files:**
- Modify: `farbversuch/run.py` (`run_seed`, `main`)
- Test: `farbversuch/tests/test_run_deploy.py` (ergänzen)

**Interfaces:**
- Produces:
```python
@dataclass
class Prepared:
    seed: int; config: dict; p1: Phase1; premise: dict; p_global: dict | None; sec: float
def prepare_seed(seed: int, cfg: Config) -> Prepared                     # Phase 1, Prämisse, p_global
def result_json(prep: Prepared, conditions: dict | None, cond_sec: dict[str, float]) -> dict
def run_seed(seed: int, cfg: Config) -> dict                              # sequentiell: prepare + deploy je Bedingung + result_json
```
- `main` arbeitet in drei Stufen, jeweils mit `multiprocessing.get_context("spawn").Pool(max(1, jobs))`:
  1. Für Seeds ohne fertige `seed_<n>.json`: `prepare_seed` und Pickle nach `<out>/.work/seed_<n>.prep.pkl`. Eine vorhandene Pickle wird nur wiederverwendet, wenn ihre `config` gleich `cfg.as_dict()` ist.
  2. Für Seeds mit erfüllter Prämisse: je `(seed, condition)` ein Job, `deploy` und Ergebnis nach `<out>/.work/seed_<n>.<condition>.json`.
  3. `result_json` atomar nach `seed_<n>.json` schreiben und die `.work`-Dateien dieses Seeds löschen.
- Die bestehenden Regeln gelten weiter: Threads festlegen, Konfigurationsprüfung vorhandener Ergebnisse, doppelte Seeds werden abgewiesen, Fortschritt auf stderr.

- [ ] **Step 1: Failing tests**

```python
@pytest.mark.slow
def test_staged_equals_sequential(tmp_path):
    cfg = tmp_path / "c.json"; TINY.to_json(cfg)
    main(["--config", str(cfg), "--seeds", "0", "--out", str(tmp_path / "o"), "--jobs", "3"])
    staged = json.loads((tmp_path / "o" / "seed_0.json").read_text())
    assert strip_sec(staged) == strip_sec(json.loads(json.dumps(run_seed(0, TINY))))
    assert not any((tmp_path / "o" / ".work").glob("seed_0.*"))

@pytest.mark.slow
def test_staged_premise_failure(tmp_path):                     # Review Focus 5
    cfg = tmp_path / "c.json"; dataclasses.replace(TINY, min_invariance=1.01).to_json(cfg)
    main(["--config", str(cfg), "--seeds", "0", "--out", str(tmp_path / "o"), "--jobs", "2"])
    r = json.loads((tmp_path / "o" / "seed_0.json").read_text())
    assert r["premise"]["ok"] is False and r["conditions"] is None

@pytest.mark.slow
def test_stale_prep_is_not_reused(tmp_path):                    # Review Focus 4
    work = tmp_path / "o" / ".work"; work.mkdir(parents=True)
    stale = prepare_seed(0, dataclasses.replace(TINY, epochs=5))
    (work / "seed_0.prep.pkl").write_bytes(pickle.dumps(stale))
    cfg = tmp_path / "c.json"; TINY.to_json(cfg)
    main(["--config", str(cfg), "--seeds", "0", "--out", str(tmp_path / "o"), "--jobs", "2"])
    assert json.loads((tmp_path / "o" / "seed_0.json").read_text())["config"] == TINY.as_dict()
```
`strip_sec` aus `test_determinism.py` nach `farbversuch/tests/helpers.py` verschieben und von beiden Stellen importieren.

- [ ] **Step 2: RED** · Expected: FAIL (`prepare_seed` fehlt)
- [ ] **Step 3: Implementieren**
- [ ] **Step 4: GREEN**, ganze Suite · Expected: grün, inklusive der bestehenden CLI-Tests
- [ ] **Step 5: Commit** · `git commit -m "feat(run): paralleler Treiber über Seeds und Bedingungen"`

---

### Task 8: Auswertung v2 und Bestätigung

**Files:**
- Modify: `farbversuch/analyze.py`
- Test: `farbversuch/tests/test_analyze.py` (ergänzen)

**Interfaces:**
- Produces:
```python
def evaluate_confirmation(results: Sequence[dict], seeds: Sequence[int]) -> dict
    # {"n", "need", "premise", "no_false_open", "red_correct", je {"count", "fulfilled"}, "confirmed": bool}
    # premise: P1 und P1b ok; no_false_open: M3-B öffnet bei none und global nichts; red_correct: M3-B red korrekt
    # need = ceil(0.8 * n); Seeds aus MAIN_SEEDS oder doppelte Seeds -> ValueError (Festlegung 8)
```
- `report_markdown` bekommt eine Tabelle je Seed: Farbinvarianz, Restanteil, Verschiebung, Übungs-Ontologie je System (Namen), δ je M3-System und die Nutzbarkeit (`gain` der ersten richtigen M3-B-Öffnung unter `red`). Bei alten Ergebnissen ohne diese Schlüssel steht „–“. Dazu kommt eine Zeile mit der erwarteten Fehlalarmrate pro Strom ≈ 1/(n_null_streams + 1).
- CLI: `--confirm` hängt einen Abschnitt „Bestätigung (Spec v2 §8)“ an, mit den drei Kriterien, Zählung/benötigt und erfüllt/nicht erfüllt.

- [ ] **Step 1: Failing tests** (bestehende `fake_result`/`sysres` um `premise` P1b-Felder und `practice` erweitern)

```python
def test_confirmation_counts_and_need():
    seeds = list(range(500, 505))
    rs = [fake_result(s, red_ok=s != 500, global_open=s == 501) for s in seeds]
    ev = evaluate_confirmation(rs, seeds)
    assert ev["need"] == 4 and ev["red_correct"] == {"count": 4, "fulfilled": True}
    assert ev["no_false_open"]["count"] == 4 and ev["confirmed"]

def test_confirmation_rejects_main_seeds_and_duplicates():
    with pytest.raises(ValueError): evaluate_confirmation([fake_result(400)], [400])
    with pytest.raises(ValueError): evaluate_confirmation([fake_result(500)], [500, 500])

def test_failed_premise_counts_against_confirmation():
    seeds = list(range(500, 505))
    ev = evaluate_confirmation([fake_result(s, ok=s > 501) for s in seeds], seeds)
    assert ev["premise"]["count"] == 3 and not ev["confirmed"]

def test_report_shows_practice_and_p1b():
    seeds = list(range(400, 410))
    md = report_markdown(evaluate([fake_result(s) for s in seeds], seeds))
    assert "Restanteil" in md and "Übungs-Ontologie" in md and "Nutzbarkeit" in md and "4,8" in md
```
- `evaluate` muss die neuen Seed-Felder tragen, damit `report_markdown` sie zeigt (z. B. `ev["seeds"]`). Zu wählen sind Schlüssel, die der Test oben erfüllt.

- [ ] **Step 2: RED** · Expected: FAIL
- [ ] **Step 3: Implementieren**
- [ ] **Step 4: GREEN**, ganze Suite · Expected: grün
- [ ] **Step 5: Commit** · `git commit -m "feat(analyse): Bericht v2 und Bestätigungsauswertung"`

---

### Task 9: Dokumentation und Lauf-Prompt

**Files:**
- Modify: `docs/HANDOVER.md`, `docs/PROJEKTBESCHREIBUNG.md`

- [ ] **Step 1: `PROJEKTBESCHREIBUNG.md` auf Spec v2 bringen.**
  - Übungs-Ontologie, P1b „weitgehend geschlossen“, Mindestverbesserung, Bestätigung 500–504.
  - Verweis auf die Spec v2 als bindend.
- [ ] **Step 2: `HANDOVER.md` neu fassen.**
  - Stand v2 und Teststand.
  - Bindend ist die Spec v2, der Plan v2 kommt hinzu.
  - Nächste Schritte: Pilot Seed 0 → Bestätigung 500–504 → Entscheidung des Nutzers → Einfrieren → Hauptlauf.
  - Laufbefehle mit `--jobs` passend zur Kernzahl.
  - Der Prompt für Claude Scientific, mit den Befehlen und dem Stopp vor 400–409:
    ```bash
    python -m farbversuch.run --config farbversuch/pilot_config.json --seeds 500-504 --jobs 16 --out farbversuch/results/confirm
    python -m farbversuch.analyze --results farbversuch/results/confirm --seeds 500-504 --confirm
    ```
  - Die Restpunkte aus der v1-Handover, die noch gelten.
- [ ] **Step 3: Prüfen.** `python -m pytest -q` ist grün, und `python -m farbversuch.freeze verify` meldet sauber eine fehlende `freeze.sha256` (noch nicht eingefroren).
- [ ] **Step 4: Commit** · `git commit -m "docs: Handover und Projektbeschreibung v2, Lauf-Prompt"`
