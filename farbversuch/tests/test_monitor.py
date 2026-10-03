import json

import numpy as np
import pytest

import farbversuch.monitor as monitor
from farbversuch import seeds
from farbversuch.forward import ForwardModel
from farbversuch.monitor import FitStats, Monitor, SYSTEMS, cusum_trace, m3_trace
from farbversuch.world import CH_COLOR, DELTAS, OBS_DIM, obs_index


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


def test_systems_run_in_order_with_own_candidates_and_names(monkeypatch):
    seen = []

    def m3(Z, A, D, F, opened, rng, **k):
        seen.append(("M3", F.shape[1], list(opened))); return 2 if F.shape[1] == 6 else 301

    def s1(S, F, opened, rng, **k):
        seen.append(("S1", F.shape[1], list(opened))); return [4, 0]

    monkeypatch.setattr(monitor, "m3_explain", m3); monkeypatch.setattr(monitor, "s1_explain", s1)
    m = make(); feed(m, 10); r = m.results()
    assert seen == [("M3", 6, []), ("M3", 1192, []), ("S1", 6, []), ("S1", 1192, [])]
    assert [(o["cand"], o["name"], o["episode"]) for o in r["M3-B"]["opened"]] == [(2, "Farbe 2", 10)]
    assert [(o["cand"], o["name"], o["episode"]) for o in r["M3-A"]["opened"]] == [(301, "bit3&a1", 10)]
    assert [(o["cand"], o["name"]) for o in r["S1-B"]["opened"]] == [(4, "Wand"), (0, "Farbe 0")]
    assert r["S1-B"]["noticed"] == 5 and r["S1-A"]["noticed"] == 5


def test_explain_gets_buffer_data_opened_and_keyed_rng(monkeypatch):
    got = {}

    def m3(Z, A, D, F, opened, rng, **k):
        got["m3"] = (Z.shape, A.tolist(), D.tolist(), F.shape, list(opened), rng.bit_generator.state, k)
        return 5

    def s1(S, F, opened, rng, **k):
        got["s1"] = (S.tolist(), list(opened), rng.bit_generator.state, k); return []

    monkeypatch.setattr(monitor, "m3_explain", m3); monkeypatch.setattr(monitor, "s1_explain", s1)
    m = make(seed=7, systems=("M3-B", "S1-B"), l2=.1, n_folds=3, n_perm=50, alpha=.01, max_open=4)
    feed(m, 20, steps=2)
    shape, A, D, Fshape, opened, state, k = got["m3"]            # zweiter Aufruf: E = 20, ein Merkmal offen
    assert shape == (40, 3) and A == [0] * 40 and D == [1] * 40 and Fshape == (40, 6) and opened == [5]
    assert state == seeds.rng(7, seeds.CV, 20).bit_generator.state
    assert k["l2"] == .1 and k["n_folds"] == 3 and isinstance(k["stats"], FitStats)
    S, opened, state, k = got["s1"]
    assert S == [1.] * 40 and opened == [] and state == seeds.rng(7, seeds.PERM, 20).bit_generator.state
    assert k == dict(n_perm=50, alpha=.01, max_new=4)


def test_m3_fit_stats_reported_and_results_are_json(monkeypatch):
    def m3(Z, A, D, F, opened, rng, stats=None, **k):
        stats.add(10, 8); stats.add(11, 8); return None

    monkeypatch.setattr(monitor, "m3_explain", m3)
    m = make(systems=("M3-B", "S1-B")); feed(m, 10)
    r = m.results()
    assert r["M3-B"]["n_fits"] == 2 and r["M3-B"]["fit_size"] == (10 + 11) * 9 * 8
    assert r["S1-B"]["n_fits"] == 0 and r["S1-B"]["fit_size"] == 0
    assert len(r["M3-B"]["check_sec"]) == 1 and r["M3-B"]["total_sec"] == sum(r["M3-B"]["check_sec"])
    json.dumps(r)


def test_check_sec_only_for_checkpoints_with_work(quiet):
    m = make(m3_threshold=99., systems=("M3-B", "S1-B")); feed(m, 20, steps=2)
    r = m.results()
    assert len(r["M3-B"]["check_sec"]) == 2                      # prüft bei E = 10 und 20, bemerkt nie
    assert len(r["S1-B"]["check_sec"]) == 2                      # erklärt ab E = 10
    m = make(window=500, systems=("M3-B",)); feed(m, 20)
    assert m.results()["M3-B"]["check_sec"] == []                # Puffer nie >= window


def test_unknown_system_and_small_buffer_rejected():
    with pytest.raises(ValueError):
        make(systems=("M3-C",))
    with pytest.raises(AssertionError):
        make(buffer_size=4, window=5)


def test_seeds_keys_and_episode_rngs():
    assert seeds.rng(1, 2, 3).random() == np.random.default_rng([1, 2, 3]).random()
    assert (seeds.TEACHER, seeds.INIT, seeds.CV, seeds.PERM) == (1, 2, 10, 11)
    card, dyn = seeds.episode_rngs(5, seeds.DEPLOY, 3, 17)
    assert card.random() == np.random.default_rng([5, seeds.DEPLOY, 3, 17, 0]).random()
    assert dyn.random() == np.random.default_rng([5, seeds.DEPLOY, 3, 17, 1]).random()


