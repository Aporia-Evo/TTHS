import json

import numpy as np
import pytest

from farbversuch.config import Config
from farbversuch.run import env_params, premise_checks, routine_rollouts, teacher_data
from farbversuch.tests.helpers import TINY
from farbversuch.world import OBS_DIM


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
def test_premise_checks_tiny(tiny_phase1):
    r = premise_checks(0, TINY, tiny_phase1)
    assert 0. <= r["color_invariance"] <= 1.
    assert r["ok"] == (r["color_invariance"] >= TINY.min_invariance and r["fwd_surprise"] < r["freq_surprise"])
    assert all(type(r[k]) is float for k in ("color_invariance", "fwd_surprise", "freq_surprise")) and type(r["ok"]) is bool
