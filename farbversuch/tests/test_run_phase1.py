import dataclasses
import json
from types import SimpleNamespace

import numpy as np
import pytest

import farbversuch.run as run
from farbversuch.config import Config
from farbversuch.monitor import SYSTEMS
from farbversuch.routine import Routine
from farbversuch.run import (calibrate_delta, env_params, invariance_and_shift, phase1, premise_checks,
                             routine_rollouts, teacher_data)
from farbversuch.seeds import DELTA, FORWARD, INVARIANCE, NULL, PREOPEN, RECOLOR, episode_rngs, rng
from farbversuch.tests.helpers import TINY
from farbversuch.world import CH_COLOR, N_DISP, OBS_DIM, make_map, observe, recolor, rollout


def test_config_defaults_match_spec():
    c = Config()
    assert (c.wall_p, c.wall_p_dense, c.p_slip, c.red_p, c.min_dist, c.max_steps) == (0.15, 0.30, 0.10, 0.5, 5, 40)
    assert (c.n_teacher_episodes, c.k, c.lr, c.epochs, c.wd, c.init_std) == (4000, 32, 0.5, 1000, 1e-3, 0.01)
    assert (c.n_forward_episodes, c.n_null_streams, c.n_null_episodes, c.max_null_alarms) == (1000, 20, 400, 0)
    assert (c.n_invariance_maps, c.min_invariance, c.n_pglobal_episodes, c.pglobal_tol) == (500, 0.95, 300, 0.02)
    assert (c.n_deploy_episodes, c.switch_episode, c.buffer_size, c.notice_window, c.check_interval) == (400, 100, 2000, 500, 10)
    assert (c.n_folds, c.max_open, c.n_perm, c.alpha, c.cusum_sd_factor) == (5, 3, 1000, 0.05, 0.5)


def test_config_json_roundtrip(tmp_path):
    c = Config(epochs=7, systems=("M3-B",)); c.to_json(tmp_path / "c.json")
    assert Config.from_json(tmp_path / "c.json") == c


def test_config_json_strict_and_complete(tmp_path):
    c = Config(systems=("M3-B", "S1-A")); d = c.as_dict()
    assert d["systems"] == ["M3-B", "S1-A"] and json.loads(json.dumps(d)) == d
    (tmp_path / "part.json").write_text('{"epochs": 7, "systems": ["S1-B"]}')
    assert Config.from_json(tmp_path / "part.json") == Config(epochs=7, systems=("S1-B",))
    (tmp_path / "bad.json").write_text('{"epochs": 7, "epoch": 8}')
    with pytest.raises(ValueError, match="epoch"):
        Config.from_json(tmp_path / "bad.json")


def test_env_params_schedule():
    c = Config()
    assert env_params(c, "red", 99, .4) == (.15, .10, False) and env_params(c, "red", 100, .4) == (.15, .10, True)
    assert env_params(c, "global", 99, .4) == (.15, .10, False) and env_params(c, "global", 100, .4) == (.15, .4, False)
    assert env_params(c, "walls", 100, .4) == (.30, .10, False) and env_params(c, "none", 300, .4) == (.15, .10, False)
    with pytest.raises(ValueError):
        env_params(c, "blau", 100, .4)


def test_teacher_data_shape_and_determinism():
    c = Config(n_teacher_episodes=12)
    X, A = teacher_data(3, c); X2, A2 = teacher_data(3, c)
    assert X.dtype == np.uint8 and X.shape == (len(A), OBS_DIM) and len(A) >= 12
    assert set(np.unique(A)) <= {0, 1, 2, 3}
    assert np.array_equal(X, X2) and np.array_equal(A, A2)


@pytest.mark.slow
def test_phase1_tiny(tiny_phase1):
    p = tiny_phase1
    assert p.routine.E.shape == (32, OBS_DIM) and np.isfinite([p.m3_threshold, p.cusum_k, p.cusum_h]).all()
    assert p.class_counts.sum() > 0 and p.class_counts[5:].sum() == 0      # beim Üben keine Doppelschritte


