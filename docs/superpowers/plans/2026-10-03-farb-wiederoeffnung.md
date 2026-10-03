# Farbversuch (Wiederöffnen einer ignorierten Dimension) – Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein numpy-Experiment bauen und durchführen. Es prüft, ob ein System eine beim Üben ignorierte Dimension (Bodenfarbe) per Modellvergleich wieder öffnet, wenn sie bedeutsam wird. Dazu gehören Vorregistrierung, Pilot, Einfrieren, Hauptlauf und Bericht.

**Architecture:** Kleine Module mit klaren Grenzen: `world` (Gitterwelt), `routine` (BFS-Lehrer, Encoder und Policy), `forward` (logistische Regression, Vorwärtsmodell), `monitor` (Puffer, Kandidaten, Bemerken, Erklären, vier Systeme), `run` (Phasen pro Seed), `analyze` (Kennzahlen, P1–P5), `freeze` (Einfrieren). Nur `run` kennt Bedingung und Wechselzeitpunkt. Die Monitore beobachten passiv, die Routine handelt unverändert.

**Tech Stack:** Python 3.11, numpy ≥ 2.0, pytest ≥ 8. Keine weiteren Pakete.

**Spec:** `docs/superpowers/specs/2026-10-03-farb-wiederoeffnung-design.md`

## Global Constraints

- Python 3, nur numpy (plus pytest für Tests).
- Die Antwort „Rot ist rutschig“ darf nirgends im System vorkommen. `routine.py`, `forward.py` und `monitor.py` haben keinen Zugriff auf Bedingung, Wechselzeitpunkt oder `C_SPECIAL`.
- Der Lehrer (BFS mit vollständiger Karte) wird nur in der Übungsphase und nur für die Routine benutzt.
- Nach Phase 1 werden Routine und Vorwärtsmodell nicht mehr verändert. Die Überraschung im Puffer kommt immer vom Vorwärtsmodell aus Phase 1.
- Pilot: Seed 0. Hauptlauf: Seeds 400–409, erst nach `frozen_config.json` und `freeze.sha256`.
- Im Pilot dürfen nur geändert werden: Trainings-Hyperparameter der Routine und des Vorwärtsmodells, Puffergröße, Prüfintervall. Jede Änderung kommt mit Grund in `PROTOKOLL.md`.
- Gleicher Seed ergibt identische Ergebnisse. Ausgenommen sind Wandzeit-Felder (Schlüssel enden auf `_sec`).
- Bericht: feste Gliederung nach Spec §11. „bestätigt“, „bewiesen“, „aus ersten Prinzipien“ nur bei tatsächlich erfüllter Vorhersage.

## Festlegungen (wo die Spec offen ist)

Jede Aufgabe setzt diese Punkte voraus. Sie sind beim Review der Stelle, an der der Plan über die Spec hinaus entscheidet.

1. Jede Episode spielt auf einer neu gezogenen Karte. Eine ungültige Karte (Abstand < 5 oder kein Weg) wird komplett neu gezogen.
2. Zufall: `np.random.default_rng([seed, TAG, strom, episode, teil])`, wobei `teil` 0 die Karte und 1 die Dynamik ist. Die vier Einsatzbedingungen benutzen dieselben Schlüssel, die Bedingung ist kein Schlüsselteil. Vor dem Wechsel sind die vier Ströme deshalb identisch.
3. `step` zieht pro Aufruf genau drei Zahlen in dieser Reihenfolge: `u_slip = rng.random()`, `a_rand = rng.integers(4)`, `u_red = rng.random()`.
4. Der Rot-Effekt wirkt nur, wenn das System sich tatsächlich bewegt hat und die neue Zelle `C_SPECIAL` hat. Richtung ist die ausgeführte Aktion, es gibt keine Kette. Das Ziel wird erst auf der Endposition geprüft (auch die Zielzelle hat eine Farbe).
5. Zielrichtungsbits: oben = Zielzeile < eigene Zeile, unten = >, links = Zielspalte <, rechts = >. Zwei Bits können gleichzeitig gesetzt sein.
6. `N(0; 0,01)` bedeutet Standardabweichung 0,01. Die Policy-Gewichte `W` starten bei 0. „Volltraining“ heißt Full-Batch-Gradientenabstieg auf mittlerer Kreuzentropie + (wd/2)·‖E‖².
7. Die Routine handelt deterministisch (argmax, bei Gleichstand der kleinste Index). Der Lehrer wählt den Nachbarn mit dem kleinsten BFS-Abstand, bei Gleichstand den kleinsten Aktionsindex. Beim Sammeln der Lehrerdaten handelt der Lehrer mit Grundrutschen. Gespeichert wird immer die *gewählte* Aktion.
8. Logistische Regression (Vorwärtsmodell, Basis- und erweiterte Modelle): Ziel ist die mittlere negative Log-Likelihood + (l2/2)·‖W‖² über **alle** Gewichte inklusive Bias, `l2 = 1e-3` (Pilot-Parameter). Gelöst wird mit L-BFGS bis max|Gradient| < 1e-6. Grund: Doppelschritte kommen beim Üben nie vor, ohne L2 auf dem Bias liefe ihr Logit gegen −∞.
9. Schwellen: Ein Alarm heißt „Wert > Schwelle“. Die Schwelle ist das zweitgrößte der 20 Null-Strom-Maxima, also liegt genau ein Strom darüber.
10. Prüfpunkte liegen nach jeder 10. abgeschlossenen Episode (E = 10, 20, …, 400). M3 prüft nur, wenn der Puffer ≥ 500 Schritte hat. Zeitpunkt eines Ereignisses ist E. Ein CUSUM-Alarm mitten in Episode i (0-basiert) zählt als E = i + 1.
11. Erklären beginnt am Prüfpunkt des Bemerkens (bei S1 am ersten Prüfpunkt ≥ Alarm). M3 öffnet höchstens ein Merkmal pro Prüfpunkt. S1 öffnet alle Holm-Ablehnungen in p-Reihenfolge bis zur Obergrenze 3. Geöffnete Merkmale werden nicht mehr getestet.
12. Kreuzvalidierung: `rng(seed, CV, E).permutation(n)`, aufgeteilt mit `np.array_split` in 5 Teile. Das Basismodell startet kalt (W = 0), das erweiterte warm aus der Basis mit 0 für die neue Spalte. Ist eine Kandidatenspalte in der Trainingsteilung konstant, ist die Verbesserung genau 0, ohne Anpassung.
13. Der S1-Test ist einseitig (Überraschung bei Merkmal = 1 höher). p = (1 + #{Permutation ≥ beobachtet}) / (1 + 1000). Holm läuft über alle noch nicht geöffneten Kandidaten. Bei gleichem p entscheidet die größere Differenz, dann der Index.
14. Farbinvarianz: Pro Karte werden alle Farben neu gezogen (gleiche Wände, Start, Ziel). Verglichen wird die Aktion an denselben Positionen der Originaltrajektorie. Vorwärts-Prämisse: 300 frische Übungsepisoden. Das Häufigkeitsmodell nutzt die Klassenhäufigkeiten der Vorwärts-Trainingsdaten mit +1-Glättung.
15. `p_global`: Bisektion auf [0,10; 1,0] mit denselben Karten und Würfen für jedes p. Ist der Zielwert nicht einschließbar, gilt der Randwert mit Kennzeichen `bracketed: false`.
16. Latenz = E − 100. Nicht bemerkt oder nicht zugeschrieben ergibt 300 (zensiert). Ein Seed, der P1 nicht erfüllt, zählt bei P2, P3 und beim Abbruchkriterium gegen M3-B und fällt aus den Vergleichen P4 und P5 heraus.
17. P4: „langsamer“ heißt höhere mittlere Zuschreibungslatenz bei `red` über die Seeds (zensiert bei 300). Fehlzuschreibungen werden über Seeds und Bedingungen summiert.
18. Test-Hook `Config.systems` (Standard: alle vier). Nur die Mini-Konfiguration der Tests lässt M3-A weg, weil es pro Prüfung ~30 s kostet.

## Review Focus

1. Doppelschritte kommen beim Üben nie vor. Ihre Überraschung muss trotzdem endlich bleiben, sonst werden Mittelwert und CUSUM `inf`. Test: `test_unseen_class_finite_surprise` (Task 4).
2. Dichte Wände (0,30): Die Kartenerzeugung muss schnell gültige Karten liefern. Test: `test_make_map_dense_terminates` (Task 1).
3. Rot-Rutschen auf das Ziel oder über das Ziel hinaus: Die Episode endet genau dann, wenn die Endposition das Ziel ist. Test: `test_red_slide_onto_and_past_goal` (Task 2).
4. Bemerken vor dem Wechsel in einem `red`-Strom ist ein Fehlalarm ohne Latenz. Eine spätere richtige Zuschreibung zählt trotzdem. Test: `test_prechange_alarm_in_red` (Task 13).
5. `p_global` ist nicht einschließbar (auch 1,0 erreicht die Rot-Überraschung nicht): kein Endlos-Loop, Kennzeichen gesetzt. Test: `test_bisect_unbracketed` (Task 11).

## Dateien

```
requirements.txt  pytest.ini  .gitignore
farbversuch/__init__.py
farbversuch/world.py     Karte, Beobachtung, Schritt, Rollout
farbversuch/routine.py   Lehrer-Aktion, Routine (Encoder + Policy), Training
farbversuch/forward.py   Logistische Regression (L-BFGS), Vorwärtsmodell, Häufigkeitsmodell
farbversuch/seeds.py     rng-Schlüssel und Tags
farbversuch/monitor.py   Ringpuffer, Kandidaten, Bemerken, Kalibrierung, Erklären (M3, S1), Monitor
farbversuch/config.py    Config mit allen Parametern, JSON
farbversuch/run.py       Phasen pro Seed, Einsatz, CLI
farbversuch/analyze.py   Kennzahlen, P1–P5, Abbruch, Markdown
farbversuch/freeze.py    frozen_config.json, freeze.sha256, Prüfung
farbversuch/tests/       helpers.py, conftest.py, test_*.py
farbversuch/PROTOKOLL.md  frozen_config.json  freeze.sha256  BERICHT.md  results/
```

Testbefehl überall: `python -m pytest -q` (schnell: `-m "not slow"`). Importe in den Testblöcken sind weggelassen; die Namen stehen im Interfaces-Block der jeweiligen Aufgabe.

---

### Task 1: Gerüst, Karte und Beobachtung

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `.gitignore`, `farbversuch/__init__.py`, `farbversuch/world.py`, `farbversuch/tests/__init__.py`, `farbversuch/tests/helpers.py`
- Test: `farbversuch/tests/test_world_map.py`

**Interfaces:**
- Produces (`world.py`):
```python
SIZE, VIEW, HALF = 9, 7, 3
N_ACTIONS = 4
DELTAS = ((-1, 0), (1, 0), (0, -1), (0, 1))          # oben, unten, links, rechts
N_COLORS, C_SPECIAL = 4, 0
CH_WALL, CH_GOAL, CH_COLOR = 0, 1, (2, 3, 4, 5)       # Kanäle je Fensterzelle
OBS_DIM = 298
GOALDIR = (294, 295, 296, 297)                        # Ziel oben, unten, links, rechts
def obs_index(ch: int, dr: int, dc: int) -> int       # ch*49 + (dr+3)*7 + (dc+3)
@dataclass(frozen=True)
class Map:
    walls: np.ndarray        # (9,9) bool, Rand True
    colors: np.ndarray       # (9,9) int8, -1 genau auf Wänden
    start: tuple[int, int]
    goal: tuple[int, int]
def bfs_distances(walls: np.ndarray, goal: tuple[int, int]) -> np.ndarray   # (9,9) int, -1 = Wand/unerreichbar
def make_map(rng: np.random.Generator, wall_p: float, min_dist: int = 5) -> Map
def recolor(m: Map, rng: np.random.Generator) -> Map  # gleiche Wände/Start/Ziel, Farben neu gezogen
def observe(m: Map, pos: tuple[int, int]) -> np.ndarray   # (298,) uint8
```
- Produces (`tests/helpers.py`): `open_map(colour: int = 1, start=(4, 4), goal=(1, 1)) -> Map` (nur Randwände, alle Innenzellen Farbe `colour`).

`make_map` zieht in dieser Reihenfolge: Innenwände `rng.random((7, 7)) < wall_p`, Farben `rng.integers(0, 4, (9, 9))` (auf Wänden −1), freie Zellen zeilenweise, `rng.choice(len(free), 2, replace=False)` für Start und Ziel. Ist der Abstand < `min_dist` oder gibt es keinen Weg, wird alles neu gezogen. Außerhalb des Gitters setzt `observe` das Wandbit und keine Farbe.

- [ ] **Step 1: Gerüst anlegen und installieren**

`requirements.txt`: `numpy>=2.0`, `pytest>=8`. `.gitignore`: `__pycache__/`, `.pytest_cache/`. `pytest.ini`:
```ini
[pytest]
testpaths = farbversuch/tests
pythonpath = .
markers =
    slow: Integrationstests mit Mini-Training
```
Run: `pip install -r requirements.txt`

- [ ] **Step 2: Failing tests schreiben**

```python
def test_obs_shape_dtype():
    o = observe(open_map(), (4, 4))
    assert o.shape == (OBS_DIM,) and o.dtype == np.uint8

def test_outside_grid_is_wall():
    o = observe(open_map(start=(1, 1)), (1, 1))
    assert o[obs_index(CH_WALL, -3, -3)] == 1
    assert all(o[obs_index(ch, -3, -3)] == 0 for ch in CH_COLOR)

def test_each_cell_wall_xor_one_colour():
    m = make_map(np.random.default_rng(3), 0.15)
    o = observe(m, m.start).astype(int)
    for dr in range(-3, 4):
        for dc in range(-3, 4):
            assert o[obs_index(CH_WALL, dr, dc)] + sum(o[obs_index(ch, dr, dc)] for ch in CH_COLOR) == 1

def test_goal_bit_and_direction():
    o = observe(open_map(goal=(6, 3)), (4, 4))
    assert o[obs_index(CH_GOAL, 2, -1)] == 1 and o[obs_index(CH_GOAL, 0, 0)] == 0
    assert list(o[list(GOALDIR)]) == [0, 1, 1, 0]

def test_colour_channel_matches_map():
    assert observe(open_map(colour=2), (4, 4))[obs_index(CH_COLOR[2], 1, 0)] == 1

def test_make_map_constraints():
    rng = np.random.default_rng(0)
    for _ in range(200):
        m = make_map(rng, 0.15)
        assert m.walls[0].all() and m.walls[-1].all() and m.walls[:, 0].all() and m.walls[:, -1].all()
        assert ((m.colors == -1) == m.walls).all()
        assert abs(m.start[0] - m.goal[0]) + abs(m.start[1] - m.goal[1]) >= 5
        assert bfs_distances(m.walls, m.goal)[m.start] > 0

def test_make_map_dense_terminates():          # Review Focus 2
    rng, t = np.random.default_rng(1), time.perf_counter()
    maps = [make_map(rng, 0.30) for _ in range(200)]
    assert time.perf_counter() - t < 5.0
    assert np.mean([m.walls[1:-1, 1:-1].mean() for m in maps]) > 0.2

def test_make_map_deterministic():
    a, b = make_map(np.random.default_rng(7), 0.15), make_map(np.random.default_rng(7), 0.15)
    assert (a.walls == b.walls).all() and (a.colors == b.colors).all() and (a.start, a.goal) == (b.start, b.goal)

def test_recolor_keeps_layout():
    m = make_map(np.random.default_rng(2), 0.15)
    r = recolor(m, np.random.default_rng(9))
    assert (r.walls == m.walls).all() and (r.start, r.goal) == (m.start, m.goal)
    assert ((r.colors == -1) == m.walls).all() and (r.colors != m.colors).any()

def test_bfs_distances_open_map():
    d = bfs_distances(open_map().walls, (1, 1))
    assert d[1, 1] == 0 and d[4, 4] == 6 and d[0, 0] == -1
```

- [ ] **Step 3: Tests laufen lassen, sie schlagen fehl**

Run: `python -m pytest farbversuch/tests/test_world_map.py -q` · Expected: FAIL (ImportError `farbversuch.world`)

- [ ] **Step 4: `world.py` und `helpers.open_map` implementieren** (Signaturen oben)

- [ ] **Step 5: Tests bestehen**

Run: `python -m pytest farbversuch/tests/test_world_map.py -q` · Expected: 10 passed

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pytest.ini .gitignore farbversuch
git commit -m "feat(welt): Karte und Beobachtung"
```

---

### Task 2: Schritt, Rutschen, Rot-Effekt, Rollout

**Files:**
- Modify: `farbversuch/world.py`
- Test: `farbversuch/tests/test_world_step.py`

**Interfaces:**
- Consumes: `Map`, `observe`, `DELTAS`, `C_SPECIAL` (Task 1)
- Produces (`world.py`):
```python
DISP = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1), (-2, 0), (2, 0), (0, -2), (0, 2))
N_DISP = 9
def disp_class(dr: int, dc: int) -> int
def step(m: Map, pos: tuple[int, int], action: int, rng: np.random.Generator,
         p_slip: float, red_active: bool, red_p: float = 0.5) -> tuple[tuple[int, int], int]   # (neue Position, Klasse)
