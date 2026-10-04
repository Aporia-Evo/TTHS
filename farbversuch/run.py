"""Ablauf pro Seed. Als einziges Modul kennt run.py die Einsatzbedingungen; Routine, Vorwärtsmodell und
Monitor sehen nur Beobachtungen, Aktionen und Verschiebungen. Üben (Phase 1), Prämissen, p_global, Einsatz,
sequentieller Ablauf (run_seed) und gestufter paralleler Treiber über Seeds und Bedingungen (CLI)."""
import argparse
import hashlib
import json
import math
import multiprocessing
import os
import pickle
import platform
import sys
import time
from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from farbversuch.closure import color_restanteil, representation_shift
from farbversuch.config import Config
from farbversuch.forward import ForwardModel, freq_surprise
from farbversuch.monitor import (SYSTEMS, Monitor, calibrate_cusum, calibrate_m3, candidate_name, candidates_A,
                                 candidates_B, m3_null_gain, null_threshold, pre_open_m3, pre_open_s1)
from farbversuch.routine import Routine, teacher_action, train_routine
from farbversuch.seeds import (DELTA, DEPLOY, FORWARD, INIT, INVARIANCE, NULL, PGLOBAL, PREMISE_FWD, PREOPEN, PROBE,
                              RECOLOR, TEACHER, episode_rngs, rng)
from farbversuch.world import N_DISP, Map, Traj, bfs_distances, make_map, observe, recolor, rollout

CONDITIONS = ("none", "red", "global", "walls")
# Die BLAS-Threadzahl ändert die Gleitkommareihenfolge und damit die Ergebnisse: immer ein Thread
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")


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
    """Phase 1 in zwei Teilen: train_phase1 (Routine, Vorwärtsmodell, Übungspuffer; genug für die Prämisse) und
    calibrate_phase1 (Übungs-Ontologie, Schwellen, δ). Die Felder der Kalibrierung sind None, solange sie fehlt."""
    routine: Routine
    forward: ForwardModel
    class_counts: np.ndarray        # (9,) Klassen der Vorwärts-Trainingsdaten
    practice_obs: np.ndarray        # Übungspuffer: letzte buffer_size Schritte der Vorwärtsdaten
    practice_actions: np.ndarray
    practice_disps: np.ndarray
    practice_episodes: np.ndarray   # Episoden-ID (Index in den Vorwärts-Rollouts) je Schritt
    sec: float                      # Rechenzeit von Phase 1 bis hierher (ohne Prämissenprüfung)
    m3_threshold: float | None = None
    cusum_k: float | None = None
    cusum_h: float | None = None
    practice: dict[str, list[int]] | None = None    # Übungs-Ontologie je System in cfg.systems
    deltas: dict[str, float] | None = None          # Mindestverbesserung je M3-System in cfg.systems


