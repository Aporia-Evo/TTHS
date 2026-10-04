"""Monitor: Ringpuffer, Kandidatenmerkmale (Arm A: Beobachtungsbit UND Aktion, Arm B: Zielzelle der Aktion),
Bemerken (M3, CUSUM), Kalibrierung an Null-Strömen und Erklären per Modellvergleich (M3) oder
Permutationstest mit Holm (S1), zusammengefasst in der Klasse Monitor."""
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from farbversuch.forward import fit_logreg, fwd_design, mean_loglik
from farbversuch.seeds import CV, PERM, rng as make_rng
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
    trace = []
    for E in range(interval, len(episodes) + 1, interval):
        n = int(ends[E - 1])
        if n >= window:
            # Dieselbe Reduktion wie im Monitor: kumulative Summen können die
            # Schwelle abrunden und bei identischen Daten einen Alarm erzeugen.
            trace.append((E, float(np.mean(steps[n - window:n]))))
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


def select_m3(imp: np.ndarray, candidates: Sequence[int], delta: float = 0.0) -> int | None:
    """imp: (len(candidates), n_folds). Größte mittlere Verbesserung unter Kandidaten mit imp > 0 in allen
    Teilungen und Mittel > delta (strikt); bei Gleichstand der kleinere Index."""
    imp, cand = np.asarray(imp), np.asarray(candidates)
    means = imp.mean(axis=1)
    ok = np.flatnonzero((imp > 0).all(axis=1) & (means > delta))
    if len(ok) == 0:
        return None
    best = means[ok].max()
    return int(cand[ok[means[ok] == best]].min())


