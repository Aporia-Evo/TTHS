"""Ablauf pro Seed. Als einziges Modul kennt run.py die Einsatzbedingungen; Routine, Vorwärtsmodell und
Monitor sehen nur Beobachtungen, Aktionen und Verschiebungen. Teil 1: Üben (Phase 1) und Prämissen."""
import time
from dataclasses import dataclass

import numpy as np

from farbversuch.config import Config
from farbversuch.forward import ForwardModel, freq_surprise
from farbversuch.monitor import calibrate_cusum, calibrate_m3
from farbversuch.routine import Routine, teacher_action, train_routine
from farbversuch.seeds import FORWARD, INIT, INVARIANCE, NULL, PREMISE_FWD, RECOLOR, TEACHER, episode_rngs, rng
from farbversuch.world import N_DISP, Map, Traj, bfs_distances, make_map, observe, recolor, rollout

CONDITIONS = ("none", "red", "global", "walls")


def env_params(cfg: Config, condition: str, episode: int, p_global: float) -> tuple[float, float, bool]:
    """(wall_p, p_slip, red_active) der Episode; vor dem Wechsel gilt für alle Bedingungen das Üben."""
    if condition not in CONDITIONS:
        raise ValueError(f"unbekannte Bedingung: {condition!r}")
    wall_p, p_slip, red_active = cfg.wall_p, cfg.p_slip, False
    if episode >= cfg.switch_episode:
        if condition == "red":
            red_active = True
        elif condition == "global":
            p_slip = p_global
        elif condition == "walls":
            wall_p = cfg.wall_p_dense
    return wall_p, p_slip, red_active


def routine_rollouts(routine: Routine, seed: int, tag: int, n_episodes: int, cfg: Config, *, p_slip: float,
                     red_active: bool = False, stream: int = 0) -> list[tuple[Map, Traj]]:
    """Die Routine handelt deterministisch auf frisch gezogenen Karten (wall_p = cfg.wall_p)."""
    out = []
    for e in range(n_episodes):
        map_rng, dyn_rng = episode_rngs(seed, tag, stream, e)
        m = make_map(map_rng, cfg.wall_p, cfg.min_dist)
        out.append((m, rollout(m, lambda o, pos: routine.act(o), dyn_rng, p_slip, red_active,
                               cfg.max_steps, cfg.red_p)))
    return out


def teacher_data(seed: int, cfg: Config) -> tuple[np.ndarray, np.ndarray]:
    """Der Lehrer (BFS auf der vollen Karte) handelt mit Grundrutschen; gespeichert wird die gewählte Aktion."""
    X, A = [], []
    for e in range(cfg.n_teacher_episodes):
        map_rng, dyn_rng = episode_rngs(seed, TEACHER, 0, e)
        m = make_map(map_rng, cfg.wall_p, cfg.min_dist)
        dist = bfs_distances(m.walls, m.goal)
        traj = rollout(m, lambda o, pos: teacher_action(dist, pos), dyn_rng, cfg.p_slip, False,
                       cfg.max_steps, cfg.red_p)
        X.append(traj.obs)
        A.append(traj.actions)
    return np.concatenate(X), np.concatenate(A)


@dataclass
class Phase1:
    routine: Routine
    forward: ForwardModel
    class_counts: np.ndarray        # (9,) Klassen der Vorwärts-Trainingsdaten
    m3_threshold: float
    cusum_k: float
    cusum_h: float
    sec: float


def _stack(rollouts: list[tuple[Map, Traj]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return (np.concatenate([t.obs for _, t in rollouts]), np.concatenate([t.actions for _, t in rollouts]),
            np.concatenate([t.disps for _, t in rollouts]))


def phase1(seed: int, cfg: Config) -> Phase1:
    t0 = time.perf_counter()
    X, A = teacher_data(seed, cfg)
    routine = train_routine(X, A, rng(seed, INIT), cfg.k, cfg.lr, cfg.epochs, cfg.wd, cfg.init_std)

    X, A, D = _stack(routine_rollouts(routine, seed, FORWARD, cfg.n_forward_episodes, cfg, p_slip=cfg.p_slip))
    forward = ForwardModel.fit(routine.encode(X), A, D, l2=cfg.fwd_l2, tol=cfg.logreg_tol,
                               max_iter=cfg.logreg_max_iter)
    class_counts = np.bincount(D, minlength=N_DISP)

    null_streams = []
    for j in range(cfg.n_null_streams):
        runs = routine_rollouts(routine, seed, NULL, cfg.n_null_episodes, cfg, p_slip=cfg.p_slip, stream=j)
        null_streams.append([forward.surprise(routine.encode(t.obs), t.actions, t.disps) for _, t in runs])
    m3_threshold = calibrate_m3(null_streams, window=cfg.notice_window, interval=cfg.check_interval,
                                max_alarms=cfg.max_null_alarms)
    cusum_k, cusum_h = calibrate_cusum(null_streams, sd_factor=cfg.cusum_sd_factor, max_alarms=cfg.max_null_alarms)
    return Phase1(routine, forward, class_counts, m3_threshold, cusum_k, cusum_h, time.perf_counter() - t0)


def color_invariance(seed: int, cfg: Config, routine: Routine) -> float:
    """Anteil der Schritte, in denen die Aktion bei neu gezogenen Farben (gleiche Wände, Start, Ziel) gleich bleibt."""
    same = total = 0
    for e in range(cfg.n_invariance_maps):
        map_rng, dyn_rng = episode_rngs(seed, INVARIANCE, 0, e)
        m = make_map(map_rng, cfg.wall_p, cfg.min_dist)
        traj = rollout(m, lambda o, pos: routine.act(o), dyn_rng, cfg.p_slip, False, cfg.max_steps, cfg.red_p)
        other = recolor(m, rng(seed, RECOLOR, e))
        for o, pos in zip(traj.obs, traj.positions):
            same += routine.act(o) == routine.act(observe(other, (int(pos[0]), int(pos[1]))))
            total += 1
    return same / total


def premise_checks(seed: int, cfg: Config, p1: Phase1) -> dict:
    """P1: Farbinvarianz der Routine und Vorwärtsmodell besser als das reine Häufigkeitsmodell."""
    invariance = color_invariance(seed, cfg, p1.routine)
    X, A, D = _stack(routine_rollouts(p1.routine, seed, PREMISE_FWD, cfg.n_premise_fwd_episodes, cfg,
                                      p_slip=cfg.p_slip))
    fwd = float(p1.forward.surprise(p1.routine.encode(X), A, D).mean())
    freq = float(freq_surprise(p1.class_counts, D))
    return {"ok": bool(invariance >= cfg.min_invariance and fwd < freq), "color_invariance": float(invariance),
            "fwd_surprise": fwd, "freq_surprise": freq}
