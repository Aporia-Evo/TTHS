import numpy as np

from farbversuch.config import Config
from farbversuch.world import SIZE, Map


def open_map(colour: int = 1, start=(4, 4), goal=(1, 1)) -> Map:
    """Nur Randwände, alle Innenzellen in einer Farbe."""
    walls = np.ones((SIZE, SIZE), dtype=bool)
    walls[1:-1, 1:-1] = False
    colors = np.full((SIZE, SIZE), colour, dtype=np.int8)
    colors[walls] = -1
    return Map(walls, colors, tuple(start), tuple(goal))


TINY = Config(n_teacher_episodes=300, epochs=200, n_forward_episodes=150, n_null_streams=5, n_null_episodes=40,
              n_invariance_maps=20, min_invariance=0.0, n_premise_fwd_episodes=30, n_pglobal_episodes=30,
              pglobal_max_iter=8, n_deploy_episodes=60, switch_episode=20, buffer_size=400, notice_window=100,
              n_perm=200, n_perm_A=400, max_restanteil=1.0, max_shift=10.0, systems=("M3-B", "S1-B", "S1-A"))