@pytest.mark.slow
def test_phase1_streams_and_timing(tiny_phase1):
    p = tiny_phase1
    assert p.sec > 0 and p.class_counts.shape == (9,)
    a = routine_rollouts(p.routine, 0, 4, 5, TINY, p_slip=TINY.p_slip, stream=2)
    b = routine_rollouts(p.routine, 0, 4, 5, TINY, p_slip=TINY.p_slip, stream=2)
    assert len(a) == 5 and all(np.array_equal(x[1].obs, y[1].obs) and np.array_equal(x[0].colors, y[0].colors)
                               for x, y in zip(a, b))


@pytest.mark.slow
def test_phase1_v2_tiny(tiny_phase1):
    p = tiny_phase1
    assert set(p.practice) == set(TINY.systems) and all(len(v) <= TINY.max_pre_open for v in p.practice.values())
    assert set(p.deltas) == {s for s in TINY.systems if s.startswith("M3")} and all(d >= 0 for d in p.deltas.values())
    assert len(p.practice_obs) == len(p.practice_episodes) == TINY.buffer_size
    assert all(type(c) is int for v in p.practice.values() for c in v)
    assert all(type(d) is float for d in p.deltas.values())
    assert json.loads(json.dumps([p.practice, p.deltas])) == [p.practice, p.deltas]


@pytest.mark.slow
def test_premise_needs_only_the_trained_part_of_phase1(tiny_phase1):
    # Entscheidung D2: P1/P1b vor Übungs-Ontologie, Null-Strömen und δ; das Ergebnis hängt nicht davon ab
    trained = run.train_phase1(0, TINY)
    assert trained.practice is None and trained.deltas is None
    assert (trained.m3_threshold, trained.cusum_k, trained.cusum_h) == (None, None, None)
    assert premise_checks(0, TINY, trained) == premise_checks(0, TINY, tiny_phase1)
    full = run.calibrate_phase1(0, TINY, trained)
    assert full.practice == tiny_phase1.practice and full.deltas == tiny_phase1.deltas
    assert (full.m3_threshold, full.cusum_k, full.cusum_h) == (tiny_phase1.m3_threshold, tiny_phase1.cusum_k,
                                                               tiny_phase1.cusum_h)
    assert full.sec >= trained.sec


def _stacked(runs):
    return (np.concatenate([t.obs for _, t in runs]), np.concatenate([t.actions for _, t in runs]),
            np.concatenate([t.disps for _, t in runs]))


@pytest.mark.slow
def test_practice_buffer_is_the_tail_of_the_forward_data(tiny_phase1):
    p, n = tiny_phase1, TINY.buffer_size
    runs = routine_rollouts(p.routine, 0, FORWARD, TINY.n_forward_episodes, TINY, p_slip=TINY.p_slip)
    obs, A, D = _stacked(runs)
    ids = np.concatenate([np.full(len(t.actions), e) for e, (_, t) in enumerate(runs)])
    assert np.array_equal(p.practice_obs, obs[-n:]) and np.array_equal(p.practice_actions, A[-n:])
    assert np.array_equal(p.practice_disps, D[-n:]) and np.array_equal(p.practice_episodes, ids[-n:])


def test_delta_is_max_of_null_gains(monkeypatch):
    gains = iter([.1, .5, .2, .4, .3])
    monkeypatch.setattr(run, "m3_null_gain", lambda *a, **k: next(gains))
    assert run.calibrate_delta([(None, None, None, None)] * 5, [], lambda j: None, max_alarms=0) == .5


def test_calibrate_delta_passes_buffer_opened_rng_and_fit_kw(monkeypatch):
    calls = []

    def fake(Z, A, D, F, opened, rng_, **kw):
        calls.append((Z, A, D, F, opened, rng_, kw))
        return float(len(calls))
    monkeypatch.setattr(run, "m3_null_gain", fake)
    buffers = [tuple(f"{n}{j}" for n in "ZADF") for j in range(3)]
    gens = [np.random.default_rng(j) for j in range(3)]
    assert calibrate_delta(buffers, [4, 7], lambda j: gens[j], max_alarms=1, l2=.5, n_folds=3) == 2.
    assert [c[:4] for c in calls] == buffers and [c[5] for c in calls] == gens
    assert all(c[4] == [4, 7] and c[6] == {"l2": .5, "n_folds": 3} for c in calls)


