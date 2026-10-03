import numpy as np

from farbversuch.routine import routine_loss_grad, teacher_action, train_routine
from farbversuch.tests.helpers import open_map
from farbversuch.world import OBS_DIM, bfs_distances


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
