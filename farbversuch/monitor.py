"""Monitor: Ringpuffer, Kandidatenmerkmale (Arm A: Beobachtungsbit UND Aktion, Arm B: Zielzelle der Aktion),
Bemerken (M3, CUSUM), Kalibrierung an Null-Strömen und Erklären per Modellvergleich (M3) oder
Permutationstest mit Holm (S1)."""
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from farbversuch.forward import fit_logreg, fwd_design, mean_loglik
from farbversuch.world import CH_COLOR, CH_GOAL, CH_WALL, DELTAS, N_ACTIONS, N_DISP, OBS_DIM, obs_index


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


def null_threshold(null_maxima: Sequence[float], max_alarms: int = 1) -> float:
    """(max_alarms+1)-größter Wert: höchstens `max_alarms` Null-Ströme liegen darüber (Alarm = Wert > Schwelle)."""
    if len(null_maxima) <= max_alarms:
        raise ValueError(f"brauche mehr als {max_alarms} Null-Maxima, habe {len(null_maxima)}")
    return float(sorted(null_maxima, reverse=True)[max_alarms])


def m3_trace(episodes: Sequence[np.ndarray], window: int = 500, interval: int = 10) -> list[tuple[int, float]]:
    """(E, Mittel der letzten `window` Überraschungen) nach jeder `interval`-ten Episode mit >= window Schritten."""
    ends = np.cumsum([len(e) for e in episodes])
    steps = np.concatenate(episodes) if len(episodes) else np.zeros(0)
    csum = np.concatenate([[0.], np.cumsum(steps)])
    trace = []
    for E in range(interval, len(episodes) + 1, interval):
        n = int(ends[E - 1])
        if n >= window:
            trace.append((E, float((csum[n] - csum[n - window]) / window)))
    return trace


def calibrate_m3(null_streams: Sequence[Sequence[np.ndarray]], window: int = 500, interval: int = 10,
                 max_alarms: int = 1) -> float:
    """M3-Schwelle aus den Maxima der Null-Ströme; ein Strom ohne Prüfpunkt zählt als -inf."""
    maxima = []
    for episodes in null_streams:
        trace = m3_trace(episodes, window, interval)
        maxima.append(max(v for _, v in trace) if trace else -np.inf)
    return null_threshold(maxima, max_alarms)


def cusum_trace(s: np.ndarray, k: float) -> np.ndarray:
    """S_t = max(0, S_{t-1} + s_t - k), S_0 = 0."""
    out = np.zeros(len(s))
    acc = 0.
    for t, x in enumerate(s):
        acc = max(0., acc + x - k)
        out[t] = acc
    return out


def calibrate_cusum(null_streams: Sequence[Sequence[np.ndarray]], sd_factor: float = 0.5,
                    max_alarms: int = 1) -> tuple[float, float]:
    """(k, h): k = Mittel + sd_factor * Std (ddof=0) aller gepoolten Null-Schritte, h aus den Strom-Maxima."""
    streams = [np.concatenate(episodes) for episodes in null_streams]
    pooled = np.concatenate(streams)
    k = float(pooled.mean() + sd_factor * pooled.std())
    h = null_threshold([cusum_trace(s, k).max() for s in streams], max_alarms)
    return k, h


@dataclass
class FitStats:
    n_fits: int = 0
    size: int = 0            # Summe (Parameterzahl x Trainingszeilen)

    def add(self, d: int, n_train: int) -> None:
        self.n_fits += 1
        self.size += d * N_DISP * n_train


def cv_folds(n: int, rng: np.random.Generator, n_folds: int = 5) -> list[np.ndarray]:
    """Testindizes der Teilungen: eine Permutation, in n_folds Teile gespalten."""
    return np.array_split(rng.permutation(n), n_folds)


def select_m3(imp: np.ndarray, candidates: Sequence[int]) -> int | None:
    """imp: (len(candidates), n_folds). Größte mittlere Verbesserung unter Kandidaten mit imp > 0 in allen
    Teilungen; bei Gleichstand der kleinere Index."""
    imp, cand = np.asarray(imp), np.asarray(candidates)
    ok = np.flatnonzero((imp > 0).all(axis=1))
    if len(ok) == 0:
        return None
    means = imp[ok].mean(axis=1)
    return int(cand[ok[means == means.max()]].min())