@dataclass
class Traj:
    obs: np.ndarray          # (T,298) uint8, vor dem Schritt
    actions: np.ndarray      # (T,) gewählte Aktion
    disps: np.ndarray        # (T,) Verschiebungsklasse
    positions: np.ndarray    # (T,2) vor dem Schritt
    reached: bool
def rollout(m: Map, choose: Callable[[np.ndarray, tuple[int, int]], int], rng: np.random.Generator,
            p_slip: float, red_active: bool, max_steps: int = 40, red_p: float = 0.5) -> Traj
```
Die Unit-Klasse für Aktion a ist `a + 1`, die Doppelschritt-Klasse `a + 5`.

- [ ] **Step 1: Failing tests schreiben**

```python
def run_steps(m, pos, a, n, **kw):
    rng = np.random.default_rng(0)
    return [step(m, pos, a, rng, **kw) for _ in range(n)]

def test_slip_rate():
    out = run_steps(open_map(), (4, 4), 0, 20000, p_slip=0.10, red_active=False)
    assert abs(np.mean([c != 1 for _, c in out]) - 0.075) < 0.006

def test_wall_blocks():
    assert all(r == ((1, 4), 0) for r in run_steps(open_map(), (1, 4), 0, 50, p_slip=0.0, red_active=False))

def test_red_effect_only_when_active():
    m = open_map(colour=C_SPECIAL)
    assert all(c == 1 for _, c in run_steps(m, (6, 4), 0, 4000, p_slip=0.0, red_active=False))
    on = run_steps(m, (6, 4), 0, 4000, p_slip=0.0, red_active=True)
    assert abs(np.mean([c == 5 for _, c in on]) - 0.5) < 0.03

def test_red_needs_special_colour():
    assert all(c == 1 for _, c in run_steps(open_map(colour=1), (6, 4), 0, 500, p_slip=0.0, red_active=True))

def test_double_step_only_if_next_free():
    out = run_steps(open_map(colour=C_SPECIAL), (2, 4), 0, 500, p_slip=0.0, red_active=True)
    assert all(r == ((1, 4), 1) for r in out)

def test_disp_class_matches_movement():
    m, rng = make_map(np.random.default_rng(4), 0.15), np.random.default_rng(5)
    pos = m.start
    for _ in range(2000):
        new, c = step(m, pos, int(rng.integers(4)), rng, p_slip=0.3, red_active=True)
        assert (new[0] - pos[0], new[1] - pos[1]) == DISP[c]
        pos = m.start if new == m.goal else new

def test_step_draws_exactly_three_numbers():
    r1, r2 = np.random.default_rng(8), np.random.default_rng(8)
    step(open_map(), (4, 4), 0, r1, p_slip=0.1, red_active=True)
    r2.random(); r2.integers(4); r2.random()
    assert r1.random() == r2.random()

def test_red_slide_onto_and_past_goal():        # Review Focus 3
    t = rollout(open_map(colour=C_SPECIAL, goal=(2, 4)), lambda o, p: 0, np.random.default_rng(0), 0.0, True, red_p=1.0)
    assert t.reached and len(t.actions) == 1 and t.disps[0] == 5
    m2 = open_map(colour=C_SPECIAL, goal=(3, 4))
    assert step(m2, (4, 4), 0, np.random.default_rng(0), 0.0, True, red_p=1.0) == ((2, 4), 5)

def test_rollout_caps_at_max_steps():
    t = rollout(open_map(start=(1, 4), goal=(7, 7)), lambda o, p: 0, np.random.default_rng(0), 0.0, False)
    assert len(t.actions) == 40 and not t.reached

def test_rollout_records_pre_step_obs():
    m = make_map(np.random.default_rng(6), 0.15)
    t = rollout(m, lambda o, p: 1, np.random.default_rng(0), 0.1, False)
    assert (t.obs[0] == observe(m, m.start)).all() and tuple(t.positions[0]) == m.start
