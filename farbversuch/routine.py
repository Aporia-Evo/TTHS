"""Routine: Lehrer-Aktion (BFS), tanh-Encoder mit Softmax-Policy und Full-Batch-Training."""
from dataclasses import dataclass

import numpy as np

from farbversuch.world import DELTAS, N_ACTIONS, OBS_DIM


def teacher_action(dist: np.ndarray, pos: tuple[int, int]) -> int:
    """Nachbar mit kleinstem BFS-Abstand >= 0; bei Gleichstand der kleinste Aktionsindex."""
    best_action, best_dist = -1, -1
    for action, (dr, dc) in enumerate(DELTAS):
        d = int(dist[pos[0] + dr, pos[1] + dc])
        if d >= 0 and (best_action < 0 or d < best_dist):
            best_action, best_dist = action, d
    if best_action < 0:
        raise ValueError(f"kein begehbarer, erreichbarer Nachbar von {pos}")
    return best_action


@dataclass
class Routine:
    E: np.ndarray            # (k, 298)
    W: np.ndarray            # (k+1, 4), letzte Zeile = Bias

    def encode(self, X: np.ndarray) -> np.ndarray:
        return np.tanh(np.asarray(X, dtype=np.float64) @ self.E.T)

    def act(self, obs: np.ndarray) -> int:
        z = self.encode(obs)
        return int(np.argmax(np.append(z, 1.0) @ self.W))

    def act_batch(self, X: np.ndarray) -> np.ndarray:
        Z = self.encode(X)
        return np.argmax(np.hstack([Z, np.ones((len(Z), 1))]) @ self.W, axis=1)


def routine_loss_grad(E: np.ndarray, W: np.ndarray, X: np.ndarray, A: np.ndarray,
                      wd: float) -> tuple[float, np.ndarray, np.ndarray]:
    """Mittlere Kreuzentropie + (wd/2)*||E||^2 und Gradienten nach E und W."""
    X = np.asarray(X, dtype=np.float64)
    n = len(X)
    Z = np.tanh(X @ E.T)
    Zb = np.hstack([Z, np.ones((n, 1))])
    logits = Zb @ W
    logits -= logits.max(axis=1, keepdims=True)
    log_norm = np.log(np.exp(logits).sum(axis=1))
    log_p = logits - log_norm[:, None]
    loss = float(-log_p[np.arange(n), A].mean() + 0.5 * wd * np.sum(E * E))
    d_logits = np.exp(log_p)
    d_logits[np.arange(n), A] -= 1.0
    d_logits /= n
    gW = Zb.T @ d_logits
    d_pre = (d_logits @ W[:-1].T) * (1.0 - Z * Z)
    gE = d_pre.T @ X + wd * E
    return loss, gE, gW


def train_routine(X: np.ndarray, A: np.ndarray, rng: np.random.Generator, k: int = 32, lr: float = 0.5,
                  epochs: int = 1000, wd: float = 1e-3, init_std: float = 0.01) -> Routine:
    X = np.asarray(X, dtype=np.float64)
    E = rng.normal(0.0, init_std, (k, OBS_DIM))
    W = np.zeros((k + 1, N_ACTIONS))
    for _ in range(epochs):
        _, gE, gW = routine_loss_grad(E, W, X, A, wd)
        E -= lr * gE
        W -= lr * gW
    return Routine(E, W)