def m3_improvements(Z, A, D, F, opened: Sequence[int], rng: np.random.Generator, l2: float = 1e-3, n_folds: int = 5,
                    tol: float = 1e-6, max_iter: int = 500,
                    stats: FitStats | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Kreuzvalidierte Verbesserung der mittleren Log-Likelihood je (Kandidat, Teilung): Basismodell gegen Basis +
    residualisierter Kandidat. Liefert (imp, Kandidatenindizes). Residualisiert wird je Teilung für alle Kandidaten
    gemeinsam gegen das Basisdesign; ist der Rest auf der Trainingsteilung praktisch null, bleibt die Verbesserung 0
    ohne Anpassung. rng zieht nur die Teilung."""
    D = np.asarray(D, dtype=np.intp)
    opened = np.asarray(opened, dtype=np.intp)
    folds = cv_folds(len(A), rng, n_folds)
    Xb = fwd_design(Z, A, F[:, opened])
    d = Xb.shape[1]
    candidates = np.setdiff1d(np.arange(F.shape[1]), opened)
    Fc = F[:, candidates]
    imp = np.zeros((len(candidates), len(folds)))
    for f, test in enumerate(folds):
        train = np.setdiff1d(np.arange(len(A)), test)
        Xb_tr, Xb_te, y_tr, y_te = Xb[train], Xb[test], D[train], D[test]
        Wb, _ = fit_logreg(Xb_tr, y_tr, N_DISP, l2, tol=tol, max_iter=max_iter)
        if stats is not None:
            stats.add(d, len(train))
        llb = mean_loglik(Xb_te, y_te, Wb)
        F_tr = Fc[train].astype(np.float64)
        B = np.linalg.lstsq(Xb_tr, F_tr, rcond=None)[0]
        R_tr = F_tr - Xb_tr @ B
        R_te = Fc[test] - Xb_te @ B
        # Rest ~ 0 (auch Nullspalten, konstante Spalten, Duplikate, Basiskopien): Verbesserung exakt 0, keine Anpassung
        active = np.flatnonzero(np.linalg.norm(R_tr, axis=0) > 1e-8 * np.linalg.norm(F_tr, axis=0))
        W0 = np.vstack([Wb, np.zeros((1, N_DISP))])
        Xe_tr = np.empty((len(train), d + 1)); Xe_tr[:, :d] = Xb_tr
        Xe_te = np.empty((len(test), d + 1)); Xe_te[:, :d] = Xb_te
        for j in active:
            Xe_tr[:, d] = R_tr[:, j]
            Xe_te[:, d] = R_te[:, j]
            We, _ = fit_logreg(Xe_tr, y_tr, N_DISP, l2, W0=W0, tol=tol, max_iter=max_iter)
            if stats is not None:
                stats.add(d + 1, len(train))
            imp[j, f] = mean_loglik(Xe_te, y_te, We) - llb
    return imp, candidates


def m3_explain(Z, A, D, F, opened: Sequence[int], rng: np.random.Generator, l2: float = 1e-3, n_folds: int = 5,
               tol: float = 1e-6, max_iter: int = 500, delta: float = 0.0, stats: FitStats | None = None,
               info: dict | None = None) -> int | None:
    """Liefert den zu öffnenden Kandidaten (select_m3 über m3_improvements) oder None. Bei einer Öffnung und
    gegebenem info steht danach info["gain"] = mittlere Verbesserung dieses Kandidaten."""
    imp, candidates = m3_improvements(Z, A, D, F, opened, rng, l2, n_folds, tol, max_iter, stats)
    c = select_m3(imp, candidates, delta)
    if c is not None and info is not None:
        info["gain"] = float(imp[np.flatnonzero(candidates == c)[0]].mean())
    return c


def m3_null_gain(Z, A, D, F, opened: Sequence[int], rng: np.random.Generator, **fit_kw) -> float:
    """Größte mittlere Verbesserung unter den Kandidaten mit Verbesserung > 0 in allen Teilungen, sonst 0.0."""
    imp, _ = m3_improvements(Z, A, D, F, opened, rng, **fit_kw)
    eligible = (imp > 0).all(axis=1)
    return float(imp[eligible].mean(axis=1).max()) if eligible.any() else 0.0


def pre_open_m3(Z, A, D, F, rng_for_round: Callable[[int], np.random.Generator], delta: float,
                max_open: int = 8, **fit_kw) -> list[int]:
    """Gierig: Runde r (ab 0) ruft m3_explain mit rng_for_round(r) und den bisher geöffneten auf; Ende bei None
    oder nach max_open Merkmalen."""
    opened: list[int] = []
    for r in range(max_open):
        c = m3_explain(Z, A, D, F, opened, rng_for_round(r), delta=delta, **fit_kw)
        if c is None:
            break
        opened.append(int(c))
    return opened


def _snap_to_grid(S: np.ndarray) -> np.ndarray:
    """Rundet S auf ein 2^-q-Raster, auf dem jede Teilsumme von bis zu len(S) Werten in float64 exakt ist: so
    hängt kein Summenwert von der Reihenfolge der BLAS-Summation ab (also nicht von der Blockbreite), und
    Gleichstände sind echte Gleichstände. Rundungsfehler höchstens 2^(b-52) relativ zu max|S|, b = Bitlänge von n
    (n = 2000: etwa 5e-13)."""
    amax = float(np.abs(S).max(initial=0.))
    if not np.isfinite(amax) or amax == 0.:
        return S
    q = 52 - np.frexp(amax)[1] - int(len(S)).bit_length()
    return np.ldexp(np.round(np.ldexp(S, q)), -q)


def perm_pvalues(S: np.ndarray, F: np.ndarray, rng: np.random.Generator, n_perm: int = 1000,
                 chunk: int = 1000) -> tuple[np.ndarray, np.ndarray]:
    """(diff, p) je Spalte; einseitig: diff = mean(S|F=1) - mean(S|F=0), p = (1 + #{Perm-diff >= diff}) / (1 + n_perm).
    Eine über alle Zeilen konstante Spalte hat diff 0 und p 1. Zieht immer genau n_perm Permutationen aus rng, in
    dieser Reihenfolge, aber blockweise zu höchstens chunk Spalten (Speicher unabhängig von n_perm). S wird vorher
    auf ein Raster gerundet (_snap_to_grid); dadurch ist das Ergebnis bitgleich für jedes chunk."""
    if chunk < 1:
        raise ValueError("chunk muss >= 1 sein")
    S = _snap_to_grid(np.asarray(S, dtype=np.float64))
    n = len(S)
    n1 = np.asarray(F).sum(axis=0, dtype=np.int64)
    varying = (n1 > 0) & (n1 < n)
    Fv_T = np.ascontiguousarray(np.asarray(F[:, varying], dtype=np.float64).T)
    k1 = n1[varying].astype(np.float64)[:, None]
    k0 = n - k1
    total = S.sum()

    def mean_diff(sum1: np.ndarray) -> np.ndarray:       # sum1: Summe von S über Zeilen mit F=1, je Spalte
        return sum1 / k1 - (total - sum1) / k0

    obs = mean_diff(Fv_T @ S[:, None])
    count = np.zeros(len(obs), dtype=np.int64)
    for start in range(0, n_perm, chunk):
        P = np.stack([rng.permutation(S) for _ in range(min(chunk, n_perm - start))], 1)
        count += (mean_diff(Fv_T @ P) >= obs).sum(axis=1)
    diff = np.zeros(F.shape[1])
    p = np.ones(F.shape[1])
    diff[varying] = obs[:, 0]
    p[varying] = (1 + count) / (1 + n_perm)
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
               alpha: float = 0.05, max_new: int = 3, chunk: int = 1000) -> list[int]:
    """Testet alle nicht geöffneten Kandidaten (Holm über alle, auch konstante) und liefert die neu zu öffnenden
    Spaltenindizes in Testreihenfolge, höchstens max_new."""
    candidates = np.setdiff1d(np.arange(F.shape[1]), np.asarray(opened, dtype=np.intp))
    diff, p = perm_pvalues(S, F[:, candidates], rng, n_perm, chunk)
    rejected = holm_select(p, diff, alpha)
    return [int(candidates[j]) for j in rejected[:max(0, max_new)]]


def pre_open_s1(S: np.ndarray, F: np.ndarray, rng: np.random.Generator, n_perm: int, alpha: float = 0.05,
                max_open: int = 8, chunk: int = 1000) -> list[int]:
    """Vor-Öffnen: S1 ohne bisher geöffnete Merkmale, höchstens max_open."""
    return s1_explain(S, F, [], rng, n_perm, alpha, max_new=max_open, chunk=chunk)


SYSTEMS = ("M3-B", "M3-A", "S1-B", "S1-A")


class _SystemState:
    """Zustand eines Systems: Name wie "M3-B" = Verfahren (M3, S1) und Arm (A, B). `practice` ist die Übungs-Ontologie
    (nie getestet, zählt nicht), `opened` enthält nur Wiederöffnungen."""

    def __init__(self, name: str, practice: Sequence[int] = (), delta: float = 0.0):
        self.name = name
        self.kind, self.arm = name.split("-")
        self.practice = [int(c) for c in practice]
        self.delta = float(delta)
        self.noticed: int | None = None
        self.opened: list[dict] = []
        self.stats = FitStats()
        self.check_sec: list[float] = []
        self.cusum = 0.

    @property
    def known(self) -> list[int]:
        return self.practice + [o["cand"] for o in self.opened]

    def open(self, cand: int, episode: int, gain: float | None = None) -> None:
        self.opened.append({"cand": int(cand), "name": candidate_name(self.arm, int(cand)), "episode": episode,
                            "gain": gain})


class Monitor:
    """Beobachtet nur Erfahrung (obs, Aktion, Verschiebung); die vier Systeme teilen sich einen Puffer."""

    def __init__(self, encode: Callable[[np.ndarray], np.ndarray], forward, *, m3_threshold: float,
                 cusum_k: float, cusum_h: float, seed: int, systems: Sequence[str] = SYSTEMS,
                 buffer_size: int = 2000, window: int = 500, interval: int = 10, n_folds: int = 5,
                 max_open: int = 3, n_perm: int = 1000, alpha: float = 0.05, l2: float = 1e-3,
                 tol: float = 1e-6, max_iter: int = 500, practice: Mapping[str, Sequence[int]] | None = None,
                 deltas: Mapping[str, float] | None = None, n_perm_A: int = 25000, perm_chunk: int = 1000):
        assert buffer_size >= window
        unknown = [name for name in systems if name not in SYSTEMS]
        if unknown:
            raise ValueError(f"unbekannte Systeme: {unknown}")
        self.encode, self.forward = encode, forward
        self.m3_threshold, self.cusum_k, self.cusum_h = m3_threshold, cusum_k, cusum_h
        self.seed, self.window, self.interval = seed, window, interval
        self.n_folds, self.max_open, self.n_perm, self.alpha = n_folds, max_open, n_perm, alpha
        self.n_perm_A, self.perm_chunk = n_perm_A, perm_chunk
        self.l2, self.tol, self.max_iter = l2, tol, max_iter
        self.buffer = RingBuffer(buffer_size)
        self.episodes = 0                                  # E: abgeschlossene Episoden
        practice, deltas = practice or {}, deltas or {}
        self._systems = [_SystemState(name, practice.get(name, ()), deltas.get(name, 0.0))
                         for name in SYSTEMS if name in systems]

    def add_step(self, obs: np.ndarray, action: int, disp: int) -> None:
        s = float(self.forward.surprise(self.encode(obs[None]), np.array([action]), np.array([disp]))[0])
        self.buffer.add(obs, action, disp, s)
        for system in self._systems:
            if system.kind == "S1" and system.noticed is None:
                system.cusum = max(0., system.cusum + s - self.cusum_k)
                if system.cusum > self.cusum_h:
                    system.noticed = self.episodes + 1     # Alarm in Episode i (0-basiert, E = i fertig) zählt als i + 1

    def end_episode(self) -> None:
        self.episodes += 1
        if self.episodes % self.interval == 0:
            self._checkpoint()

    def _checkpoint(self) -> None:
        E = self.episodes
        cache: dict = {}                                   # pro Prüfpunkt höchstens einmal, erst bei Bedarf berechnet

        def data():
            if "data" not in cache:
                cache["data"] = self.buffer.data()
            return cache["data"]

        def encoded():
            if "Z" not in cache:
                cache["Z"] = self.encode(data()[0])
            return cache["Z"]

        def candidates(arm):
            if arm not in cache:
                build = candidates_B if arm == "B" else candidates_A
                cache[arm] = build(data()[0], data()[1])
            return cache[arm]

        for system in self._systems:
            t0 = time.perf_counter()
            worked = False
            if system.kind == "M3" and system.noticed is None and len(self.buffer) >= self.window:
                worked = True
                if float(np.mean(data()[3][-self.window:])) > self.m3_threshold:
                    system.noticed = E
            if system.noticed is not None and len(system.opened) < self.max_open:
                worked = True
                if system.kind == "M3":
                    info: dict = {}
                    c = m3_explain(encoded(), data()[1], data()[2], candidates(system.arm), system.known,
                                   make_rng(self.seed, CV, E), l2=self.l2, n_folds=self.n_folds, tol=self.tol,
                                   max_iter=self.max_iter, delta=system.delta, stats=system.stats, info=info)
                    if c is not None:
                        system.open(c, E, info.get("gain"))
                else:
                    n_perm = self.n_perm if system.arm == "B" else self.n_perm_A
                    for c in s1_explain(data()[3], candidates(system.arm), system.known,
                                        make_rng(self.seed, PERM, E), n_perm=n_perm, alpha=self.alpha,
                                        max_new=self.max_open - len(system.opened), chunk=self.perm_chunk):
                        system.open(c, E)
            if worked:
                system.check_sec.append(time.perf_counter() - t0)

    def results(self) -> dict[str, dict]:
        return {system.name: {"noticed": system.noticed,
                              "practice": [{"cand": c, "name": candidate_name(system.arm, c)}
                                           for c in system.practice],
                              "delta": system.delta if system.kind == "M3" else None,
                              "opened": [dict(o) for o in system.opened],
                              "buffer_bytes": int(self.buffer.nbytes),
                              "n_fits": system.stats.n_fits,
                              "fit_size": system.stats.size,
                              "check_sec": list(system.check_sec),
                              "total_sec": float(sum(system.check_sec))}
                for system in self._systems}
