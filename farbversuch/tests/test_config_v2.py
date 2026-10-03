from farbversuch.config import Config
from farbversuch.seeds import (CV, DELTA, DEPLOY, FORWARD, INIT, INVARIANCE, NULL, PERM, PGLOBAL, PREMISE_FWD, PREOPEN,
                               PROBE, RECOLOR, TEACHER)


def test_config_v2_defaults():
    c = Config()
    assert (c.n_null_streams, c.n_null_episodes, c.max_null_alarms) == (20, 400, 0)
    assert (c.n_perm, c.n_perm_A, c.perm_chunk) == (1000, 25000, 1000)
    assert (c.pre_open_delta, c.max_pre_open) == (0.01, 8)
    assert (c.max_restanteil, c.max_shift, c.n_shift_positions) == (0.15, 0.25, 500)


def test_seed_tags_unique():
    tags = [TEACHER, INIT, FORWARD, NULL, INVARIANCE, RECOLOR, PREMISE_FWD, PGLOBAL, DEPLOY, CV, PERM, PREOPEN, DELTA, PROBE]
    assert len(set(tags)) == 14 and (PREOPEN, DELTA, PROBE) == (12, 13, 14)
