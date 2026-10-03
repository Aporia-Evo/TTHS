import numpy as np

from farbversuch.monitor import (
    CAND_B_NAMES,
    RingBuffer,
    candidate_name,
    candidates_A,
    candidates_B,
)
from farbversuch.world import CH_COLOR, CH_GOAL, CH_WALL, OBS_DIM, obs_index


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
