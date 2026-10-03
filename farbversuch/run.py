"""Ablauf pro Seed. Als einziges Modul kennt run.py die Einsatzbedingungen; Routine, Vorwärtsmodell und
Monitor sehen nur Beobachtungen, Aktionen und Verschiebungen. Üben (Phase 1), Prämissen, p_global, Einsatz, CLI."""
import argparse
import json
import multiprocessing
import os
import platform
import sys
import time
from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from farbversuch.config import Config
from farbversuch.forward import ForwardModel, freq_surprise
from farbversuch.monitor import Monitor, calibrate_cusum, calibrate_m3
from farbversuch.routine import Routine, teacher_action, train_routine
from farbversuch.seeds import (DEPLOY, FORWARD, INIT, INVARIANCE, NULL, PGLOBAL, PREMISE_FWD, RECOLOR, TEACHER,
                              episode_rngs, rng)
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
                      max_iter=cfg.logreg_max_iter)
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


def _log(msg: str) -> None:
    """Fortschritt für lange Läufe; nach stderr, damit stdout und Ergebnisse unberührt bleiben."""
    print(f"{time.strftime('%H:%M:%S')} {msg}", file=sys.stderr, flush=True)


def run_seed(seed: int, cfg: Config) -> dict:
    t0 = time.perf_counter()
    _log(f"seed {seed} gestartet")
    p1 = phase1(seed, cfg)
    premise = premise_checks(seed, cfg, p1)
    _log(f"seed {seed} Phase 1 fertig ({p1.sec:.0f} s), Prämisse {'ok' if premise['ok'] else 'nicht erfüllt'}")
    result = {"seed": int(seed), "config": cfg.as_dict(), "env": env_block(), "premise": premise,
              "calibration": {"m3_threshold": float(p1.m3_threshold), "cusum_k": float(p1.cusum_k),
                              "cusum_h": float(p1.cusum_h)},
              "p_global": None, "conditions": None, "phase1_sec": float(p1.sec)}
    if premise["ok"]:
        result["p_global"] = find_p_global(seed, cfg, p1)
        result["conditions"] = {}
        for c in CONDITIONS:
            t1 = time.perf_counter()
            result["conditions"][c] = deploy(seed, cfg, p1, result["p_global"]["p_global"], c)
            now = time.perf_counter()
            _log(f"seed {seed} Bedingung {c} fertig ({now - t1:.0f} s, seit Start {now - t0:.0f} s)")
    result["total_sec"] = time.perf_counter() - t0
    return result


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


def _run_and_write(task: tuple[int, Config, str]) -> int:
    """Worker (top-level, damit spawn ihn importiert). Atomar geschrieben: ein Abbruch hinterlässt keine Teildatei."""
    seed, cfg, out = task
    path = Path(out) / f"seed_{seed}.json"
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(run_seed(seed, cfg), indent=2) + "\n")
    os.replace(tmp, path)
    return seed


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m farbversuch.run", description="Farbversuch: Seeds ausführen")
    ap.add_argument("--seeds", required=True, help='z. B. "400-409", "0" oder "1,5"')
    ap.add_argument("--out", required=True,
                    help="Ausgabeordner für seed_<n>.json (Vorhandenes mit gleicher Konfiguration wird übersprungen)")
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
            todo.append((s, cfg, str(out)))
        elif json.loads(path.read_text()).get("config") == cfg.as_dict():
            skipped.append(s)
        else:
            foreign.append(str(path))
    if foreign:                                  # nichts überschreiben, nichts starten
        raise SystemExit("Abbruch: vorhandene Ergebnisse stammen aus einer anderen Konfiguration und werden nicht "
                         "überschrieben: " + ", ".join(foreign))
    for s in skipped:
        print(f"seed {s} übersprungen (vorhanden)", file=sys.stderr, flush=True)
    if todo:                                     # auch --jobs 1 läuft in einem frisch gestarteten Worker
        with multiprocessing.get_context("spawn").Pool(max(1, args.jobs)) as pool:
            for seed in pool.imap_unordered(_run_and_write, todo):
                print(f"seed {seed} fertig", flush=True)


if __name__ == "__main__":
    main()