@pytest.mark.slow
def test_phase1_uses_the_agreed_rng_keys_and_buffers(monkeypatch, tiny_phase1):
    seen = {"m3": [], "s1": [], "gain": []}
    real_m3, real_s1, real_gain = run.pre_open_m3, run.pre_open_s1, run.m3_null_gain

    def spy_m3(Z, A, D, F, rng_for_round, delta, max_open=8, **fit_kw):
        states = [rng_for_round(r).bit_generator.state for r in range(3)]
        seen["m3"].append((F.shape[1], delta, max_open, fit_kw, states))
        return real_m3(Z, A, D, F, rng_for_round, delta, max_open, **fit_kw)

    def spy_s1(S, F, rng_, n_perm, alpha=.05, max_open=8, chunk=1000):
        seen["s1"].append((len(S), F.shape[1], rng_.bit_generator.state, n_perm, alpha, max_open, chunk))
        return real_s1(S, F, rng_, n_perm, alpha, max_open, chunk)

    def spy_gain(Z, A, D, F, opened, rng_, **fit_kw):
        seen["gain"].append((A.copy(), D.copy(), F.shape[1], list(opened), rng_.bit_generator.state, fit_kw))
        return real_gain(Z, A, D, F, opened, rng_, **fit_kw)
    monkeypatch.setattr(run, "pre_open_m3", spy_m3)
    monkeypatch.setattr(run, "pre_open_s1", spy_s1)
    monkeypatch.setattr(run, "m3_null_gain", spy_gain)
    p = phase1(0, TINY)
    assert p.practice == tiny_phase1.practice and p.deltas == tiny_phase1.deltas       # und sie sind deterministisch
    fit_kw = dict(l2=TINY.fwd_l2, n_folds=TINY.n_folds, tol=TINY.logreg_tol, max_iter=TINY.logreg_max_iter)
    i_m3, i_b, i_a = (SYSTEMS.index(s) for s in ("M3-B", "S1-B", "S1-A"))

    (width, delta, max_open, kw, states), = seen["m3"]
    assert (width, delta, max_open, kw) == (6, TINY.pre_open_delta, TINY.max_pre_open, fit_kw)
    assert states == [rng(0, PREOPEN, i_m3, r).bit_generator.state for r in range(3)]
    assert [(s[0], s[1], s[3:]) for s in seen["s1"]] == [
        (TINY.buffer_size, 6, (TINY.n_perm, TINY.alpha, TINY.max_pre_open, TINY.perm_chunk)),
        (TINY.buffer_size, 1192, (TINY.n_perm_A, TINY.alpha, TINY.max_pre_open, TINY.perm_chunk))]
    assert [s[2] for s in seen["s1"]] == [rng(0, PREOPEN, i, 0).bit_generator.state for i in (i_b, i_a)]

    assert len(seen["gain"]) == TINY.n_null_streams
    for j, (A, D, width, opened, state, kw) in enumerate(seen["gain"]):
        runs = routine_rollouts(p.routine, 0, NULL, TINY.n_null_episodes, TINY, p_slip=TINY.p_slip, stream=j)
        _, A_j, D_j = _stacked(runs)
        assert np.array_equal(A, A_j[-TINY.buffer_size:]) and np.array_equal(D, D_j[-TINY.buffer_size:])
        assert (width, opened, kw) == (6, p.practice["M3-B"], fit_kw)
        assert state == rng(0, DELTA, i_m3, j).bit_generator.state


def _colour_blind(seed=0):
    E = np.random.default_rng(seed).normal(0., 1., (8, OBS_DIM))
    for ch in CH_COLOR:
        E[:, ch * 49:(ch + 1) * 49] = 0.
    return Routine(E, np.random.default_rng(seed + 1).normal(0., 1., (9, 4)))


def test_invariance_and_shift_colour_blind_and_sensitive():
    cfg = dataclasses.replace(TINY, n_invariance_maps=6)
    inv, shift = invariance_and_shift(0, cfg, _colour_blind())
    assert (inv, shift) == (1., 0.) and type(inv) is float and type(shift) is float
    sensitive = Routine(np.random.default_rng(5).normal(0., 1., (8, OBS_DIM)), _colour_blind().W)
    inv2, shift2 = invariance_and_shift(0, cfg, sensitive)
    assert 0. <= inv2 < 1. and shift2 > 0.
    assert (inv2, shift2) == invariance_and_shift(0, cfg, sensitive)