def m3_explain(Z, A, D, F, opened: Sequence[int], rng: np.random.Generator, l2: float = 1e-3, n_folds: int = 5,
               tol: float = 1e-6, max_iter: int = 500, stats: FitStats | None = None) -> int | None:
    """Kreuzvalidierter Vergleich Basismodell gegen Basis + je ein Kandidat; liefert den zu öffnenden Kandidaten."""
    D = np.asarray(D, dtype=np.intp)
    opened = np.asarray(opened, dtype=np.intp)
    folds = cv_folds(len(A), rng, n_folds)
    Xb = fwd_design(Z, A, F[:, opened])
    d = Xb.shape[1]
    candidates = np.setdiff1d(np.arange(F.shape[1]), opened)
    imp = np.zeros((len(candidates), len(folds)))
    for f, test in enumerate(folds):
        train = np.setdiff1d(np.arange(len(A)), test)
        Xb_tr, Xb_te, y_tr, y_te = Xb[train], Xb[test], D[train], D[test]
        Wb, _ = fit_logreg(Xb_tr, y_tr, N_DISP, l2, tol=tol, max_iter=max_iter)
        if stats is not None:
            stats.add(d, len(train))
        llb = mean_loglik(Xb_te, y_te, Wb)
        F_tr, F_te = F[train][:, candidates], F[test][:, candidates]
        varying = F_tr.min(axis=0) != F_tr.max(axis=0)   # konstante Spalten: Verbesserung exakt 0, keine Anpassung
        W0 = np.vstack([Wb, np.zeros((1, N_DISP))])
        Xe_tr = np.empty((len(train), d + 1)); Xe_tr[:, :d] = Xb_tr
        Xe_te = np.empty((len(test), d + 1)); Xe_te[:, :d] = Xb_te
        for j in np.flatnonzero(varying):
            Xe_tr[:, d] = F_tr[:, j]
            Xe_te[:, d] = F_te[:, j]
            We, _ = fit_logreg(Xe_tr, y_tr, N_DISP, l2, W0=W0, tol=tol, max_iter=max_iter)
            if stats is not None:
                stats.add(d + 1, len(train))
            imp[j, f] = mean_loglik(Xe_te, y_te, We) - llb
    return select_m3(imp, candidates.tolist())


def perm_pvalues(S: np.ndarray, F: np.ndarray, rng: np.random.Generator,
                 n_perm: int = 1000) -> tuple[np.ndarray, np.ndarray]:
    """(diff, p) je Spalte; einseitig: diff = mean(S|F=1) - mean(S|F=0), p = (1 + #{Perm-diff >= diff}) / (1 + n_perm).
    Eine über alle Zeilen konstante Spalte hat diff 0 und p 1. Zieht immer genau n_perm Permutationen aus rng."""
    S = np.asarray(S, dtype=np.float64)
    n = len(S)
    P = np.stack([rng.permutation(S) for _ in range(n_perm)], 1)
    n1 = np.asarray(F).sum(axis=0, dtype=np.int64)
    varying = (n1 > 0) & (n1 < n)
    diff = np.zeros(F.shape[1])
    p = np.ones(F.shape[1])
    if varying.any():
        Fv = np.asarray(F[:, varying], dtype=np.float64)
        k1 = n1[varying].astype(np.float64)[:, None]
        k0 = n - k1
        total = S.sum()

        def mean_diff(sum1: np.ndarray) -> np.ndarray:   # sum1: Summe von S über Zeilen mit F=1, je Spalte
            return sum1 / k1 - (total - sum1) / k0

        obs = mean_diff(Fv.T @ S[:, None])
        perm = mean_diff(Fv.T @ P)
        diff[varying] = obs[:, 0]
        p[varying] = (1 + (perm >= obs).sum(axis=1)) / (1 + n_perm)
    return diff, p


def holm_select(p: np.ndarray, diff: np.ndarray, alpha: float = 0.05) -> list[int]:
    """Holm-Stufenverfahren über alle len(p) Hypothesen. Reihenfolge: p aufsteigend, diff absteigend, Index aufsteigend;
    Rang i (0-basiert) wird abgelehnt, wenn p <= alpha / (m - i); Abbruch beim ersten Nein. Liefert die Ablehnungen."""
    p, diff = np.asarray(p), np.asarray(diff)
    m = len(p)
    order = np.lexsort((np.arange(m), -diff, p))
    selected = []
    for i, j in enumerate(order):
        if p[j] > alpha / (m - i):
            break
        selected.append(int(j))
    return selected


def s1_explain(S: np.ndarray, F: np.ndarray, opened: Sequence[int], rng: np.random.Generator, n_perm: int = 1000,
               alpha: float = 0.05, max_open: int = 3) -> list[int]:
    """Testet alle nicht geöffneten Kandidaten (Holm über alle, auch konstante) und liefert die neu zu öffnenden
    Spaltenindizes in Testreihenfolge, höchstens max_open - len(opened)."""
    candidates = np.setdiff1d(np.arange(F.shape[1]), np.asarray(opened, dtype=np.intp))
    diff, p = perm_pvalues(S, F[:, candidates], rng, n_perm)
    rejected = holm_select(p, diff, alpha)
    return [int(candidates[j]) for j in rejected[:max(0, max_open - len(opened))]]