```

- [ ] **Step 2: Tests laufen lassen** · Run: `python -m pytest farbversuch/tests/test_world_step.py -q` · Expected: FAIL (ImportError `step`)
- [ ] **Step 3: `disp_class`, `step`, `Traj`, `rollout` implementieren** (Festlegungen 3 und 4)
- [ ] **Step 4: Tests bestehen** · Expected: 10 passed
- [ ] **Step 5: Commit** · `git commit -m "feat(welt): Schritt, Rutschen, Rot-Effekt, Rollout"`

---

### Task 3: Routine (Lehrer, Encoder, Policy, Training)

**Files:**
- Create: `farbversuch/routine.py`
- Test: `farbversuch/tests/test_routine.py`

**Interfaces:**
- Consumes: `DELTAS`, `OBS_DIM`, `bfs_distances` (Task 1, nur in Tests)
- Produces (`routine.py`):
```python
def teacher_action(dist: np.ndarray, pos: tuple[int, int]) -> int   # Nachbar mit kleinstem Abstand >= 0; Gleichstand -> kleinster Index
@dataclass
class Routine:
    E: np.ndarray            # (k, 298)
    W: np.ndarray            # (k+1, 4), letzte Zeile = Bias
    def encode(self, X: np.ndarray) -> np.ndarray     # tanh(X @ E.T), akzeptiert uint8; (n,298)->(n,k), (298,)->(k,)
    def act(self, obs: np.ndarray) -> int             # argmax([z, 1] @ W)
    def act_batch(self, X: np.ndarray) -> np.ndarray  # (n,)
def routine_loss_grad(E, W, X, A, wd: float) -> tuple[float, np.ndarray, np.ndarray]   # (Loss, gE, gW)
def train_routine(X: np.ndarray, A: np.ndarray, rng: np.random.Generator, k: int = 32, lr: float = 0.5,
                  epochs: int = 1000, wd: float = 1e-3, init_std: float = 0.01) -> Routine
```
Loss = mittlere Kreuzentropie + (wd/2)·‖E‖². `E ~ N(0, init_std)` aus `rng`, `W = 0`. Pro Epoche ein Full-Batch-Schritt `E -= lr*gE; W -= lr*gW`, gerechnet in float64.

- [ ] **Step 1: Failing tests schreiben**

```python
def test_teacher_tie_breaks_to_lowest_action():
    assert teacher_action(bfs_distances(open_map().walls, (2, 2)), (4, 4)) == 0     # oben und links gleich gut

def test_teacher_avoids_walls():
    walls = open_map().walls.copy(); walls[3, 4] = True
    assert teacher_action(bfs_distances(walls, (2, 4)), (4, 4)) == 2                # links und rechts gleich, links kleiner

def test_loss_grad_matches_finite_differences():
    rng = np.random.default_rng(0)
    X, A = (rng.random((20, OBS_DIM)) < 0.3).astype(float), rng.integers(4, size=20)
    E, W = rng.normal(0, 0.1, (5, OBS_DIM)), rng.normal(0, 0.1, (6, 4))
    _, gE, gW = routine_loss_grad(E, W, X, A, 1e-3)
    for M, G in ((E, gE), (W, gW)):
        for idx in [(0, 0), (1, 2), (2, 3)]:
            M[idx] += 1e-6; lp = routine_loss_grad(E, W, X, A, 1e-3)[0]
            M[idx] -= 2e-6; lm = routine_loss_grad(E, W, X, A, 1e-3)[0]
            M[idx] += 1e-6
            assert abs((lp - lm) / 2e-6 - G[idx]) < 1e-6

def test_training_learns_simple_rule():
    rng = np.random.default_rng(1); A = rng.integers(4, size=400)
    X = (rng.random((400, OBS_DIM)) < 0.2).astype(np.uint8); X[:, :4] = np.eye(4, dtype=np.uint8)[A]
    r = train_routine(X, A, np.random.default_rng(2), epochs=300)
    assert (r.act_batch(X) == A).mean() > 0.95

def test_training_deterministic_and_act_consistent():
    rng = np.random.default_rng(3); X, A = (rng.random((50, OBS_DIM)) < 0.2).astype(np.uint8), rng.integers(4, size=50)
    r1 = train_routine(X, A, np.random.default_rng(4), epochs=20)
    r2 = train_routine(X, A, np.random.default_rng(4), epochs=20)
    assert np.array_equal(r1.E, r2.E) and [r1.act(x) for x in X] == list(r1.act_batch(X))
```

- [ ] **Step 2: Tests laufen lassen** · Run: `python -m pytest farbversuch/tests/test_routine.py -q` · Expected: FAIL (ImportError)
- [ ] **Step 3: `routine.py` implementieren**
- [ ] **Step 4: Tests bestehen** · Expected: 5 passed
- [ ] **Step 5: Commit** · `git commit -m "feat(routine): Lehrer, Encoder und Policy, Training"`

---

### Task 4: Logistische Regression und Vorwärtsmodell

**Files:**
- Create: `farbversuch/forward.py`
- Test: `farbversuch/tests/test_forward.py`

**Interfaces:**
- Consumes: `N_ACTIONS`, `N_DISP` (Tasks 1–2)
- Produces (`forward.py`):
```python
def log_softmax(L: np.ndarray) -> np.ndarray
def logreg_obj(W: np.ndarray, X: np.ndarray, y: np.ndarray, l2: float) -> tuple[float, np.ndarray]   # (Ziel, Gradient)
def fit_logreg(X, y, n_classes: int, l2: float, W0: np.ndarray | None = None,
               tol: float = 1e-6, max_iter: int = 500) -> tuple[np.ndarray, int]   # (W (d,K), Iterationen)
def mean_loglik(X, y, W) -> float
def fwd_design(Z: np.ndarray, A: np.ndarray, extra: np.ndarray | None = None) -> np.ndarray   # [Z | onehot(A,4) | 1 | extra]
@dataclass
class ForwardModel:
    W: np.ndarray
    @classmethod
    def fit(cls, Z, A, D, l2: float = 1e-3, tol: float = 1e-6, max_iter: int = 500) -> "ForwardModel"
    def surprise(self, Z, A, D) -> np.ndarray          # -log p(D | Z, A), (n,)
def freq_surprise(train_counts: np.ndarray, D_eval: np.ndarray) -> float   # Mittel von -log((count+1)/(N+9))
```
L-BFGS: Gedächtnis 10, Startskalierung sᵀy/yᵀy, Armijo mit c1 = 1e-4 ab Schrittweite 1, halbierend höchstens 40-mal (sonst Abbruch). Ein Paar mit sᵀy ≤ 1e-12 wird verworfen. Das Abbruchkriterium wird **vor** dem ersten Schritt geprüft, damit eine bereits konvergierte warme Lösung unverändert zurückkommt. Gemessen: ~6 ms pro warm gestarteter Anpassung bei 1600 Zeilen.

- [ ] **Step 1: Failing tests schreiben**

```python
def synth(n=600, d=4, K=9, seed=0):
    rng = np.random.default_rng(seed)
    X = np.hstack([rng.normal(size=(n, d)), np.ones((n, 1))]); P = np.exp(log_softmax(X @ rng.normal(size=(d + 1, K))))
    return X, np.array([rng.choice(K, p=p) for p in P])

def test_logreg_grad_matches_finite_differences():
    X, y = synth(n=50); W = np.random.default_rng(1).normal(size=(5, 9)); _, g = logreg_obj(W, X, y, 1e-3)
    for idx in [(0, 0), (2, 5), (4, 8)]:
        Wp, Wm = W.copy(), W.copy(); Wp[idx] += 1e-6; Wm[idx] -= 1e-6
        assert abs((logreg_obj(Wp, X, y, 1e-3)[0] - logreg_obj(Wm, X, y, 1e-3)[0]) / 2e-6 - g[idx]) < 1e-6

def test_fit_converges():
    X, y = synth(); W, _ = fit_logreg(X, y, 9, 1e-3)
    assert np.abs(logreg_obj(W, X, y, 1e-3)[1]).max() < 1e-6

def test_warm_start_reaches_same_optimum():
    X, y = synth(); col = (np.random.default_rng(1).random(len(y)) < 0.3).astype(float)[:, None]
    Wb, _ = fit_logreg(X, y, 9, 1e-3); Xe = np.hstack([X, col])
    Wc, _ = fit_logreg(Xe, y, 9, 1e-3)
    Ww, _ = fit_logreg(Xe, y, 9, 1e-3, W0=np.vstack([Wb, np.zeros((1, 9))]))
    assert np.abs(Wc - Ww).max() < 1e-4 and abs(mean_loglik(Xe, y, Wc) - mean_loglik(Xe, y, Ww)) < 1e-7

def test_zero_column_returns_base_exactly():
    X, y = synth(); Wb, _ = fit_logreg(X, y, 9, 1e-3)
    We, it = fit_logreg(np.hstack([X, np.zeros((len(y), 1))]), y, 9, 1e-3, W0=np.vstack([Wb, np.zeros((1, 9))]))
    assert it == 0 and np.array_equal(We[:-1], Wb) and (We[-1] == 0).all()

def test_unseen_class_finite_surprise():        # Review Focus 1
    rng = np.random.default_rng(0); Z, A = rng.normal(size=(500, 3)), rng.integers(4, size=500)
    s = ForwardModel.fit(Z, A, 1 + A).surprise(Z[:4], A[:4], np.full(4, 8))
    assert np.isfinite(s).all() and (s > 3).all()

def test_surprise_is_neg_log_prob():
    rng = np.random.default_rng(0); Z, A = rng.normal(size=(300, 3)), rng.integers(4, size=300); D = rng.integers(9, size=300)
    fm = ForwardModel.fit(Z, A, D)
    assert np.allclose(fm.surprise(Z, A, D), -log_softmax(fwd_design(Z, A) @ fm.W)[np.arange(300), D])

def test_log_softmax_stable():
    assert np.allclose(log_softmax(np.array([[1000., 0.]])), [[0., -1000.]])

def test_fwd_design_layout():
    X = fwd_design(np.zeros((2, 3)), np.array([1, 3]), np.array([[1], [0]]))
    assert X.shape == (2, 9) and list(X[0, 3:]) == [0, 1, 0, 0, 1, 1]

def test_freq_surprise():
    assert np.isclose(freq_surprise(np.array([2, 1] + [0] * 7), np.array([0, 1])), -(np.log(3 / 12) + np.log(2 / 12)) / 2)
