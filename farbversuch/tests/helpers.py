import numpy as np

from farbversuch.world import SIZE, Map


def open_map(colour: int = 1, start=(4, 4), goal=(1, 1)) -> Map:
    """Nur Randwände, alle Innenzellen in einer Farbe."""
    walls = np.ones((SIZE, SIZE), dtype=bool)
    walls[1:-1, 1:-1] = False
    colors = np.full((SIZE, SIZE), colour, dtype=np.int8)
    colors[walls] = -1
    return Map(walls, colors, tuple(start), tuple(goal))
