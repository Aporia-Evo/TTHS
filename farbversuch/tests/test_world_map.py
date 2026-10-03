import time

import numpy as np

from farbversuch.tests.helpers import open_map
from farbversuch.world import (
    CH_COLOR,
    CH_GOAL,
    CH_WALL,
    GOALDIR,
    OBS_DIM,
    bfs_distances,
    make_map,
    obs_index,
    observe,
    recolor,
)


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