```

- [ ] **Step 2: Tests laufen lassen** · Run: `python -m pytest farbversuch/tests/test_forward.py -q` · Expected: FAIL (ImportError)
- [ ] **Step 3: `forward.py` implementieren**
- [ ] **Step 4: Tests bestehen** · Expected: 9 passed
- [ ] **Step 5: Commit** · `git commit -m "feat(vorwaerts): L-BFGS-Logreg und Vorwärtsmodell"`

---

### Task 5: Ringpuffer und Kandidaten

**Files:**
- Create: `farbversuch/monitor.py`
- Test: `farbversuch/tests/test_buffer_candidates.py`

**Interfaces:**
- Consumes: `OBS_DIM`, `DELTAS`, `CH_WALL`, `CH_GOAL`, `CH_COLOR`, `obs_index` (Task 1). **Kein** `C_SPECIAL`.
- Produces (`monitor.py`):
```python
class RingBuffer:
    def __init__(self, capacity: int)
    def add(self, obs: np.ndarray, action: int, disp: int, surprise: float) -> None
    def __len__(self) -> int
    def data(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]   # obs uint8, A int8, D int8, S float64; älteste zuerst
    @property
    def nbytes(self) -> int                       # capacity * (298 + 1 + 1 + 8)
CAND_B_NAMES = ("Farbe 0", "Farbe 1", "Farbe 2", "Farbe 3", "Wand", "Ziel")
def candidates_B(obs: np.ndarray, actions: np.ndarray) -> np.ndarray   # (n,6) uint8, Zielzelle der gewählten Aktion
def candidates_A(obs: np.ndarray, actions: np.ndarray) -> np.ndarray   # (n,1192) uint8, Spalte a*298+i = obs[:,i] UND Aktion==a
def candidate_name(arm: str, c: int) -> str                            # B: CAND_B_NAMES[c]; A: f"bit{c % 298}&a{c // 298}"
```

- [ ] **Step 1: Failing tests schreiben**

```python
def test_ring_keeps_last_entries_in_order():
    b = RingBuffer(5)
    for t in range(7):
        b.add(np.full(OBS_DIM, t % 2, np.uint8), t % 4, t, float(t))
    obs, A, D, S = b.data()
    assert len(b) == 5 and list(S) == [2., 3., 4., 5., 6.] and list(D) == [2, 3, 4, 5, 6] and list(A) == [2, 3, 0, 1, 2]
    assert (obs[0] == 0).all() and (obs[1] == 1).all()

def test_ring_partial_fill():
    b = RingBuffer(5); b.add(np.zeros(OBS_DIM, np.uint8), 0, 0, 0.); b.add(np.zeros(OBS_DIM, np.uint8), 1, 1, 1.)
    assert len(b) == 2 and list(b.data()[3]) == [0., 1.]

def test_ring_nbytes():
    assert RingBuffer(2000).nbytes == 2000 * 308

def test_candidates_B_reads_target_cell():
    o = np.zeros(OBS_DIM, np.uint8)
    o[obs_index(CH_COLOR[2], -1, 0)] = 1; o[obs_index(CH_WALL, 0, -1)] = 1
    o[obs_index(CH_GOAL, 1, 0)] = 1; o[obs_index(CH_COLOR[0], 1, 0)] = 1
    F = candidates_B(np.stack([o, o, o]), np.array([0, 2, 1]))
    assert F.tolist() == [[0, 0, 1, 0, 0, 0], [0, 0, 0, 0, 1, 0], [1, 0, 0, 0, 0, 1]]

def test_candidates_A_layout():
    rng = np.random.default_rng(0)
    obs, A = (rng.random((50, OBS_DIM)) < 0.3).astype(np.uint8), rng.integers(4, size=50)
    F = candidates_A(obs, A)
    assert F.shape == (50, 1192)
    for a in range(4):
        assert (F[:, a * 298:(a + 1) * 298] == obs * (A == a)[:, None]).all()
```

- [ ] **Step 2: Tests laufen lassen** · Expected: FAIL (ImportError)
- [ ] **Step 3: Puffer und Kandidaten implementieren**
- [ ] **Step 4: Tests bestehen** · Expected: 5 passed
- [ ] **Step 5: Commit** · `git commit -m "feat(monitor): Ringpuffer und Kandidaten A/B"`

---

### Task 6: Bemerken und Kalibrierung

**Files:**
- Modify: `farbversuch/monitor.py`
- Test: `farbversuch/tests/test_notice.py`

**Interfaces:**
- Produces (`monitor.py`):
```python
def null_threshold(null_maxima: Sequence[float], max_alarms: int = 1) -> float     # (max_alarms+1)-größter Wert
def m3_trace(episodes: Sequence[np.ndarray], window: int = 500, interval: int = 10) -> list[tuple[int, float]]
    # (E, Mittel der letzten `window` Überraschungen) an jedem Prüfpunkt mit >= window Schritten
def calibrate_m3(null_streams: Sequence[Sequence[np.ndarray]], window: int = 500, interval: int = 10,
                 max_alarms: int = 1) -> float      # Strom ohne Prüfpunkt zählt als -inf
def cusum_trace(s: np.ndarray, k: float) -> np.ndarray    # S_t = max(0, S_{t-1} + s_t - k), S_0 = 0
def calibrate_cusum(null_streams, sd_factor: float = 0.5, max_alarms: int = 1) -> tuple[float, float]
    # k = Mittel + sd_factor * Std (ddof=0) aller Null-Schritte gepoolt; h = null_threshold der Strom-Maxima
```

- [ ] **Step 1: Failing tests schreiben**

```python
def test_null_threshold_is_second_largest():
    v = [1., 5., 3., 4.]
    assert null_threshold(v) == 4. and sum(x > null_threshold(v) for x in v) == 1

def test_calibrations_allow_at_most_one_null_alarm():
    rng = np.random.default_rng(0)
    nulls = [[rng.exponential(1., rng.integers(5, 15)) for _ in range(300)] for _ in range(20)]
    t = calibrate_m3(nulls)
    assert sum(max(v for _, v in m3_trace(s)) > t for s in nulls) <= 1
    k, h = calibrate_cusum(nulls)
    assert sum(cusum_trace(np.concatenate(s), k).max() > h for s in nulls) <= 1

def test_m3_trace_needs_window_and_uses_last_steps():
    tr = m3_trace([np.full(10, float(i)) for i in range(60)], window=500, interval=10)
    assert tr[0][0] == 50 and np.isclose(tr[0][1], np.arange(50.).mean())
    assert tr[1][0] == 60 and np.isclose(tr[1][1], np.arange(10., 60.).mean())

def test_cusum_trace_values():
    assert cusum_trace(np.array([1., 3., 0., 2.]), 1.).tolist() == [0., 2., 1., 2.]

def test_calibrate_cusum_k():
    k, _ = calibrate_cusum([[np.array([1., 2.]), np.array([3.])], [np.array([4.])]])
    assert np.isclose(k, 2.5 + 0.5 * np.std([1., 2., 3., 4.]))
```

- [ ] **Step 2: Tests laufen lassen** · Expected: FAIL
- [ ] **Step 3: Implementieren**
- [ ] **Step 4: Tests bestehen** · Expected: 5 passed
- [ ] **Step 5: Commit** · `git commit -m "feat(monitor): Bemerken und Kalibrierung (M3, CUSUM)"`

---

### Task 7: Erklären per Modellvergleich (M3)

**Files:**
- Modify: `farbversuch/monitor.py`
- Test: `farbversuch/tests/test_explain_m3.py`

**Interfaces:**
- Consumes: `fit_logreg`, `mean_loglik`, `fwd_design` (Task 4), `N_DISP`
- Produces (`monitor.py`):
```python
@dataclass
class FitStats:
    n_fits: int = 0
    size: int = 0            # Summe (Parameterzahl × Trainingszeilen)
def cv_folds(n: int, rng: np.random.Generator, n_folds: int = 5) -> list[np.ndarray]   # Testindizes
def select_m3(imp: np.ndarray, candidates: Sequence[int]) -> int | None    # imp: (len(candidates), n_folds)
def m3_explain(Z, A, D, F, opened: Sequence[int], rng: np.random.Generator, l2: float = 1e-3, n_folds: int = 5,
               tol: float = 1e-6, max_iter: int = 500, stats: FitStats | None = None) -> int | None
```
Ablauf von `m3_explain`:
1. `folds = cv_folds(n, rng, n_folds)`; Basisdesign `Xb = fwd_design(Z, A, F[:, opened])`.
2. Pro Teilung: Basis kalt anpassen, `llb` = `mean_loglik` auf der Testteilung. Pro Kandidat `c ∉ opened`: Ist die Spalte auf Train konstant, gilt `imp[c, f] = 0` ohne Anpassung. Sonst `Xe = [Xb | F[:, c]]`, warm aus `[Wb; 0]` anpassen, `imp[c, f] = ll_ext − llb`.
3. `select_m3`: Kandidaten mit `imp > 0` in **allen** Teilungen. Davon gewinnt die größte mittlere Verbesserung, bei Gleichstand der kleinere Index. Sonst `None`.
4. `stats` zählt jede Anpassung (Basis und erweitert) und deren `d·K·len(train)`.

- [ ] **Step 1: Failing tests schreiben**

```python
def slide_data(n=1500, seed=0):
    rng = np.random.default_rng(seed); Z, A = rng.normal(size=(n, 3)), rng.integers(4, size=n)
    sig, noise = (rng.random((2, n)) < 0.25).astype(np.uint8)
    D = 1 + A; slide = (sig == 1) & (rng.random(n) < 0.5); D[slide] = 5 + A[slide]
    return Z, A, D, np.stack([sig, noise, np.zeros(n, np.uint8)], 1)

def test_select_m3_needs_all_folds_and_takes_largest_mean():
    assert select_m3(np.array([[.3, .3, .3, .3, -.01], [.05] * 5, [.06] * 5]), [0, 1, 2]) == 2
    assert select_m3(np.array([[.1] * 5, [.1] * 5]), [4, 7]) == 4
    assert select_m3(np.zeros((1, 5)), [0]) is None

def test_m3_opens_signal():
    Z, A, D, F = slide_data()
    assert m3_explain(Z, A, D, F, [], np.random.default_rng(1)) == 0

def test_m3_ignores_noise_once_signal_open():
    Z, A, D, F = slide_data()
    assert m3_explain(Z, A, D, F, [0], np.random.default_rng(1)) is None

def test_m3_skips_constant_column_without_fit():
    Z, A, D, F = slide_data(); st = FitStats()
    m3_explain(Z, A, D, F, [], np.random.default_rng(1), stats=st)
    assert st.n_fits == 5 * 3 and st.size > 0           # je Teilung: Basis, Signal, Rauschen

def test_m3_deterministic():
    Z, A, D, F = slide_data(); s1, s2 = FitStats(), FitStats()
    assert m3_explain(Z, A, D, F, [], np.random.default_rng(1), stats=s1) == m3_explain(Z, A, D, F, [], np.random.default_rng(1), stats=s2)
    assert s1 == s2