def test_real_explainers_find_the_slippery_colour_feature():
    rng = np.random.default_rng(0)
    encode = lambda X: X[..., :20].astype(float)
    def draw(n): return (rng.random((n, OBS_DIM)) < .3).astype(np.uint8)
    fwd = ForwardModel.fit(encode(draw(2000)), rng.integers(0, 4, 2000), np.ones(2000, int))
    m = Monitor(encode, fwd, m3_threshold=.3, cusum_k=.2, cusum_h=3., seed=3, systems=("M3-B", "S1-B"),
                window=100, n_perm=200)
    for ep in range(60):
        for _ in range(20):
            obs, a = draw(1)[0], int(rng.integers(0, 4))
            slip = ep >= 30 and obs[obs_index(CH_COLOR[0], *DELTAS[a])] == 1     # ab Episode 30 rutscht Farbe 0
            m.add_step(obs, a, 2 if slip else 1)
        m.end_episode()
    r = m.results()
    assert 30 < r["S1-B"]["noticed"] <= 40 and 30 < r["M3-B"]["noticed"] <= 60
    for name in ("M3-B", "S1-B"):
        assert [o["name"] for o in r[name]["opened"]] == ["Farbe 0"]
    assert r["M3-B"]["n_fits"] > 0 and r["S1-B"]["n_fits"] == 0


class SeqFwd:
    """Vorwärtsmodell-Attrappe: liefert die vorgegebene Überraschung Schritt für Schritt der Reihe nach."""
    def __init__(self, values): self._values = iter(values)
    def surprise(self, Z, A, D): return np.array([next(self._values)])


def run_stream(episodes, **kw):
    mon = Monitor(lambda X: X[..., :3].astype(float), SeqFwd(np.concatenate(episodes)), seed=0,
                  systems=("M3-B", "S1-B"), **kw)
    for ep in episodes:
        for _ in ep:
            mon.add_step(np.zeros(OBS_DIM, np.uint8), 0, 1)
        mon.end_episode()
    return mon.results()


def offline_m3(episodes, threshold, window, interval):
    return next((E for E, v in m3_trace(episodes, window, interval) if v > threshold), None)


def offline_s1(episodes, k, h):
    alarm = np.flatnonzero(cusum_trace(np.concatenate(episodes), k) > h)
    if len(alarm) == 0:
        return None
    return int(np.searchsorted(np.cumsum([len(e) for e in episodes]), alarm[0], side="right")) + 1


def test_live_noticing_equals_the_offline_traces_on_random_streams(quiet):
    rng = np.random.default_rng(0)
    m3_seen, s1_seen = [], []
    for i in range(20):
        episodes = [rng.random(int(rng.integers(1, 9))) * 2 for _ in range(int(rng.integers(30, 60)))]
        window, interval = int(rng.integers(10, 40)), int(rng.integers(2, 6))
        buffer_size = window + int(rng.integers(0, window))        # Fenster <= Puffer < alle Schritte
        flat = np.concatenate(episodes)
        assert buffer_size < len(flat)
        values = sorted(v for _, v in m3_trace(episodes, window, interval))
        if i % 4 == 0:
            threshold = values[-1] + .1                                 # nie über der Schwelle
        else:
            j = int(rng.integers(0, len(values) - 1))                   # Schwelle zwischen zwei Prüfwerten
            assert values[j + 1] - values[j] > 1e-9
            threshold = (values[j] + values[j + 1]) / 2
        k = float(flat.mean())
        peak = cusum_trace(flat, k).max()
        h = peak * 1.01 + .01 if i % 4 == 1 else float(peak * rng.uniform(.3, .9))
        r = run_stream(episodes, m3_threshold=threshold, cusum_k=k, cusum_h=h, window=window, interval=interval,
                       buffer_size=buffer_size)
        m3_seen.append(offline_m3(episodes, threshold, window, interval))
        s1_seen.append(offline_s1(episodes, k, h))
        assert r["M3-B"]["noticed"] == m3_seen[-1] and r["S1-B"]["noticed"] == s1_seen[-1]
    for seen in (m3_seen, s1_seen):                                     # der Vergleich ist nicht leer
        assert None in seen and len({e for e in seen if e is not None}) >= 3


def test_m3_averages_the_last_window_steps_of_a_larger_buffer(quiet):
    episodes = [np.zeros(5)] * 20 + [np.ones(5)] * 10                   # 100 niedrige, dann hohe Schritte
    r = run_stream(episodes, m3_threshold=.5, cusum_k=.5, cusum_h=1e9, window=10, interval=5, buffer_size=100)
    assert r["M3-B"]["noticed"] == offline_m3(episodes, .5, 10, 5) == 25    # der ganze Puffer läge bei 0,2


def test_alarms_need_strictly_more_than_the_threshold(quiet):
    ones = [np.ones(2)] * 10
    common = dict(cusum_k=1., cusum_h=1., window=4, interval=5, buffer_size=10)
    assert run_stream(ones, m3_threshold=1., **common)["M3-B"]["noticed"] is None        # Mittel == Schwelle
    assert run_stream(ones, m3_threshold=np.nextafter(1., 0.), **common)["M3-B"]["noticed"] == 5
    single = [np.ones(1)] * 6                                           # CUSUM 0,5 / 1,0 / 1,5 mit k = 0,5
    common = dict(m3_threshold=99., cusum_k=.5, window=4, interval=5, buffer_size=10)
    assert run_stream(single, cusum_h=1., **common)["S1-B"]["noticed"] == 3             # 1,0 == h löst nicht aus
    assert run_stream(single, cusum_h=np.nextafter(1., 0.), **common)["S1-B"]["noticed"] == 2
    assert run_stream(single, cusum_h=1.5, **common)["S1-B"]["noticed"] == 4              # 1,5 == h, erst 2,0 löst aus
