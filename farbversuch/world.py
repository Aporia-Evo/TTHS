"""Gitterwelt: Karte, Beobachtung (Schrittdynamik folgt in einer späteren Aufgabe)."""
from collections import deque
from dataclasses import dataclass, replace

import numpy as np

SIZE, VIEW, HALF = 9, 7, 3
N_ACTIONS = 4
DELTAS = ((-1, 0), (1, 0), (0, -1), (0, 1))          # oben, unten, links, rechts
N_COLORS, C_SPECIAL = 4, 0
CH_WALL, CH_GOAL, CH_COLOR = 0, 1, (2, 3, 4, 5)       # Kanäle je Fensterzelle
OBS_DIM = 298
GOALDIR = (294, 295, 296, 297)                        # Ziel oben, unten, links, rechts

_CELLS = VIEW * VIEW


def obs_index(ch: int, dr: int, dc: int) -> int:
    return ch * _CELLS + (dr + HALF) * VIEW + (dc + HALF)


@dataclass(frozen=True)
class Map:
    walls: np.ndarray        # (9,9) bool, Rand True
    colors: np.ndarray       # (9,9) int8, -1 genau auf Wänden
    start: tuple[int, int]
    goal: tuple[int, int]


def bfs_distances(walls: np.ndarray, goal: tuple[int, int]) -> np.ndarray:
    """Weglänge jeder Zelle zum Ziel, -1 für Wände und unerreichbare Zellen."""
    dist = np.full(walls.shape, -1, dtype=int)
    dist[goal] = 0
    queue = deque([goal])
    while queue:
        r, c = queue.popleft()
        for dr, dc in DELTAS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < walls.shape[0] and 0 <= nc < walls.shape[1] \
                    and not walls[nr, nc] and dist[nr, nc] < 0:
                dist[nr, nc] = dist[r, c] + 1
                queue.append((nr, nc))
    return dist


def _draw_colors(rng: np.random.Generator, walls: np.ndarray) -> np.ndarray:
    colors = rng.integers(0, N_COLORS, (SIZE, SIZE)).astype(np.int8)
    colors[walls] = -1
    return colors


def make_map(rng: np.random.Generator, wall_p: float, min_dist: int = 5) -> Map:
    """Zieht Karten, bis Start und Ziel Manhattan-Abstand >= min_dist haben und ein Weg existiert."""
    while True:
        walls = np.ones((SIZE, SIZE), dtype=bool)
        walls[1:-1, 1:-1] = rng.random((SIZE - 2, SIZE - 2)) < wall_p
        colors = _draw_colors(rng, walls)
        free = np.argwhere(~walls)                    # zeilenweise
        if len(free) < 2:
            continue
        i, j = rng.choice(len(free), 2, replace=False)
        start, goal = (int(free[i][0]), int(free[i][1])), (int(free[j][0]), int(free[j][1]))
        if abs(start[0] - goal[0]) + abs(start[1] - goal[1]) < min_dist:
            continue
        if bfs_distances(walls, goal)[start] < 0:
            continue
        return Map(walls, colors, start, goal)


def recolor(m: Map, rng: np.random.Generator) -> Map:
    """Gleiche Wände, Start und Ziel; Farben neu gezogen."""
    return replace(m, colors=_draw_colors(rng, m.walls))


def observe(m: Map, pos: tuple[int, int]) -> np.ndarray:
    """7x7-Fenster um pos (Wand, Ziel, vier Farbkanäle) plus vier Zielrichtungsbits."""
    r, c = pos
    win_walls = np.ones((VIEW, VIEW), dtype=bool)     # außerhalb des Gitters: Wand
    win_colors = np.full((VIEW, VIEW), -1, dtype=np.int8)
    win_goal = np.zeros((VIEW, VIEW), dtype=bool)
    r0, c0 = r - HALF, c - HALF
    lo_r, hi_r = max(r0, 0), min(r0 + VIEW, SIZE)
    lo_c, hi_c = max(c0, 0), min(c0 + VIEW, SIZE)
    src = (slice(lo_r, hi_r), slice(lo_c, hi_c))
    dst = (slice(lo_r - r0, hi_r - r0), slice(lo_c - c0, hi_c - c0))
    win_walls[dst] = m.walls[src]
    win_colors[dst] = m.colors[src]
    gr, gc = m.goal
    if 0 <= gr - r0 < VIEW and 0 <= gc - c0 < VIEW:
        win_goal[gr - r0, gc - c0] = True

    o = np.zeros(OBS_DIM, dtype=np.uint8)
    o[CH_WALL * _CELLS:(CH_WALL + 1) * _CELLS] = win_walls.ravel()
    o[CH_GOAL * _CELLS:(CH_GOAL + 1) * _CELLS] = win_goal.ravel()
    for k, ch in enumerate(CH_COLOR):
        o[ch * _CELLS:(ch + 1) * _CELLS] = (win_colors == k).ravel()
    o[list(GOALDIR)] = (gr < r, gr > r, gc < c, gc > c)
    return o
