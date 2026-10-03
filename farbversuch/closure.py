"""P1b: wie geschlossen ist die Farbdimension in der Darstellung z (Restanteil, Verschiebung)."""
import numpy as np

from farbversuch.forward import fit_logreg
from farbversuch.world import CH_COLOR, CH_WALL, DELTAS, N_COLORS, obs_index


def _with_bias(X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=np.float64)
    return np.hstack([X, np.ones((len(X), 1))])


def _cv_hits(X: np.ndarray, y: np.ndarray, fold: np.ndarray, n_folds: int, l2: float) -> tuple[int, int]:
    """Treffer der Probe aus z bzw. Rohbeobachtung ueber alle Test-Teilungen; Rueckgabe (Treffer, Zeilen)."""
    hits = rows = 0
    for k in range(n_folds):
        te = fold == k
        tr = ~te
        if not te.any() or not tr.any():
            continue
        W, _ = fit_logreg(X[tr], y[tr], N_COLORS, l2)
        hits += int(np.sum(np.argmax(X[te] @ W, axis=1) == y[te]))
        rows += int(te.sum())
    return hits, rows


def _majority_hits(y: np.ndarray, fold: np.ndarray, n_folds: int) -> int:
    hits = 0
    for k in range(n_folds):
        te = fold == k
        tr = ~te
        if not te.any() or not tr.any():
            continue
        major = np.argmax(np.bincount(y[tr], minlength=N_COLORS))
        hits += int(np.sum(y[te] == major))
    return hits


def color_restanteil(Z: np.ndarray, obs: np.ndarray, episode_ids: np.ndarray, rng: np.random.Generator,
                     l2: float = 1e-3, n_folds: int = 5, min_rows: int = 20, min_gap: float = 0.05) -> float:
    """Mittel ueber die vier Nachbarzellen von (acc_z - acc_maj) / (acc_raw - acc_maj); nan, wenn keine Zelle bleibt."""
    Zb, Rb = _with_bias(Z), _with_bias(obs)
    ids = np.unique(episode_ids)
    groups = np.array_split(rng.permutation(ids), n_folds)       # eine Teilung fuer Z, Roh und Mehrheit
    fold_of = {int(e): k for k, g in enumerate(groups) for e in g}
    fold_all = np.array([fold_of[int(e)] for e in episode_ids])

    values = []
    for dr, dc in DELTAS:
        free = np.asarray(obs[:, obs_index(CH_WALL, dr, dc)]) == 0
        if free.sum() < min_rows:
            continue
        colors = np.stack([obs[free, obs_index(ch, dr, dc)] for ch in CH_COLOR], axis=1)
        y = np.argmax(colors, axis=1)
        fold = fold_all[free]
        hits_z, n = _cv_hits(Zb[free], y, fold, n_folds, l2)
        if n == 0:
            continue
        hits_raw, _ = _cv_hits(Rb[free], y, fold, n_folds, l2)
        acc_maj = _majority_hits(y, fold, n_folds) / n
        gap = hits_raw / n - acc_maj
        if gap <= min_gap:
            continue
        values.append((hits_z / n - acc_maj) / gap)
    return float(np.mean(values)) if values else float("nan")


def representation_shift(Z: np.ndarray, Z_recolored: np.ndarray) -> float:
    """Mittlere Zeilennorm von Z - Z' geteilt durch mittlere Zeilennorm von Z."""
    num = np.linalg.norm(np.asarray(Z, dtype=float) - np.asarray(Z_recolored, dtype=float), axis=1).mean()
    den = np.linalg.norm(np.asarray(Z, dtype=float), axis=1).mean()
    return float(num / den)