def _stack(rollouts: list[tuple[Map, Traj]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return (np.concatenate([t.obs for _, t in rollouts]), np.concatenate([t.actions for _, t in rollouts]),
            np.concatenate([t.disps for _, t in rollouts]))


def _tail(n: int, what: str, *arrays: np.ndarray) -> tuple[np.ndarray, ...]:
    """Die letzten n Zeilen jedes Arrays. Weniger als n Zeilen sind ein Fehler: der Puffer wäre sonst stillschweigend
    kürzer als buffer_size."""
    if len(arrays[0]) < n:
        raise ValueError(f"{what}: nur {len(arrays[0])} Schritte, buffer_size verlangt {n}")
    return tuple(a[-n:] for a in arrays)


def _fit_kw(cfg: Config) -> dict:
    return dict(l2=cfg.fwd_l2, n_folds=cfg.n_folds, tol=cfg.logreg_tol, max_iter=cfg.logreg_max_iter)


def _candidates(arm: str, obs: np.ndarray, actions: np.ndarray) -> np.ndarray:
    return (candidates_B if arm == "B" else candidates_A)(obs, actions)


def calibrate_delta(buffers: Sequence[tuple], opened: Sequence[int],
                    rng_for_buffer: Callable[[int], np.random.Generator], max_alarms: int, **fit_kw) -> float:
    """δ eines M3-Systems: null_threshold über den Null-Gewinnen der Puffer; buffers[j] = (Z, A, D, F)."""
    gains = [m3_null_gain(*buffers[j], opened, rng_for_buffer(j), **fit_kw) for j in range(len(buffers))]
    return null_threshold(gains, max_alarms)


def _pre_open_practice(seed: int, cfg: Config, forward: ForwardModel, Z: np.ndarray, obs: np.ndarray,
                       actions: np.ndarray, disps: np.ndarray) -> dict[str, list[int]]:
    """Übungs-Ontologie je System auf dem Übungspuffer: M3 greedy mit fester Mindestverbesserung, S1 Holm-Ablehnungen
    auf der Überraschung des Phase-1-Vorwärtsmodells."""
    S = forward.surprise(Z, actions, disps)
    F: dict[str, np.ndarray] = {}                    # Kandidaten je Arm, nur einmal gebaut
    practice: dict[str, list[int]] = {}
    for name in cfg.systems:
        kind, arm = name.split("-")
        i = SYSTEMS.index(name)
        if arm not in F:
            F[arm] = _candidates(arm, obs, actions)
        if kind == "M3":
            practice[name] = pre_open_m3(Z, actions, disps, F[arm], lambda r, i=i: rng(seed, PREOPEN, i, r),
                                         delta=cfg.pre_open_delta, max_open=cfg.max_pre_open, **_fit_kw(cfg))
        else:
            n_perm = cfg.n_perm if arm == "B" else cfg.n_perm_A
            practice[name] = pre_open_s1(S, F[arm], rng(seed, PREOPEN, i, 0), n_perm, alpha=cfg.alpha,
                                         max_open=cfg.max_pre_open, chunk=cfg.perm_chunk)
        _log(f"seed {seed} Vor-Öffnen {name}: {', '.join(candidate_name(arm, c) for c in practice[name]) or 'keine'}")
    return practice


def _calibrate_deltas(seed: int, cfg: Config, routine: Routine, null_buffers: Sequence[tuple],
                      practice: dict[str, list[int]]) -> dict[str, float]:
    """δ je M3-System aus den Puffern (obs, Aktionen, Verschiebungen) der Null-Ströme; Basis = Übungs-Ontologie."""
    deltas: dict[str, float] = {}
    for name in cfg.systems:
        kind, arm = name.split("-")
        if kind == "M3":
            i = SYSTEMS.index(name)
            buffers = [(routine.encode(obs), actions, disps, _candidates(arm, obs, actions))
                       for obs, actions, disps in null_buffers]
            deltas[name] = calibrate_delta(buffers, practice[name], lambda j, i=i: rng(seed, DELTA, i, j),
                                           cfg.max_null_alarms, **_fit_kw(cfg))
            _log(f"seed {seed} δ {name} = {deltas[name]:.4g}")
    return deltas


def train_phase1(seed: int, cfg: Config) -> Phase1:
    """Phase 1, Spec §4 Schritte 1–2: Routine, Vorwärtsmodell und Übungspuffer. Mehr braucht die Prämisse nicht."""
    t0 = time.perf_counter()
    X, A = teacher_data(seed, cfg)
    routine = train_routine(X, A, rng(seed, INIT), cfg.k, cfg.lr, cfg.epochs, cfg.wd, cfg.init_std)
    _log(f"seed {seed} Routine trainiert ({time.perf_counter() - t0:.0f} s)")

    t1 = time.perf_counter()
    runs = routine_rollouts(routine, seed, FORWARD, cfg.n_forward_episodes, cfg, p_slip=cfg.p_slip)
    X, A, D = _stack(runs)
    episodes = np.concatenate([np.full(len(t.actions), e) for e, (_, t) in enumerate(runs)])
    forward = ForwardModel.fit(routine.encode(X), A, D, l2=cfg.fwd_l2, tol=cfg.logreg_tol,
                               max_iter=cfg.logreg_max_iter)
    class_counts = np.bincount(D, minlength=N_DISP)

    p_obs, p_actions, p_disps, p_episodes = _tail(cfg.buffer_size, "Übungspuffer (Vorwärtsdaten)", X, A, D, episodes)
    _log(f"seed {seed} Vorwärtsmodell fertig ({time.perf_counter() - t1:.0f} s)")
    return Phase1(routine=routine, forward=forward, class_counts=class_counts, practice_obs=p_obs,
                  practice_actions=p_actions, practice_disps=p_disps, practice_episodes=p_episodes,
                  sec=time.perf_counter() - t0)


def calibrate_phase1(seed: int, cfg: Config, p1: Phase1) -> Phase1:
    """Phase 1, Spec §4 Schritte 3–4: Übungs-Ontologie je System, Null-Ströme, Schwellen und δ. Teuer; läuft nur
    bei erfüllter Prämisse (Entscheidung D2 des Nutzers vom 04.10.2026)."""
    t0 = time.perf_counter()
    routine, forward = p1.routine, p1.forward
    practice = _pre_open_practice(seed, cfg, forward, routine.encode(p1.practice_obs), p1.practice_obs,
                                  p1.practice_actions, p1.practice_disps)

    t1 = time.perf_counter()
    null_streams, null_buffers = [], []
    for j in range(cfg.n_null_streams):
        runs = routine_rollouts(routine, seed, NULL, cfg.n_null_episodes, cfg, p_slip=cfg.p_slip, stream=j)
        null_streams.append([forward.surprise(routine.encode(t.obs), t.actions, t.disps) for _, t in runs])
        null_buffers.append(_tail(cfg.buffer_size, f"δ-Puffer von Null-Strom {j}", *_stack(runs)))
    m3_threshold = calibrate_m3(null_streams, window=cfg.notice_window, interval=cfg.check_interval,
                                max_alarms=cfg.max_null_alarms)
    cusum_k, cusum_h = calibrate_cusum(null_streams, sd_factor=cfg.cusum_sd_factor, max_alarms=cfg.max_null_alarms)
    _log(f"seed {seed} Null-Ströme und Schwellen fertig ({time.perf_counter() - t1:.0f} s)")
    deltas = _calibrate_deltas(seed, cfg, routine, null_buffers, practice)
    return replace(p1, m3_threshold=m3_threshold, cusum_k=cusum_k, cusum_h=cusum_h, practice=practice, deltas=deltas,
                   sec=p1.sec + time.perf_counter() - t0)


def phase1(seed: int, cfg: Config) -> Phase1:
    """Die ganze Phase 1 ohne Prämissenprüfung (prepare_seed prüft die Prämisse zwischen den beiden Teilen)."""
    return calibrate_phase1(seed, cfg, train_phase1(seed, cfg))


def invariance_and_shift(seed: int, cfg: Config, routine: Routine) -> tuple[float, float]:
    """(Anteil der Schritte, in denen die Aktion bei neu gezogenen Farben (gleiche Wände, Start, Ziel) gleich bleibt;
    Verschiebung von z: mittleres ||z - z'|| / mittleres ||z|| über die ersten cfg.n_shift_positions Positionen,
    z' aus der umgefärbten Beobachtung derselben Position)."""
    same = total = 0
    originals, recolored = [], []
    for e in range(cfg.n_invariance_maps):
        map_rng, dyn_rng = episode_rngs(seed, INVARIANCE, 0, e)
        m = make_map(map_rng, cfg.wall_p, cfg.min_dist)
        traj = rollout(m, lambda o, pos: routine.act(o), dyn_rng, cfg.p_slip, False, cfg.max_steps, cfg.red_p)
        other = recolor(m, rng(seed, RECOLOR, e))
        for o, pos in zip(traj.obs, traj.positions):
            o_other = observe(other, (int(pos[0]), int(pos[1])))
            same += routine.act(o) == routine.act(o_other)
            total += 1
            if total <= cfg.n_shift_positions:
                originals.append(o)
                recolored.append(o_other)
    shift = representation_shift(routine.encode(np.array(originals)), routine.encode(np.array(recolored)))
    return same / total, shift


def premise_checks(seed: int, cfg: Config, p1: Phase1) -> dict:
    """P1: Farbinvarianz der Routine und Vorwärtsmodell besser als das reine Häufigkeitsmodell. P1b: Restanteil auf
    dem Übungspuffer und Verschiebung von z. Ein nicht endlicher Restanteil oder eine nicht endliche Verschiebung gilt
    als nicht erfüllt (Restanteil ist nan, wenn keine Nachbarzelle bleibt)."""
    invariance, shift = invariance_and_shift(seed, cfg, p1.routine)
    X, A, D = _stack(routine_rollouts(p1.routine, seed, PREMISE_FWD, cfg.n_premise_fwd_episodes, cfg,
                                      p_slip=cfg.p_slip))
    fwd = float(p1.forward.surprise(p1.routine.encode(X), A, D).mean())
    freq = float(freq_surprise(p1.class_counts, D))
    restanteil = float(color_restanteil(p1.routine.encode(p1.practice_obs), p1.practice_obs, p1.practice_episodes,
                                        rng(seed, PROBE), l2=cfg.fwd_l2, n_folds=cfg.n_folds))
    closed = (math.isfinite(restanteil) and restanteil <= cfg.max_restanteil
              and math.isfinite(shift) and shift <= cfg.max_shift)
    return {"ok": bool(invariance >= cfg.min_invariance and fwd < freq and closed),
            "color_invariance": float(invariance), "fwd_surprise": fwd, "freq_surprise": freq,
            "restanteil": restanteil, "shift": float(shift)}


def bisect_to_target(f: Callable[[float], float], target: float, lo: float, hi: float, rel_tol: float,
                     max_iter: int) -> tuple[float, bool, int]:
    """Bisektion für ein steigendes f. Gibt (p, getroffen, Auswertungen von f) zurück. Liegt das Ziel außerhalb
    von [f(lo), f(hi)] (mit Toleranz), kommt der nächste Randwert mit False. Ist max_iter erschöpft, kommt mit False
    der ausgewertete Punkt (Rand oder Mitte) mit dem kleinsten Abstand zum Ziel. max_iter zählt die Halbierungen."""
    tol = rel_tol * target
    evals = 1
    f_hi = f(hi)
    if f_hi < target - tol:
        return hi, False, evals
    if abs(f_hi - target) <= tol:
        return hi, True, evals
    evals += 1
    f_lo = f(lo)
    if f_lo > target + tol:
        return lo, False, evals
    if abs(f_lo - target) <= tol:
        return lo, True, evals
    best_p, best_gap = min(((hi, abs(f_hi - target)), (lo, abs(f_lo - target))), key=lambda x: x[1])
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        f_mid = f(mid)
        evals += 1
        gap = abs(f_mid - target)
        if gap <= tol:
            return mid, True, evals
        if gap < best_gap:
            best_p, best_gap = mid, gap
        if f_mid < target:
            lo = mid
        else:
            hi = mid
    return best_p, False, evals


def find_p_global(seed: int, cfg: Config, p1: Phase1) -> dict:
    """p_global so, dass das Grundrutschen dieselbe mittlere Überraschung pro Schritt erzeugt wie der Rot-Effekt.
    Dieselben Karten und Würfe für jedes p; die Routine handelt, das Vorwärtsmodell aus Phase 1 misst."""
    def mean_surprise(p_slip: float, red_active: bool) -> float:
        X, A, D = _stack(routine_rollouts(p1.routine, seed, PGLOBAL, cfg.n_pglobal_episodes, cfg, p_slip=p_slip,
                                          red_active=red_active))
        return float(p1.forward.surprise(p1.routine.encode(X), A, D).mean())

    seen: dict[float, float] = {}

    def f(p_slip: float) -> float:
        seen[p_slip] = mean_surprise(p_slip, False)
        return seen[p_slip]

    lo, hi = cfg.p_slip, 1.0
    target = mean_surprise(lo, True)
    p, hit, evals = bisect_to_target(f, target, lo, hi, cfg.pglobal_tol, cfg.pglobal_max_iter)
    # Festlegung 15: nicht einschließbar nur bei den beiden Randausstiegen (f(hi) zu klein, f(lo) zu groß);
    # f(lo) wird nur ausgewertet, wenn f(hi) nicht schon ausstieg
    tol = cfg.pglobal_tol * target
    bracketed = not (seen[hi] < target - tol or (lo in seen and seen[lo] > target + tol))
    return {"p_global": float(p), "red_surprise": target, "hit": bool(hit), "bracketed": bracketed,
            "evals": int(evals)}


def stream_episodes(seed: int, cfg: Config, p1: Phase1, p_global: float, condition: str) -> Iterator[Traj]:
    """Einsatzstrom einer Bedingung. Karten und Würfe hängen nicht von der Bedingung ab, nur die Parameter."""
    for e in range(cfg.n_deploy_episodes):
        wall_p, p_slip, red_active = env_params(cfg, condition, e, p_global)
        map_rng, dyn_rng = episode_rngs(seed, DEPLOY, 0, e)
        m = make_map(map_rng, wall_p, cfg.min_dist)
        yield rollout(m, lambda o, pos: p1.routine.act(o), dyn_rng, p_slip, red_active, cfg.max_steps, cfg.red_p)


def deploy(seed: int, cfg: Config, p1: Phase1, p_global: float, condition: str) -> dict:
    """Frischer Monitor je Bedingung; er sieht nur Beobachtung, gewählte Aktion und Verschiebung."""
    monitor = Monitor(p1.routine.encode, p1.forward, m3_threshold=p1.m3_threshold, cusum_k=p1.cusum_k,
                      cusum_h=p1.cusum_h, seed=seed, systems=cfg.systems, buffer_size=cfg.buffer_size,
                      window=cfg.notice_window, interval=cfg.check_interval, n_folds=cfg.n_folds,
                      max_open=cfg.max_open, n_perm=cfg.n_perm, alpha=cfg.alpha, l2=cfg.fwd_l2, tol=cfg.logreg_tol,
                      max_iter=cfg.logreg_max_iter, practice=p1.practice, deltas=p1.deltas, n_perm_A=cfg.n_perm_A,
                      perm_chunk=cfg.perm_chunk)
    for traj in stream_episodes(seed, cfg, p1, p_global, condition):
        for o, a, d in zip(traj.obs, traj.actions, traj.disps):
            monitor.add_step(o, int(a), int(d))
        monitor.end_episode()
    return monitor.results()


def _blas_id() -> str | None:
    blas = np.show_config(mode="dicts").get("Build Dependencies", {}).get("blas", {})
    return " ".join(str(blas[k]) for k in ("name", "version") if blas.get(k)) or None


def env_block() -> dict:
    """Umgebung, in der gerechnet wurde (Threadvariablen so, wie dieser Prozess sie sieht)."""
    return {**{var: os.environ.get(var) for var in THREAD_VARS}, "numpy": np.__version__, "blas": _blas_id(),
            "python": platform.python_version()}


_SRC_DIR = Path(__file__).resolve().parent


def fingerprint() -> str:
    """Herkunft eines Zwischenstands: Quelltext aller Module von farbversuch (ohne tests/) und die Umgebung (env_block).
    Ein Zwischenstand aus anderem Code oder anderer Umgebung wird nicht wiederverwendet."""
    h = hashlib.sha256()
    for f in sorted(_SRC_DIR.glob("*.py")):
        h.update(f.name.encode() + b"\0" + f.read_bytes() + b"\0")
    h.update(json.dumps(env_block(), sort_keys=True).encode())
    return h.hexdigest()


def _log(msg: str) -> None:
    """Fortschritt für lange Läufe; nach stderr, damit stdout und Ergebnisse unberührt bleiben."""
    print(f"{time.strftime('%H:%M:%S')} {msg}", file=sys.stderr, flush=True)


def _finite_or_none(x: float) -> float | None:
    return x if math.isfinite(x) else None


@dataclass
class Prepared:
    """Alles, was die Bedingungen eines Seeds gemeinsam brauchen (Ergebnis der Vorbereitung)."""
    seed: int
    config: dict                    # cfg.as_dict(): eine gespeicherte Vorbereitung gilt nur für dieselbe Konfiguration
    fingerprint: str                # Code und Umgebung, aus denen sie stammt (fingerprint())
    p1: Phase1
    premise: dict
    p_global: dict | None           # None, wenn die Prämisse nicht erfüllt ist
    sec: float                      # Vorbereitungszeit: Phase 1, Prämisse, p_global


def prepare_seed(seed: int, cfg: Config) -> Prepared:
    """Prämisse vor den teuren Schritten (Entscheidung D2): P1 und P1b hängen nicht von Übungs-Ontologie, δ oder den
    Null-Strömen ab. Scheitert sie, entfallen Vor-Öffnen, Null-Ströme, Schwellen, δ und p_global."""
    t0 = time.perf_counter()
    _log(f"seed {seed} gestartet")
    p1 = train_phase1(seed, cfg)
    premise = premise_checks(seed, cfg, p1)
    _log(f"seed {seed} Prämisse {'ok' if premise['ok'] else 'nicht erfüllt'} (Invarianz {premise['color_invariance']:.3f}, "
         f"Restanteil {premise['restanteil']:.3f}, Verschiebung {premise['shift']:.3f})")
    p_global = None
    if premise["ok"]:
        p1 = calibrate_phase1(seed, cfg, p1)
        _log(f"seed {seed} Phase 1 fertig ({p1.sec:.0f} s)")
        p_global = find_p_global(seed, cfg, p1)
    return Prepared(seed=int(seed), config=cfg.as_dict(), fingerprint=fingerprint(), p1=p1, premise=premise,
                    p_global=p_global, sec=time.perf_counter() - t0)


def result_json(prep: Prepared, conditions: dict | None, cond_sec: dict[str, float]) -> dict:
    """Ergebnis eines Seeds. Bei nicht erfüllter Prämisse sind calibration, practice, delta, p_global und conditions
    None (nicht berechnet, Entscheidung D2). total_sec = Vorbereitungszeit + Summe der Bedingungszeiten
    (Festlegung 9), egal ob die Bedingungen nacheinander oder in getrennten Prozessen liefen."""
    p1, premise = prep.p1, prep.premise
    ok = bool(premise["ok"])
    # JSON kennt kein NaN/Infinity: ein nicht endlicher Restanteil oder eine nicht endliche Verschiebung steht als null
    json_premise = {**premise, "restanteil": _finite_or_none(premise["restanteil"]),
                    "shift": _finite_or_none(premise["shift"])}
    calibration = practice = delta = None
    if ok:
        calibration = {"m3_threshold": float(p1.m3_threshold), "cusum_k": float(p1.cusum_k),
                       "cusum_h": float(p1.cusum_h)}
        practice = {name: [{"cand": c, "name": candidate_name(name.split("-")[1], c)} for c in cands]
                    for name, cands in p1.practice.items()}
        delta = dict(p1.deltas)
    return {"seed": int(prep.seed), "config": prep.config, "env": env_block(), "premise": json_premise,
            "calibration": calibration, "practice": practice, "delta": delta,
            "p_global": prep.p_global, "conditions": conditions, "phase1_sec": float(p1.sec),
            "total_sec": float(prep.sec + sum(cond_sec.values()))}


def _deploy_timed(prep: Prepared, cfg: Config, condition: str) -> tuple[dict, float]:
    _log(f"seed {prep.seed} Bedingung {condition} gestartet")
    t0 = time.perf_counter()
    result = deploy(prep.seed, cfg, prep.p1, prep.p_global["p_global"], condition)
    return result, time.perf_counter() - t0


def run_seed(seed: int, cfg: Config) -> dict:
    """Sequentielle Referenz: vorbereiten, die Bedingungen der Reihe nach, Ergebnis. main liefert je Seed dasselbe
    (bis auf die _sec-Schlüssel), auch wenn es die Arbeit auf Prozesse verteilt."""
    t0 = time.perf_counter()
    prep = prepare_seed(seed, cfg)
    conditions, cond_sec = None, {}
    if prep.premise["ok"]:
        conditions, cond_sec = {}, {}
        for c in CONDITIONS:
            conditions[c], cond_sec[c] = _deploy_timed(prep, cfg, c)
            now = time.perf_counter()
            _log(f"seed {seed} Bedingung {c} fertig ({cond_sec[c]:.0f} s, seit Start {now - t0:.0f} s)")
    return result_json(prep, conditions, cond_sec)


def duplicates(xs: Sequence[int]) -> list[int]:
    return sorted(x for x, n in Counter(xs).items() if n > 1)


def parse_seeds(s: str) -> list[int]:
    """"400-409" (einschließlich), "0" oder "1,5"; auch gemischt: "1-3,7". Doppelte Seeds sind ein Fehler."""
    seeds: list[int] = []
    for part in s.split(","):
        lo, sep, hi = part.strip().partition("-")
        if not sep:
            seeds.append(int(lo))
        elif int(lo) <= int(hi):
            seeds.extend(range(int(lo), int(hi) + 1))
        else:
            raise ValueError(f"absteigender Bereich: {part!r}")
    if dup := duplicates(seeds):
        raise ValueError(f"doppelte Seeds: {dup}")
    return seeds


def _write_atomic(path: Path, data: str | bytes) -> None:
    """Ein Abbruch hinterlässt keine Teildatei; die Prozess-ID im Namen verhindert Kollisionen zweier Prozesse."""
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    if isinstance(data, bytes):
        tmp.write_bytes(data)
    else:
        tmp.write_text(data)
    os.replace(tmp, path)


def _load_prep(work: Path, seed: int) -> Prepared:
    return pickle.loads((work / f"seed_{seed}.prep.pkl").read_bytes())


# Die drei Stufen von main. Die Arbeiter sind top-level, damit spawn sie importieren kann; Zwischenstände liegen in
# <out>/.work und werden nur bei gleicher Konfiguration und gleicher Herkunft (fingerprint) wiederverwendet.
def _prepare_job(task: tuple[int, Config, str]) -> tuple[int, bool]:
    """Stufe 1: Vorbereitung eines Seeds als Pickle. Gibt (Seed, Prämisse erfüllt) zurück."""
    seed, cfg, out = task
    work = Path(out) / ".work"
    work.mkdir(parents=True, exist_ok=True)
    path = work / f"seed_{seed}.prep.pkl"
    prep = _load_prep(work, seed) if path.exists() else None
    if prep is not None and prep.config == cfg.as_dict() and getattr(prep, "fingerprint", None) == fingerprint():
        _log(f"seed {seed} Vorbereitung übernommen")
    else:
        prep = prepare_seed(seed, cfg)
        _write_atomic(path, pickle.dumps(prep))
    return seed, bool(prep.premise["ok"])


def _deploy_job(task: tuple[int, Config, str, str]) -> tuple[int, str]:
    """Stufe 2: eine Bedingung eines Seeds; Monitor-Ergebnis, Laufzeit, Konfiguration und Herkunft nach
    <out>/.work/seed_<n>.<condition>.json."""
    seed, cfg, out, condition = task
    work = Path(out) / ".work"
    path = work / f"seed_{seed}.{condition}.json"
    origin = fingerprint()
    stored = json.loads(path.read_text()) if path.exists() else {}
    if stored.get("config") == cfg.as_dict() and stored.get("fingerprint") == origin:
        _log(f"seed {seed} Bedingung {condition} übernommen")
    else:
        result, sec = _deploy_timed(_load_prep(work, seed), cfg, condition)
        _write_atomic(path, json.dumps({"config": cfg.as_dict(), "fingerprint": origin, "result": result,
                                        "sec": sec}))
        _log(f"seed {seed} Bedingung {condition} fertig ({sec:.0f} s)")
    return seed, condition


def _finish_job(task: tuple[int, Config, str]) -> int:
    """Stufe 3: seed_<n>.json atomar schreiben, danach die .work-Dateien dieses Seeds löschen."""
    seed, cfg, out = task
    work = Path(out) / ".work"
    prep = _load_prep(work, seed)
    conditions, cond_sec = None, {}
    if prep.premise["ok"]:
        stored = {c: json.loads((work / f"seed_{seed}.{c}.json").read_text()) for c in CONDITIONS}
        conditions = {c: stored[c]["result"] for c in CONDITIONS}
        cond_sec = {c: stored[c]["sec"] for c in CONDITIONS}
    result = result_json(prep, conditions, cond_sec)
    _write_atomic(Path(out) / f"seed_{seed}.json", json.dumps(result, indent=2) + "\n")
    for f in work.glob(f"seed_{seed}.*"):
        f.unlink(missing_ok=True)
    return seed


def _stage(fn: Callable, tasks: Sequence, jobs: int) -> Iterator:
    """Eine Stufe in einem frisch gestarteten Pool (auch bei jobs = 1); Ergebnisse in Fertigstellungsreihenfolge."""
    if tasks:
        with multiprocessing.get_context("spawn").Pool(max(1, jobs)) as pool:
            yield from pool.imap_unordered(fn, tasks)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m farbversuch.run", description="Farbversuch: Seeds ausführen")
    ap.add_argument("--seeds", required=True, help='z. B. "400-409", "0" oder "1,5"')
    ap.add_argument("--out", required=True,
                    help="Ausgabeordner für seed_<n>.json (Vorhandenes mit gleicher Konfiguration wird übersprungen; "
                         "Zwischenstände liegen in <out>/.work)")
    ap.add_argument("--config", default=None, help="Konfigurations-JSON (Standard: Config())")
    ap.add_argument("--jobs", type=int, default=1)
    args = ap.parse_args(argv)

    for var in THREAD_VARS:                      # vor dem Start der Worker: sie erben sie vor dem Import von numpy
        os.environ[var] = "1"
    cfg = Config.from_json(args.config) if args.config else Config()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    todo, skipped, foreign = [], [], []
    for s in parse_seeds(args.seeds):
        path = out / f"seed_{s}.json"
        if not path.exists():
            todo.append(s)
        elif json.loads(path.read_text()).get("config") == cfg.as_dict():
            skipped.append(s)
        else:
            foreign.append(str(path))
    if foreign:                                  # nichts überschreiben, nichts starten
        raise SystemExit("Abbruch: vorhandene Ergebnisse stammen aus einer anderen Konfiguration und werden nicht "
                         "überschrieben: " + ", ".join(foreign))
    for s in skipped:
        print(f"seed {s} übersprungen (vorhanden)", file=sys.stderr, flush=True)
    tasks = [(s, cfg, str(out)) for s in todo]
    premise_ok = dict(_stage(_prepare_job, tasks, args.jobs))                    # Stufe 1: Vorbereitung je Seed
    deploy_tasks = [(s, cfg, str(out), c) for s in todo if premise_ok[s] for c in CONDITIONS]
    for _ in _stage(_deploy_job, deploy_tasks, args.jobs):                       # Stufe 2: je Seed und Bedingung
        pass
    for seed in _stage(_finish_job, tasks, args.jobs):                           # Stufe 3: Ergebnis je Seed
        print(f"seed {seed} fertig", flush=True)


if __name__ == "__main__":
    main()
