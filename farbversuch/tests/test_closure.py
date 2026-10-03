import numpy as np

from farbversuch.closure import color_restanteil, representation_shift
from farbversuch.world import CH_COLOR, CH_WALL, DELTAS, make_map, obs_index, observe


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