def test_cv_folds_partition():
    folds = cv_folds(103, np.random.default_rng(0))
    assert sorted(np.concatenate(folds).tolist()) == list(range(103)) and {len(f) for f in folds} == {20, 21}
```
(Vorab im Prototyp geprüft: Das Signal wird geöffnet, Rauschen bleibt bei 6 Seeds zu, genau 15 Anpassungen.)

- [ ] **Step 2: Tests laufen lassen** · Expected: FAIL
- [ ] **Step 3: Implementieren**
- [ ] **Step 4: Tests bestehen** · Expected: 6 passed
- [ ] **Step 5: Commit** · `git commit -m "feat(monitor): Erklären per Modellvergleich (M3)"`

---

### Task 8: Erklären per Permutationstest (S1)

**Files:**
- Modify: `farbversuch/monitor.py`
- Test: `farbversuch/tests/test_explain_s1.py`

**Interfaces:**
- Produces (`monitor.py`):
```python
def perm_pvalues(S: np.ndarray, F: np.ndarray, rng: np.random.Generator, n_perm: int = 1000) -> tuple[np.ndarray, np.ndarray]
    # (diff, p) je Spalte; diff = mean(S|F=1) - mean(S|F=0); konstante Spalte: diff 0, p 1
def holm_select(p: np.ndarray, diff: np.ndarray, alpha: float = 0.05) -> list[int]   # Ablehnungen in Testreihenfolge
def s1_explain(S, F, opened: Sequence[int], rng: np.random.Generator, n_perm: int = 1000,
               alpha: float = 0.05, max_open: int = 3) -> list[int]                  # neu geöffnete, höchstens max_open - len(opened)
```
Permutationen vektorisiert: `P = np.stack([rng.permutation(S) for _ in range(n_perm)], 1)`, Summen über `F.T @ P`. Holm: Sortierung nach p aufsteigend, dann diff absteigend, dann Index. Rang i (0-basiert) wird abgelehnt, wenn `p ≤ alpha / (m − i)`, Abbruch beim ersten Nein. m = Zahl der nicht geöffneten Kandidaten.

- [ ] **Step 1: Failing tests schreiben**

```python
def test_perm_pvalue_extremes():
    rng = np.random.default_rng(0); f = (rng.random(400) < 0.3).astype(np.uint8)
    S = 1. + 3. * f + rng.normal(0, 0.1, 400)
    diff, p = perm_pvalues(S, np.stack([f, np.ones(400, np.uint8)], 1), np.random.default_rng(1))
    assert p[0] == 1 / 1001 and diff[0] > 2.5 and p[1] == 1. and diff[1] == 0.

def test_holm_stepdown():
    assert holm_select(np.array([.001, .02, .012, .5]), np.zeros(4)) == [0, 2, 1]
    assert holm_select(np.array([.03, .03]), np.zeros(2)) == []
    assert holm_select(np.array([.001, .001]), np.array([1., 2.])) == [1, 0]

def test_s1_respects_cap_and_opened():
    rng = np.random.default_rng(0); F = (rng.random((400, 5)) < 0.3).astype(np.uint8)
    S = 1. + F[:, :4] @ np.array([3., 3., 5., 3.]) + rng.normal(0, 0.1, 400)
    assert s1_explain(S, F, [0, 1], np.random.default_rng(1)) == [2]

def test_s1_arm_a_cannot_reject():              # Folge der Spec: 0,05/1192 < 1/1001
    rng = np.random.default_rng(0); F = (rng.random((300, 1192)) < 0.3).astype(np.uint8)
    S = 1. + 3. * F[:, 5] + rng.normal(0, 0.1, 300)
    assert s1_explain(S, F, [], np.random.default_rng(1)) == []
```

- [ ] **Step 2: Tests laufen lassen** · Expected: FAIL
- [ ] **Step 3: Implementieren**
- [ ] **Step 4: Tests bestehen** · Expected: 4 passed
- [ ] **Step 5: Commit** · `git commit -m "feat(monitor): Erklären per Permutationstest mit Holm (S1)"`

---

### Task 9: Seeds und Monitor (vier Systeme, Takt, Kosten)

**Files:**
- Create: `farbversuch/seeds.py`
- Modify: `farbversuch/monitor.py`
- Test: `farbversuch/tests/test_monitor.py`

**Interfaces:**
- Consumes: alles aus Tasks 5–8; vom Vorwärtsmodell nur `.surprise(Z, A, D)`
- Produces (`seeds.py`):
```python
TEACHER, INIT, FORWARD, NULL, INVARIANCE, RECOLOR, PREMISE_FWD, PGLOBAL, DEPLOY, CV, PERM = range(1, 12)
def rng(*keys: int) -> np.random.Generator                      # np.random.default_rng(list(keys))
def episode_rngs(seed: int, tag: int, stream: int, episode: int) -> tuple[np.random.Generator, np.random.Generator]
    # (Karte, Dynamik) = rng(seed, tag, stream, episode, 0), rng(seed, tag, stream, episode, 1)
```
- Produces (`monitor.py`):
```python
SYSTEMS = ("M3-B", "M3-A", "S1-B", "S1-A")
class Monitor:
    def __init__(self, encode: Callable[[np.ndarray], np.ndarray], forward, *, m3_threshold: float,
                 cusum_k: float, cusum_h: float, seed: int, systems: Sequence[str] = SYSTEMS,
                 buffer_size: int = 2000, window: int = 500, interval: int = 10, n_folds: int = 5,
                 max_open: int = 3, n_perm: int = 1000, alpha: float = 0.05, l2: float = 1e-3,
                 tol: float = 1e-6, max_iter: int = 500)        # assert buffer_size >= window
    def add_step(self, obs: np.ndarray, action: int, disp: int) -> None
    def end_episode(self) -> None
    def results(self) -> dict[str, dict]
        # je System: {"noticed": int|None, "opened": [{"cand", "name", "episode"}], "buffer_bytes",
        #             "n_fits", "fit_size", "check_sec": [float], "total_sec"}
```
Verhalten:
- `add_step` berechnet die Überraschung mit `forward.surprise(encode(obs[None]), …)[0]` und legt sie in den Puffer. Für jedes S1-System ohne Alarm läuft CUSUM weiter; bei > h gilt `noticed = E + 1`.
- `end_episode` zählt E hoch. Nur bei `E % interval == 0` wird geprüft, die Systeme in `SYSTEMS`-Reihenfolge. Ein M3-System ohne Alarm bemerkt bei `len ≥ window` und Mittel der letzten `window` Überraschungen > Schwelle (`noticed = E`). Jedes bemerkte System mit weniger als `max_open` Merkmalen erklärt dann: M3 mit `m3_explain(…, rng(seed, CV, E))`, S1 mit `s1_explain(…, rng(seed, PERM, E))`. Z und Kandidatenmatrizen werden pro Prüfpunkt und Arm nur einmal berechnet. Die Wandzeit jeder Prüfung mit Arbeit kommt nach `check_sec`.
- `m3_explain` und `s1_explain` werden als Modul-Globale aufgerufen, damit Tests sie ersetzen können.

- [ ] **Step 1: Failing tests schreiben**

```python
import farbversuch.monitor as monitor

class FakeFwd:
    def __init__(self, s): self.s = s
    def surprise(self, Z, A, D): return np.full(len(A), self.s)

def make(s=1., **kw):
    args = dict(m3_threshold=.5, cusum_k=.5, cusum_h=2., seed=0, window=5, interval=10) | kw
    return Monitor(lambda X: X[..., :3].astype(float), FakeFwd(s), **args)

def feed(mon, n_eps, steps=1):
    for _ in range(n_eps):
        for _ in range(steps):
            mon.add_step(np.zeros(OBS_DIM, np.uint8), 0, 1)
        mon.end_episode()

@pytest.fixture
def quiet(monkeypatch):
    monkeypatch.setattr(monitor, "m3_explain", lambda *a, **k: None)
    monkeypatch.setattr(monitor, "s1_explain", lambda *a, **k: [])

def test_m3_checks_only_at_interval(quiet):
    m = make(); feed(m, 9); assert m.results()["M3-B"]["noticed"] is None
    feed(m, 1); assert m.results()["M3-B"]["noticed"] == 10

def test_m3_waits_for_window(quiet):
    m = make(window=25); feed(m, 20); assert m.results()["M3-B"]["noticed"] is None
    feed(m, 10); assert m.results()["M3-B"]["noticed"] == 30

def test_s1_notices_mid_episode(quiet):
    m = make(m3_threshold=99.); feed(m, 2, steps=2); assert m.results()["S1-B"]["noticed"] is None
    m.add_step(np.zeros(OBS_DIM, np.uint8), 0, 1); assert m.results()["S1-B"]["noticed"] == 3

def test_opened_stays_and_cap(monkeypatch):
    nxt = iter(range(100)); monkeypatch.setattr(monitor, "m3_explain", lambda *a, **k: next(nxt))
    m = make(systems=("M3-B",)); feed(m, 60); op = m.results()["M3-B"]["opened"]
    assert [o["cand"] for o in op] == [0, 1, 2] and [o["episode"] for o in op] == [10, 20, 30]

def test_s1_first_explain_at_next_checkpoint(monkeypatch):
    calls = []; monkeypatch.setattr(monitor, "s1_explain", lambda *a, **k: calls.append(1) or [])
    m = make(m3_threshold=99.); feed(m, 3, steps=2); assert calls == []
    feed(m, 7, steps=2); assert len(calls) == 2                  # S1-B und S1-A an E = 10

def test_results_report_costs(quiet):
    r = make().results()["M3-A"]
    assert r["buffer_bytes"] == 2000 * 308 and {"n_fits", "fit_size", "check_sec", "total_sec"} <= set(r)