def test_shift_uses_the_first_positions_of_the_invariance_runs(monkeypatch):
    routine, seen = Routine(np.random.default_rng(5).normal(0., 1., (8, OBS_DIM)), _colour_blind().W), []
    monkeypatch.setattr(run, "representation_shift", lambda Z, Zr: (seen.append((Z, Zr)), 0.)[1])
    cfg = dataclasses.replace(TINY, n_invariance_maps=4, n_shift_positions=3)
    invariance_and_shift(0, cfg, routine)
    map_rng, dyn_rng = episode_rngs(0, INVARIANCE, 0, 0)
    m = make_map(map_rng, cfg.wall_p, cfg.min_dist)
    traj = rollout(m, lambda o, pos: routine.act(o), dyn_rng, cfg.p_slip, False, cfg.max_steps, cfg.red_p)
    other = recolor(m, rng(0, RECOLOR, 0))
    (Z, Zr), = seen
    assert np.array_equal(Z, routine.encode(traj.obs[:3]))
    recolored = np.array([observe(other, (int(r), int(c))) for r, c in traj.positions[:3]])
    assert np.array_equal(Zr, routine.encode(recolored))


@pytest.mark.slow
def test_premise_checks_tiny(tiny_phase1):
    r = premise_checks(0, TINY, tiny_phase1)
    assert 0. <= r["color_invariance"] <= 1.
    floats = ("color_invariance", "fwd_surprise", "freq_surprise", "restanteil", "shift")
    assert all(type(r[k]) is float for k in floats)
    assert type(r["ok"]) is bool


@pytest.mark.slow
def test_premise_has_p1b(tiny_phase1):
    r = premise_checks(0, TINY, tiny_phase1)
    assert list(r) == ["ok", "color_invariance", "fwd_surprise", "freq_surprise", "restanteil", "shift"]
    assert isinstance(r["restanteil"], float) and r["shift"] >= 0.
    assert r["ok"] == bool(r["color_invariance"] >= TINY.min_invariance and r["fwd_surprise"] < r["freq_surprise"]
                           and r["restanteil"] <= TINY.max_restanteil and r["shift"] <= TINY.max_shift)


def _fake_premise(monkeypatch, restanteil, shift, invariance=1.):
    traj = SimpleNamespace(obs=np.zeros((3, OBS_DIM), np.uint8), actions=np.zeros(3, int), disps=np.zeros(3, int))
    monkeypatch.setattr(run, "invariance_and_shift", lambda seed, cfg, routine: (invariance, shift))
    monkeypatch.setattr(run, "color_restanteil", lambda *a, **k: restanteil)
    monkeypatch.setattr(run, "routine_rollouts", lambda *a, **k: [(None, traj)])
    return SimpleNamespace(routine=SimpleNamespace(encode=lambda X: np.zeros((len(X), 2))),
                           forward=SimpleNamespace(surprise=lambda Z, A, D: np.zeros(len(A))),
                           class_counts=np.ones(N_DISP), practice_obs=np.zeros((5, OBS_DIM), np.uint8),
                           practice_episodes=np.arange(5))


@pytest.mark.parametrize("restanteil, shift, invariance, ok", [
    (.10, .20, 1., True), (.15, .25, 1., True),                       # Grenzen zählen als erfüllt
    (.16, .20, 1., False), (.10, .26, 1., False), (.10, .20, .94, False),
    (float("nan"), .20, 1., False), (.10, float("nan"), 1., False),    # nicht endlich: nicht erfüllt
    (float("-inf"), .20, 1., False), (.10, float("inf"), 1., False),
])
def test_premise_ok_needs_finite_p1b_values_within_bounds(monkeypatch, restanteil, shift, invariance, ok):
    cfg = dataclasses.replace(TINY, min_invariance=.95, max_restanteil=.15, max_shift=.25)
    r = premise_checks(0, cfg, _fake_premise(monkeypatch, restanteil, shift, invariance))
    assert r["ok"] is ok and np.isclose(r["shift"], shift, equal_nan=True) and r["fwd_surprise"] < r["freq_surprise"]
    assert type(r["restanteil"]) is float and type(r["shift"]) is float
