"""Monitor: Ringpuffer und Kandidatenmerkmale (Arm A: Beobachtungsbit UND Aktion, Arm B: Zielzelle der Aktion)."""
import numpy as np

from farbversuch.world import CH_COLOR, CH_GOAL, CH_WALL, DELTAS, N_ACTIONS, OBS_DIM, obs_index


class RingBuffer:
    """Feste Kapazität; behält die letzten `capacity` Schritte (obs, Aktion, Verschiebung, Überraschung)."""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self._obs = np.zeros((capacity, OBS_DIM), dtype=np.uint8)
        self._action = np.zeros(capacity, dtype=np.int8)
        self._disp = np.zeros(capacity, dtype=np.int8)
        self._surprise = np.zeros(capacity, dtype=np.float64)
        self._head = 0          # nächste Schreibposition
        self._count = 0

    def add(self, obs: np.ndarray, action: int, disp: int, surprise: float) -> None:
        h = self._head
        self._obs[h] = obs
        self._action[h] = action
        self._disp[h] = disp
        self._surprise[h] = surprise
        self._head = (h + 1) % self.capacity
        self._count = min(self._count + 1, self.capacity)

    def __len__(self) -> int:
        return self._count

    def data(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """(obs, A, D, S) als Kopien, älteste Zeile zuerst."""
        if self._count < self.capacity:
            order = np.arange(self._count)
        else:
            order = (self._head + np.arange(self.capacity)) % self.capacity
        return (self._obs[order], self._action[order], self._disp[order], self._surprise[order])

    @property
    def nbytes(self) -> int:
        return self._obs.nbytes + self._action.nbytes + self._disp.nbytes + self._surprise.nbytes


CAND_B_NAMES = ("Farbe 0", "Farbe 1", "Farbe 2", "Farbe 3", "Wand", "Ziel")
_CAND_B_CHANNELS = (*CH_COLOR, CH_WALL, CH_GOAL)
# Spalte der Zielzelle in der Beobachtung: _B_COLS[a, k] gehört zu Aktion a und Kandidat k
_B_COLS = np.array([[obs_index(ch, dr, dc) for ch in _CAND_B_CHANNELS] for dr, dc in DELTAS], dtype=np.intp)


def candidates_B(obs: np.ndarray, actions: np.ndarray) -> np.ndarray:
    """(n, 6) uint8: Inhalt der Zielzelle der gewählten Aktion, Reihenfolge wie CAND_B_NAMES."""
    cols = _B_COLS[np.asarray(actions, dtype=np.intp)]
    return np.take_along_axis(obs, cols, axis=1)


def candidates_A(obs: np.ndarray, actions: np.ndarray) -> np.ndarray:
    """(n, 1192) uint8: Spalte a*298+i = obs[:, i] UND Aktion == a."""
    actions = np.asarray(actions)
    F = np.zeros((obs.shape[0], N_ACTIONS * OBS_DIM), dtype=np.uint8)
    for a in range(N_ACTIONS):
        rows = actions == a
        F[rows, a * OBS_DIM:(a + 1) * OBS_DIM] = obs[rows]
    return F


def candidate_name(arm: str, c: int) -> str:
    if arm == "B":
        return CAND_B_NAMES[c]
    if arm == "A":
        return f"bit{c % OBS_DIM}&a{c // OBS_DIM}"
    raise ValueError(f"unbekannter Arm: {arm!r}")