```

- [ ] **Step 2: Tests laufen lassen** · Expected: FAIL
- [ ] **Step 3: `seeds.py` und `Monitor` implementieren**
- [ ] **Step 4: Tests bestehen** · Expected: 6 passed
- [ ] **Step 5: Commit** · `git commit -m "feat(monitor): vier Systeme mit Prüftakt und Kosten"`

---

### Task 10: Konfiguration, Phase 1 und Prämissen

**Files:**
- Create: `farbversuch/config.py`, `farbversuch/run.py`, `farbversuch/tests/conftest.py`
- Modify: `farbversuch/tests/helpers.py` (Konstante `TINY`)
- Test: `farbversuch/tests/test_run_phase1.py`

**Interfaces:**
- Consumes: Tasks 1–9
- Produces (`config.py`):
```python
@dataclass(frozen=True)
class Config:
    wall_p: float = 0.15; wall_p_dense: float = 0.30; p_slip: float = 0.10; red_p: float = 0.5
    min_dist: int = 5; max_steps: int = 40
    n_teacher_episodes: int = 4000; k: int = 32; lr: float = 0.5; epochs: int = 1000; wd: float = 1e-3; init_std: float = 0.01
    n_forward_episodes: int = 1000; fwd_l2: float = 1e-3; logreg_tol: float = 1e-6; logreg_max_iter: int = 500
    n_null_streams: int = 20; n_null_episodes: int = 300; max_null_alarms: int = 1; cusum_sd_factor: float = 0.5
    n_invariance_maps: int = 500; min_invariance: float = 0.95; n_premise_fwd_episodes: int = 300
    n_pglobal_episodes: int = 300; pglobal_tol: float = 0.02; pglobal_max_iter: int = 30
    n_deploy_episodes: int = 400; switch_episode: int = 100; buffer_size: int = 2000
    notice_window: int = 500; check_interval: int = 10
    n_folds: int = 5; max_open: int = 3; n_perm: int = 1000; alpha: float = 0.05
    systems: tuple[str, ...] = ("M3-B", "M3-A", "S1-B", "S1-A")
    def to_json(self, path) -> None
    @classmethod
    def from_json(cls, path) -> "Config"     # Liste -> Tupel; unbekannter Schlüssel -> ValueError
    def as_dict(self) -> dict                # JSON-fähig (Tupel als Liste)
```
- Produces (`run.py`):
```python
CONDITIONS = ("none", "red", "global", "walls")
def env_params(cfg: Config, condition: str, episode: int, p_global: float) -> tuple[float, float, bool]   # (wall_p, p_slip, red_active)
def routine_rollouts(routine: Routine, seed: int, tag: int, n_episodes: int, cfg: Config, *, p_slip: float,
                     red_active: bool = False, stream: int = 0) -> list[tuple[Map, Traj]]
def teacher_data(seed: int, cfg: Config) -> tuple[np.ndarray, np.ndarray]    # (X uint8, A)
@dataclass
class Phase1:
    routine: Routine; forward: ForwardModel; class_counts: np.ndarray   # (9,) Klassen der Vorwärts-Trainingsdaten
    m3_threshold: float; cusum_k: float; cusum_h: float; sec: float
def phase1(seed: int, cfg: Config) -> Phase1
def premise_checks(seed: int, cfg: Config, p1: Phase1) -> dict   # {"ok", "color_invariance", "fwd_surprise", "freq_surprise"}
```
Schlüssel: Lehrer `episode_rngs(seed, TEACHER, 0, e)`, Init `rng(seed, INIT)`, Vorwärtsdaten `FORWARD`, Null-Strom j `episode_rngs(seed, NULL, j, e)`, Invarianz `INVARIANCE` mit `recolor(m, rng(seed, RECOLOR, e))`, Vorwärts-Prämisse `PREMISE_FWD`. Überall gilt `wall_p = cfg.wall_p`, `p_slip = cfg.p_slip`, kein Rot. Die Routine handelt über `lambda o, pos: routine.act(o)`.
- Produces (`helpers.py`):
```python
TINY = Config(n_teacher_episodes=300, epochs=200, n_forward_episodes=150, n_null_streams=5, n_null_episodes=40,
              n_invariance_maps=20, min_invariance=0.0, n_premise_fwd_episodes=30, n_pglobal_episodes=30,
              pglobal_max_iter=8, n_deploy_episodes=60, switch_episode=20, buffer_size=400, notice_window=100,
              n_perm=200, systems=("M3-B", "S1-B", "S1-A"))
```
- Produces (`conftest.py`): Session-Fixture `tiny_phase1 = phase1(0, TINY)`.

- [ ] **Step 1: Failing tests schreiben**

```python
def test_config_defaults_match_spec():
    c = Config()
    assert (c.wall_p, c.wall_p_dense, c.p_slip, c.red_p, c.min_dist, c.max_steps) == (0.15, 0.30, 0.10, 0.5, 5, 40)
    assert (c.n_teacher_episodes, c.k, c.lr, c.epochs, c.wd, c.init_std) == (4000, 32, 0.5, 1000, 1e-3, 0.01)
    assert (c.n_forward_episodes, c.n_null_streams, c.n_null_episodes, c.max_null_alarms) == (1000, 20, 300, 1)
    assert (c.n_invariance_maps, c.min_invariance, c.n_pglobal_episodes, c.pglobal_tol) == (500, 0.95, 300, 0.02)
    assert (c.n_deploy_episodes, c.switch_episode, c.buffer_size, c.notice_window, c.check_interval) == (400, 100, 2000, 500, 10)
    assert (c.n_folds, c.max_open, c.n_perm, c.alpha, c.cusum_sd_factor) == (5, 3, 1000, 0.05, 0.5)

def test_config_json_roundtrip(tmp_path):
    c = Config(epochs=7, systems=("M3-B",)); c.to_json(tmp_path / "c.json")
    assert Config.from_json(tmp_path / "c.json") == c

def test_env_params_schedule():
    c = Config()
    assert env_params(c, "red", 99, .4) == (.15, .10, False) and env_params(c, "red", 100, .4) == (.15, .10, True)
    assert env_params(c, "global", 99, .4) == (.15, .10, False) and env_params(c, "global", 100, .4) == (.15, .4, False)
    assert env_params(c, "walls", 100, .4) == (.30, .10, False) and env_params(c, "none", 300, .4) == (.15, .10, False)

@pytest.mark.slow
def test_phase1_tiny(tiny_phase1):
    p = tiny_phase1
    assert p.routine.E.shape == (32, OBS_DIM) and np.isfinite([p.m3_threshold, p.cusum_k, p.cusum_h]).all()
    assert p.class_counts.sum() > 0 and p.class_counts[5:].sum() == 0      # beim Üben keine Doppelschritte

@pytest.mark.slow
def test_premise_checks_tiny(tiny_phase1):
    r = premise_checks(0, TINY, tiny_phase1)
    assert 0. <= r["color_invariance"] <= 1.
    assert r["ok"] == (r["color_invariance"] >= TINY.min_invariance and r["fwd_surprise"] < r["freq_surprise"])
```

- [ ] **Step 2: Tests laufen lassen** · Run: `python -m pytest farbversuch/tests/test_run_phase1.py -q` · Expected: FAIL
- [ ] **Step 3: `config.py`, `run.py` (Teil 1), `TINY`, `conftest.py` implementieren**
- [ ] **Step 4: Tests bestehen** · Expected: 5 passed (die slow-Tests dauern einige Sekunden)
- [ ] **Step 5: Commit** · `git commit -m "feat(run): Konfiguration, Phase 1 und Prämissen"`

---

### Task 11: p_global, Einsatz, run_seed, Kommandozeile

**Files:**
- Modify: `farbversuch/run.py`
- Test: `farbversuch/tests/test_run_deploy.py`

**Interfaces:**
- Consumes: Task 10, `Monitor` (Task 9)
- Produces (`run.py`):
```python
def bisect_to_target(f: Callable[[float], float], target: float, lo: float, hi: float,
                     rel_tol: float, max_iter: int) -> tuple[float, bool, int]   # (p, getroffen, Auswertungen von f)
def find_p_global(seed: int, cfg: Config, p1: Phase1) -> dict   # {"p_global", "red_surprise", "bracketed", "evals"}
def stream_episodes(seed: int, cfg: Config, p1: Phase1, p_global: float, condition: str) -> Iterator[Traj]
def deploy(seed: int, cfg: Config, p1: Phase1, p_global: float, condition: str) -> dict   # Monitor.results()
def run_seed(seed: int, cfg: Config) -> dict
def parse_seeds(s: str) -> list[int]        # "400-409", "0", "1,5"
def main(argv: list[str] | None = None) -> None
```
- `bisect_to_target` setzt ein steigendes f voraus. Gilt `f(hi) < target·(1−rel_tol)`, kommt `(hi, False, …)` zurück; gilt `f(lo) > target·(1+rel_tol)`, kommt `(lo, False, …)`. Sonst wird halbiert, bis `|f(p) − target| ≤ rel_tol·target` (dann `True`) oder `max_iter` erreicht ist.
- `find_p_global`: Karten und Würfe `episode_rngs(seed, PGLOBAL, 0, e)`. Ziel ist die gepoolte mittlere Überraschung pro Schritt mit Rot aktiv und `cfg.p_slip`. Gesucht wird p auf [`cfg.p_slip`, 1,0] ohne Rot.
- `stream_episodes`: Pro Episode e gelten `env_params(cfg, condition, e, p_global)`, Karte und Würfe aus `episode_rngs(seed, DEPLOY, 0, e)`. `deploy` füttert jede Episode Schritt für Schritt in einen `Monitor(p1.routine.encode, p1.forward, seed=seed, …)` und ruft danach `end_episode()`.
- Abbildung Config → Monitor bzw. Phase 1, wo die Namen abweichen: `window ← notice_window`, `interval ← check_interval`, `l2 ← fwd_l2`, `tol ← logreg_tol`, `max_iter ← logreg_max_iter`, `systems ← systems`. Dieselben Werte nutzen `calibrate_m3` (dazu `max_alarms ← max_null_alarms`), `calibrate_cusum` (`sd_factor ← cusum_sd_factor`) und `ForwardModel.fit`. Alle übrigen Parameter heißen gleich.
- Ergebnis-JSON (nur Python-Typen):
```json
{"seed": 400, "config": {"...": "Config.as_dict()"},
 "premise": {"ok": true, "color_invariance": 0.97, "fwd_surprise": 0.41, "freq_surprise": 0.72},
 "calibration": {"m3_threshold": 0.0, "cusum_k": 0.0, "cusum_h": 0.0},
 "p_global": {"p_global": 0.37, "red_surprise": 0.0, "bracketed": true, "evals": 6},
 "conditions": {"none": {"M3-B": {"noticed": null, "opened": [], "...": "..."}}},
 "phase1_sec": 0.0, "total_sec": 0.0}
```
Ist die Prämisse nicht erfüllt, sind `"p_global"` und `"conditions"` `null`, und der Seed endet dort.
- CLI: `python -m farbversuch.run --seeds 400-409 --out DIR [--config FILE] [--jobs N]` schreibt `DIR/seed_<n>.json`. Vorhandene Dateien werden übersprungen, so lässt sich ein abgebrochener Lauf fortsetzen. Bei `--jobs > 1` werden vor dem Start `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` und `MKL_NUM_THREADS` auf `1` gesetzt, dann läuft ein `multiprocessing.get_context("spawn").Pool`.

- [ ] **Step 1: Failing tests schreiben**

```python
def test_bisect_hits_target():
    p, ok, _ = bisect_to_target(lambda p: p * p, .25, .1, 1., .02, 30)
    assert ok and abs(p * p - .25) <= .005

