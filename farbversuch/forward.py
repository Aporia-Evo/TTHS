"""Vorwaertsmodell: multinomiale logistische Regression (L-BFGS) auf [Z | onehot(A) | 1 | extra]."""
from collections import deque
from dataclasses import dataclass

import numpy as np

from farbversuch.world import N_ACTIONS, N_DISP


def log_softmax(L: np.ndarray) -> np.ndarray:
    """Zeilenweises log-softmax, stabil durch Subtraktion des Zeilenmaximums."""
    shifted = L - L.max(axis=1, keepdims=True)
    return shifted - np.log(np.exp(shifted).sum(axis=1, keepdims=True))


def logreg_obj(W: np.ndarray, X: np.ndarray, y: np.ndarray, l2: float) -> tuple[float, np.ndarray]:
    """Mittlere negative Log-Likelihood + (l2/2)*||W||^2 (alle Gewichte inkl. Bias) und Gradient."""
    n = X.shape[0]
    cols = np.arange(n)
    LT = W.T @ X.T                                       # (K, n): Reduktionen laufen ueber die lange Achse
    m = LT.max(axis=0)
    E = np.exp(LT - m)
    S = E.sum(axis=0)
    nll = float(np.mean(m + np.log(S) - LT[y, cols]))
    E /= S
    E[y, cols] -= 1.0
    return nll + 0.5 * l2 * float(np.sum(W * W)), (E @ X).T / n + l2 * W


def fit_logreg(X, y, n_classes: int, l2: float, W0: np.ndarray | None = None,
               tol: float = 1e-6, max_iter: int = 500) -> tuple[np.ndarray, int]:
    """L-BFGS (Gedaechtnis 10, Armijo c1 = 1e-4) bis max|Gradient| < tol; liefert (W, Iterationen)."""
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.intp)
    shape = (X.shape[1], n_classes)
    W = np.zeros(shape) if W0 is None else np.array(W0, dtype=np.float64)
    f, G = logreg_obj(W, X, y, l2)
    g = G.ravel()
    pairs: deque = deque(maxlen=10)                      # (s, y, 1 / s^T y)
    for it in range(max_iter):
        if np.abs(g).max() < tol:                        # auch vor dem ersten Schritt
            return W, it
        q = g.copy()
        alphas = []
        for s, yv, rho in reversed(pairs):
            a = rho * (s @ q)
            alphas.append(a)
            q -= a * yv
        if pairs:
            s, yv, _ = pairs[-1]
            q *= (s @ yv) / (yv @ yv)
        for (s, yv, rho), a in zip(pairs, reversed(alphas)):
            q += (a - rho * (yv @ q)) * s
        d = -q
        slope = g @ d
        step = 1.0
        for _ in range(41):                              # Schritt 1, dann hoechstens 40 Halbierungen
            W_new = W + step * d.reshape(shape)
            f_new, G_new = logreg_obj(W_new, X, y, l2)
            if f_new <= f + 1e-4 * step * slope:
                break
            step *= 0.5
        else:
            return W, it
        g_new = G_new.ravel()
        s, yv = step * d, g_new - g
        sy = float(s @ yv)
        if sy > 1e-12:
            pairs.append((s, yv, 1.0 / sy))
        W, f, g = W_new, f_new, g_new
    return W, max_iter


def mean_loglik(X, y, W) -> float:
    return float(np.mean(log_softmax(X @ W)[np.arange(len(y)), y]))


def fwd_design(Z: np.ndarray, A: np.ndarray, extra: np.ndarray | None = None) -> np.ndarray:
    """Spalten [Z | onehot(A, 4) | 1 | extra]."""
    n = len(A)
    onehot = np.zeros((n, N_ACTIONS))
    onehot[np.arange(n), A] = 1.0
    parts = [np.asarray(Z, dtype=np.float64), onehot, np.ones((n, 1))]
    if extra is not None:
        parts.append(np.asarray(extra, dtype=np.float64))
    return np.hstack(parts)


@dataclass
class ForwardModel:
    W: np.ndarray

    @classmethod
    def fit(cls, Z, A, D, l2: float = 1e-3, tol: float = 1e-6, max_iter: int = 500) -> "ForwardModel":
        W, _ = fit_logreg(fwd_design(Z, A), D, N_DISP, l2, tol=tol, max_iter=max_iter)
        return cls(W)

    def surprise(self, Z, A, D) -> np.ndarray:
        """-log p(D | Z, A) je Zeile."""
        D = np.asarray(D, dtype=np.intp)
        return -log_softmax(fwd_design(Z, A) @ self.W)[np.arange(len(D)), D]


def freq_surprise(train_counts: np.ndarray, D_eval: np.ndarray) -> float:
    """Mittel von -log((count + 1) / (N + 9)) mit +1-Glaettung."""
    counts = np.asarray(train_counts, dtype=np.float64)
    return float(np.mean(-np.log((counts[D_eval] + 1.0) / (counts.sum() + N_DISP))))
