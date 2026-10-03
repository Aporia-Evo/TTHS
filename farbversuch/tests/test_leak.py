import numpy as np
import pytest

from farbversuch.monitor import candidates_B, m3_explain, s1_explain
from farbversuch.seeds import episode_rngs
from farbversuch.world import C_SPECIAL, make_map, rollout

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