def test_bisect_unbracketed():                   # Review Focus 5
    p, ok, n = bisect_to_target(lambda p: p, 5., .1, 1., .02, 30)
    assert (p, ok) == (1., False) and n <= 2

def test_parse_seeds():
    assert parse_seeds("400-402") == [400, 401, 402] and parse_seeds("0") == [0] and parse_seeds("1,5") == [1, 5]

@pytest.mark.slow
def test_streams_share_maps_before_switch(tiny_phase1):
    s = {c: list(stream_episodes(0, TINY, tiny_phase1, .4, c)) for c in ("none", "red")}
    sw = TINY.switch_episode
    assert all(np.array_equal(a.positions, b.positions) for a, b in zip(s["none"][:sw], s["red"][:sw]))
    assert any((t.disps >= 5).any() for t in s["red"][sw:]) and not any((t.disps >= 5).any() for t in s["none"])

@pytest.mark.slow
def test_run_seed_schema():
    r = run_seed(0, TINY)
    assert set(r["conditions"]) == set(CONDITIONS) and set(r["conditions"]["red"]) == set(TINY.systems)
    assert json.loads(json.dumps(r)) == r

@pytest.mark.slow
def test_premise_failure_stops_seed():
    r = run_seed(0, dataclasses.replace(TINY, min_invariance=1.01))
    assert r["premise"]["ok"] is False and r["conditions"] is None and r["p_global"] is None

@pytest.mark.slow
def test_cli_writes_and_skips(tmp_path):
    cfg = tmp_path / "c.json"; TINY.to_json(cfg)
    args = ["--config", str(cfg), "--seeds", "0", "--out", str(tmp_path / "o")]
    main(args); f = tmp_path / "o" / "seed_0.json"; t = f.stat().st_mtime_ns
    main(args); assert f.stat().st_mtime_ns == t
```

- [ ] **Step 2: Tests laufen lassen** · Expected: FAIL
- [ ] **Step 3: Implementieren**
- [ ] **Step 4: Tests bestehen** · Expected: 7 passed
- [ ] **Step 5: Commit** · `git commit -m "feat(run): p_global, Einsatz, run_seed und CLI"`

---

### Task 12: Querschnittstests – Isolation, Leck, Determinismus

**Files:**
- Test: `farbversuch/tests/test_isolation.py`, `farbversuch/tests/test_leak.py`, `farbversuch/tests/test_determinism.py`

**Interfaces:**
- Consumes: `Routine.act`, `Monitor.add_step`, `m3_explain`, `s1_explain`, `candidates_B`, `run_seed`, `episode_rngs`, `make_map`, `rollout`, `C_SPECIAL` (nur im Test, als Index des Kandidaten „Farbe 0“)

- [ ] **Step 1: Tests schreiben**

```python
# test_isolation.py
FORBIDDEN = {"C_SPECIAL", "condition", "switch_episode", "red_active", "p_global", "env_params", "Config", "CONDITIONS"}
ALLOWED_WORLD = {"DELTAS", "N_ACTIONS", "OBS_DIM", "CH_WALL", "CH_GOAL", "CH_COLOR", "N_DISP", "obs_index"}

@pytest.mark.parametrize("mod", ["routine", "forward", "monitor"])
def test_no_access_to_condition_switch_or_special(mod):
    tree = ast.parse((Path(__file__).parents[1] / f"{mod}.py").read_text())
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name): names.add(n.id)
        if isinstance(n, ast.Attribute): names.add(n.attr)
        if isinstance(n, ast.arg): names.add(n.arg)
        if isinstance(n, (ast.Import, ast.ImportFrom)): names |= {a.name for a in n.names}
        if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("farbversuch"):
            assert n.module in ("farbversuch.world", "farbversuch.forward", "farbversuch.seeds")
            if n.module == "farbversuch.world":
                assert {a.name for a in n.names} <= ALLOWED_WORLD
        if isinstance(n, ast.Import):
            assert not any(a.name.startswith("farbversuch") for a in n.names)
    assert not names & FORBIDDEN

def test_agent_and_monitor_see_only_experience():
    assert list(inspect.signature(Routine.act).parameters) == ["self", "obs"]
    assert list(inspect.signature(Monitor.add_step).parameters) == ["self", "obs", "action", "disp"]

# test_leak.py
SPECIAL = C_SPECIAL                       # Kandidatenindex „Farbe 0“ im Arm B

def greedy_m3(Z, A, D, F):
    opened = []
    for _ in range(3):
        c = m3_explain(Z, A, D, F, opened, np.random.default_rng(1))
        if c is None: break
        opened.append(c)
    return opened

@pytest.fixture(scope="module")
def red_buffer(tiny_phase1):
    p1, parts = tiny_phase1, []
    for e in range(1000):
        mrng, drng = episode_rngs(99, 0, 0, e)                      # eigene Schlüssel, Rot von Anfang an
        parts.append(rollout(make_map(mrng, .15), lambda o, pos: p1.routine.act(o), drng, .10, True))
        if sum(len(t.actions) for t in parts) >= 2000: break
    obs, A, D = (np.concatenate([getattr(t, k) for t in parts])[-2000:] for k in ("obs", "actions", "disps"))
    Z = p1.routine.encode(obs)
    return Z, A, D, p1.forward.surprise(Z, A, D), candidates_B(obs, A)

@pytest.mark.slow
def test_positive_control(red_buffer):
    Z, A, D, S, F = red_buffer
    assert SPECIAL in greedy_m3(Z, A, D, F) and SPECIAL in s1_explain(S, F, [], np.random.default_rng(2))

@pytest.mark.slow
def test_shuffled_candidate_never_opened(red_buffer):
    Z, A, D, S, F = red_buffer
    for k in range(5):
        Fs = F.copy(); Fs[:, SPECIAL] = F[np.random.default_rng(10 + k).permutation(len(F)), SPECIAL]
        assert SPECIAL not in greedy_m3(Z, A, D, Fs)
        assert SPECIAL not in s1_explain(S, Fs, [], np.random.default_rng(2))

# test_determinism.py
def strip_sec(x):
    if isinstance(x, dict): return {k: strip_sec(v) for k, v in x.items() if not k.endswith("_sec")}
    if isinstance(x, list): return [strip_sec(v) for v in x]
    return x

@pytest.mark.slow
def test_same_seed_same_result():
    assert strip_sec(run_seed(0, TINY)) == strip_sec(run_seed(0, TINY))
```

- [ ] **Step 2: Tests laufen lassen** · Run: `python -m pytest farbversuch/tests/test_isolation.py farbversuch/tests/test_leak.py farbversuch/tests/test_determinism.py -q` · Expected: 6 passed. Schlägt ein Test fehl, ist das ein Fehler im Systemcode aus den Tasks 3–11. Dort reparieren, den Test nicht abschwächen.
- [ ] **Step 3: Gesamte Suite** · Run: `python -m pytest -q` · Expected: alle bestanden
- [ ] **Step 4: Commit** · `git commit -m "test: Isolation, Lecktest Zuschreibung, Determinismus"`

---

### Task 13: Auswertung (Kennzahlen, P1–P5, Abbruchkriterium)

**Files:**
- Create: `farbversuch/analyze.py`
- Test: `farbversuch/tests/test_analyze.py`

**Interfaces:**
- Consumes: Ergebnis-JSON (Task 11), `SYSTEMS`, `CONDITIONS`, `C_SPECIAL`, `CH_COLOR`, `DELTAS`, `obs_index`
- Produces (`analyze.py`):
```python
def is_correct(arm: str, cand: int) -> bool   # B: cand == C_SPECIAL; A: cand % 298 == obs_index(CH_COLOR[C_SPECIAL], *DELTAS[cand // 298])
def is_colour(arm: str, cand: int) -> bool    # B: cand < 4; A: Bit liegt in einem Farbkanal
def stream_metrics(res: dict, condition: str, arm: str, switch: int, horizon: int) -> dict
    # {"false_alarm", "notice_latency", "correct", "attr_latency", "misattr", "n_opened"}
def evaluate(results: Sequence[dict], seeds: Sequence[int]) -> dict
    # {"P1": {"ok_seeds", "failed_seeds"}, "P2": {"count", "fulfilled"}, "P3": {"count", "fulfilled"},
    #  "P4": {"latency_A", "latency_B", "misattr_A", "misattr_B", "fulfilled"}, "P5": {"M3-B", "S1-B", "fulfilled"},
    #  "abort": {"red_correct", "global_open", "triggered"}, "systems": {Name: {Bedingung: Kennzahlen + Kosten}}}
def report_markdown(ev: dict) -> str
def main(argv: list[str] | None = None) -> None   # python -m farbversuch.analyze --results DIR --seeds 400-409
```
Regeln:
- `notice_latency`: nicht bemerkt ergibt `horizon`. Bemerken bei E ≤ switch ist ein Fehlalarm mit Latenz `None`. In `none` ist jedes Bemerken ein Fehlalarm.
- `correct` und `attr_latency` gelten nur für `red`: erste richtige Öffnung bei E, Latenz max(0, E − switch), sonst `horizon`.
- `misattr`: in `red` die Öffnungen, die nicht richtig sind. Sonst die Öffnungen von Farbmerkmalen.
- `horizon = n_deploy_episodes − switch_episode` und `switch` kommen aus `result["config"]`.
- Seeds ohne erfüllte Prämisse: Festlegung 16. P2: ≥ 9; P3: ≥ 9 Seeds ohne Öffnung; P5: M3-B ≥ S1-B. Abbruch: richtige Zuschreibung < 5 oder Öffnung bei `global` > 3.
- Kosten je System: Summe `n_fits` und `fit_size`, Mittel und Maximum von `check_sec`, Summe `total_sec`, `buffer_bytes`.

- [ ] **Step 1: Failing tests schreiben**

```python
def sysres(noticed=None, opened=()):
    return {"noticed": noticed, "opened": [{"cand": c, "name": "", "episode": e} for c, e in opened],
            "buffer_bytes": 0, "n_fits": 0, "fit_size": 0, "check_sec": [], "total_sec": 0.}

def fake_result(seed, red_ok=True, global_open=False, ok=True):
    conds = {c: {s: sysres() for s in SYSTEMS} for c in CONDITIONS}
    conds["red"]["M3-B"] = sysres(110, [(C_SPECIAL, 120)] if red_ok else [])
    conds["global"]["M3-B"] = sysres(110, [(4, 120)] if global_open else [])
    return {"seed": seed, "config": {"switch_episode": 100, "n_deploy_episodes": 400},
            "premise": {"ok": ok}, "conditions": conds if ok else None}

A_RED = 0 * 298 + obs_index(CH_COLOR[C_SPECIAL], -1, 0)       # Farbe 0 oben, Aktion oben

def test_is_correct():
    assert is_correct("B", C_SPECIAL) and not is_correct("B", 4)
    assert is_correct("A", A_RED) and not is_correct("A", 1 * 298 + obs_index(CH_COLOR[C_SPECIAL], -1, 0))

def test_latency_and_censoring():
    m = stream_metrics(sysres(130, [(C_SPECIAL, 140)]), "red", "B", 100, 300)
    assert (m["notice_latency"], m["correct"], m["attr_latency"], m["false_alarm"]) == (30, True, 40, False)
    assert stream_metrics(sysres(), "red", "B", 100, 300)["notice_latency"] == 300
    assert stream_metrics(sysres(250), "none", "B", 100, 300)["false_alarm"]

def test_prechange_alarm_in_red():               # Review Focus 4
    m = stream_metrics(sysres(90, [(C_SPECIAL, 120)]), "red", "B", 100, 300)
    assert m["false_alarm"] and m["notice_latency"] is None and m["correct"] and m["attr_latency"] == 20

def test_misattribution_rules():
    assert stream_metrics(sysres(110, [(2, 120), (4, 130)]), "global", "B", 100, 300)["misattr"] == 1
    assert stream_metrics(sysres(110, [(4, 120), (C_SPECIAL, 130)]), "red", "B", 100, 300)["misattr"] == 1

def test_predictions_and_abort():
    seeds = list(range(400, 410))
    ev = evaluate([fake_result(s, red_ok=s != 400, global_open=s == 401) for s in seeds], seeds)
    assert ev["P2"] == {"count": 9, "fulfilled": True} and ev["P3"]["fulfilled"] and not ev["abort"]["triggered"]
    ev = evaluate([fake_result(s, red_ok=s < 404) for s in seeds], seeds)
    assert not ev["P2"]["fulfilled"] and ev["abort"]["triggered"]
    ev = evaluate([fake_result(s, global_open=s < 404) for s in seeds], seeds)
    assert not ev["P3"]["fulfilled"] and ev["abort"]["triggered"]

def test_failed_premise_counts_against_m3b():
    seeds = list(range(400, 410))
    ev = evaluate([fake_result(s, ok=s != 409) for s in seeds], seeds)
    assert ev["P1"]["failed_seeds"] == [409] and ev["P2"]["count"] == 9 and ev["abort"]["global_open"] == 1
```

- [ ] **Step 2: Tests laufen lassen** · Expected: FAIL
- [ ] **Step 3: Implementieren**
- [ ] **Step 4: Tests bestehen** · Expected: 6 passed
- [ ] **Step 5: Commit** · `git commit -m "feat(analyse): Kennzahlen, P1–P5 und Abbruchkriterium"`

---

### Task 14: Einfrieren

**Files:**
- Create: `farbversuch/freeze.py`
- Test: `farbversuch/tests/test_freeze.py`

**Interfaces:**
- Consumes: `Config` (Task 10)
- Produces (`freeze.py`):
```python
def source_files(root: Path) -> list[Path]          # requirements.txt, pytest.ini, farbversuch/**/*.py; sortiert, relativ zu root
def write_freeze(root: Path, cfg: Config) -> None   # farbversuch/frozen_config.json, dann farbversuch/freeze.sha256
                                                    # im sha256sum-Format, Quelldateien + frozen_config.json
def verify_freeze(root: Path) -> list[str]          # abweichende oder fehlende Pfade; [] = in Ordnung
def main(argv: list[str] | None = None) -> None     # write [--config FILE] | verify (Exitcode 1 bei Abweichung, sonst "OK")
```

- [ ] **Step 1: Failing tests schreiben**

```python
def tree(tmp_path):
    (tmp_path / "farbversuch" / "tests").mkdir(parents=True)
    for p in ("farbversuch/a.py", "farbversuch/tests/t.py", "requirements.txt", "pytest.ini"):
        (tmp_path / p).write_text(p)
    return tmp_path

def test_write_then_verify_clean(tmp_path):
    root = tree(tmp_path); write_freeze(root, Config(epochs=3))
    assert verify_freeze(root) == [] and Config.from_json(root / "farbversuch" / "frozen_config.json") == Config(epochs=3)

def test_verify_reports_change(tmp_path):
    root = tree(tmp_path); write_freeze(root, Config()); (root / "farbversuch" / "a.py").write_text("x")
    assert verify_freeze(root) == ["farbversuch/a.py"]

def test_sha256sum_format(tmp_path):
    root = tree(tmp_path); write_freeze(root, Config())
    lines = (root / "farbversuch" / "freeze.sha256").read_text().splitlines()
    assert len(lines) == 5 and all(re.fullmatch(r"[0-9a-f]{64}  \S+", l) for l in lines)
```

- [ ] **Step 2: Tests laufen lassen** · Expected: FAIL
- [ ] **Step 3: Implementieren**
- [ ] **Step 4: Tests bestehen** · Expected: 3 passed
- [ ] **Step 5: Commit** · `git commit -m "feat(freeze): Konfiguration und Prüfsummen einfrieren"`

---

### Task 15: Pilot (Seed 0)

**Files:**
- Create: `farbversuch/PROTOKOLL.md`, ggf. `farbversuch/pilot_config.json`, `farbversuch/results/pilot/seed_0.json`

- [ ] **Step 1: Gesamte Suite grün** · Run: `python -m pytest -q` · Expected: alle bestanden
- [ ] **Step 2: Pilot im Hintergrund starten** · Run: `python -m farbversuch.run --seeds 0 --out farbversuch/results/pilot` · Expected: `seed_0.json`. Wandzeit notieren.
- [ ] **Step 3: Pilot prüfen.** Zu prüfen: `premise` (Farbinvarianz ≥ 0,95, Vorwärtsmodell besser als Häufigkeiten), `p_global.bracketed`, `check_sec` von M3-A (Mittel, Maximum), `total_sec`.
- [ ] **Step 4: Nur wenn nötig anpassen.** Erlaubt sind nur Trainings-Hyperparameter der Routine (`lr`, `epochs`, `wd`, `init_std`, `n_teacher_episodes`, `k`), des Vorwärtsmodells (`fwd_l2`, `n_forward_episodes`, `logreg_tol`, `logreg_max_iter`), `buffer_size` und `check_interval`. Änderungen gehen in `farbversuch/pilot_config.json`. Danach die alte Pilotausgabe löschen und mit `--config farbversuch/pilot_config.json` neu laufen lassen. Ein Grund ist nur Fehlersuche oder P1 (Spec §8), nie ein Ergebnis zu P2–P5. Ein Code-Fehler wird testgetrieben repariert (erst ein fehlschlagender Test) und ebenfalls protokolliert. Jeder Eintrag in `PROTOKOLL.md`:
```markdown
## 2026-10-0X – <Parameter>: <alt> → <neu>
Grund: <Fehlersuche | P1 Farbinvarianz | P1 Vorwärtsmodell>
Beobachtung vorher: <Zahl> · nachher: <Zahl>
```
Ist Laufzeit allein das Problem (M3-A zu langsam), kommt der Vorschlag zuerst zum Nutzer, nicht direkt ins Protokoll: Die Spec nennt Laufzeit nicht als Pilotgrund.
- [ ] **Step 5: Commit** · `git add farbversuch/PROTOKOLL.md farbversuch/results/pilot farbversuch/pilot_config.json` (falls vorhanden) · `git commit -m "pilot: Seed 0 und Protokoll"`

---

### Task 16: Einfrieren und Hauptlauf (Seeds 400–409)

**Files:**
- Create: `farbversuch/frozen_config.json`, `farbversuch/freeze.sha256`, `farbversuch/results/main/seed_400.json` … `seed_409.json`

- [ ] **Step 1: Einfrieren** · Run: `python -m farbversuch.freeze write --config farbversuch/pilot_config.json` (ohne Pilotänderung ohne `--config`), dann `python -m farbversuch.freeze verify` · Expected: `OK`
- [ ] **Step 2: Commit vor dem Hauptlauf** · `git add farbversuch/frozen_config.json farbversuch/freeze.sha256 && git commit -m "freeze: Konfiguration und Prüfsummen vor dem Hauptlauf"` und pushen
- [ ] **Step 3: Hauptlauf im Hintergrund** · Run: `python -m farbversuch.run --config farbversuch/frozen_config.json --seeds 400-409 --jobs 4 --out farbversuch/results/main` · Expected: 10 Dateien. Nach Abbruch denselben Befehl wiederholen; fertige Seeds werden übersprungen. Zwischen Step 1 und Step 4 wird kein Code geändert. Bricht der Lauf mit einem Fehler ab: anhalten und den Nutzer fragen, nicht still flicken.
- [ ] **Step 4: Prüfsummen bestätigen** · Run: `python -m farbversuch.freeze verify` · Expected: `OK`
- [ ] **Step 5: Commit** · `git add farbversuch/results/main && git commit -m "hauptlauf: Seeds 400–409"`

---

### Task 17: Auswertung und Bericht

**Files:**
- Create: `farbversuch/results/main/kennzahlen.md`, `farbversuch/BERICHT.md`

- [ ] **Step 1: Kennzahlen erzeugen** · Run: `python -m farbversuch.analyze --results farbversuch/results/main --seeds 400-409 > farbversuch/results/main/kennzahlen.md` · Expected: Tabellen je System und Bedingung, P1–P5 erfüllt/nicht erfüllt, Abbruchkriterium
- [ ] **Step 2: `BERICHT.md` schreiben** in der festen Gliederung: 1. Frage und Aufbau (kurz). 2. Beobachtet (Zahlen aus `kennzahlen.md`, P1–P5 je erfüllt oder nicht, Abbruchkriterium). 3. Deutung (Annahme), jede Aussage als Annahme gekennzeichnet. 4. Grenzen, mindestens: S1-A kann mit 1000 Permutationen und Holm über 1192 Kandidaten strukturell nichts öffnen; Null-Ströme haben 300, Einsatzströme 400 Episoden. 5. Pilot-Änderungen (aus `PROTOKOLL.md`) und nachträgliche Erkundungen, getrennt und mit dem Hinweis, dass sie auf frischen Seeds bestätigt werden müssen.
- [ ] **Step 3: Sprachregel prüfen** · Run: `grep -nE "bestätigt|bewiesen|ersten Prinzipien" farbversuch/BERICHT.md` · Expected: jeder Treffer bezieht sich auf eine erfüllte Vorhersage
- [ ] **Step 4: Commit** · `git add farbversuch/BERICHT.md farbversuch/results/main/kennzahlen.md && git commit -m "bericht: Auswertung Hauptlauf"`
