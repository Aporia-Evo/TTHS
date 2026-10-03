"""Auswertung: Kennzahlen je Strom, Vorhersagen P1-P5, Abbruchkriterium und Markdown-Zahlen für BERICHT.md.
Der Auswerter darf C_SPECIAL kennen; er gehört nicht zu den Systemen."""
import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from farbversuch.monitor import SYSTEMS
from farbversuch.run import CONDITIONS, parse_seeds
from farbversuch.world import CH_COLOR, C_SPECIAL, DELTAS, HALF, OBS_DIM, obs_index

# Eingefrorene Schwellen der Spec §7 (Hauptlauf mit 10 Seeds)
P2_MIN, P3_MIN = 9, 9
ABORT_RED_MIN, ABORT_GLOBAL_MAX = 5, 3


def is_correct(arm: str, cand: int) -> bool:
    """Richtige Zuschreibung in `red`: Farbe 0 in der Zielzelle (B) bzw. ihr Bit in Richtung der kombinierten Aktion (A)."""
    if arm == "B":
        return cand == C_SPECIAL
    return cand % OBS_DIM == obs_index(CH_COLOR[C_SPECIAL], *DELTAS[cand // OBS_DIM])


def is_colour(arm: str, cand: int) -> bool:
    if arm == "B":
        return cand < len(CH_COLOR)
    return obs_index(CH_COLOR[0], -HALF, -HALF) <= cand % OBS_DIM <= obs_index(CH_COLOR[-1], HALF, HALF)


def stream_metrics(res: dict, condition: str, arm: str, switch: int, horizon: int) -> dict:
    """Kennzahlen eines Stroms. Zeit = abgeschlossene Episoden E; Latenz = E - switch, zensiert bei `horizon`."""
    noticed = res["noticed"]
    if noticed is None:
        false_alarm, notice_latency = False, horizon
    elif condition == "none" or noticed <= switch:
        false_alarm, notice_latency = True, None
    else:
        false_alarm, notice_latency = False, noticed - switch
    opened = res["opened"]
    if condition == "red":
        # richtig nur nach dem Wechsel (E > switch): davor sind alle Ströme gleich, eine Öffnung ist keine Erkennung
        hits = [o["episode"] for o in opened if o["episode"] > switch and is_correct(arm, o["cand"])]
        correct = bool(hits)
        attr_latency = min(hits) - switch if hits else horizon
        misattr = len(opened) - len(hits)
    else:
        correct, attr_latency = None, None
        misattr = sum(is_colour(arm, o["cand"]) for o in opened)
    return {"false_alarm": false_alarm, "notice_latency": notice_latency, "correct": correct,
            "attr_latency": attr_latency, "misattr": misattr, "n_opened": len(opened)}


def _mean(xs: Sequence[float]) -> float | None:
    return float(sum(xs) / len(xs)) if xs else None


def _aggregate(condition: str, pairs: list[tuple[dict, dict]]) -> dict:
    """pairs: (Rohergebnis, Kennzahlen) je Seed mit erfüllter Prämisse."""
    raws, ms = [p[0] for p in pairs], [p[1] for p in pairs]
    lat = [m["notice_latency"] for m in ms if m["notice_latency"] is not None]
    checks = [t for r in raws for t in r["check_sec"]]
    red = condition == "red"
    return {
        "n_seeds": len(pairs),
        "n_false_alarm": sum(m["false_alarm"] for m in ms),
        "n_noticed": sum(1 for r, m in pairs if r["noticed"] is not None and not m["false_alarm"]),
        "notice_latency_mean": None if condition == "none" else _mean(lat),
        "n_correct": sum(m["correct"] for m in ms) if red else None,
        "attr_latency_mean": _mean([m["attr_latency"] for m in ms]) if red else None,
        "misattr": sum(m["misattr"] for m in ms),
        "n_opened": sum(m["n_opened"] for m in ms),
        "buffer_bytes": max((r["buffer_bytes"] for r in raws), default=0),
        "n_fits": sum(r["n_fits"] for r in raws),
        "fit_size": sum(r["fit_size"] for r in raws),
        "check_sec_mean": _mean(checks) or 0.,
        "check_sec_max": max(checks, default=0.),
        "total_sec": float(sum(r["total_sec"] for r in raws)),
    }


def _require_identical(rs: Sequence[dict], key: str, label: str) -> None:
    """Ergebnisse verschiedener Konfigurationen oder Umgebungen (BLAS-Threads!) sind nicht vergleichbar.
    Ein fehlender Schlüssel zählt als None."""
    if len(rs) < 2:
        return
    first = rs[0].get(key)
    differing = [r["seed"] for r in rs if r.get(key) != first]
    if differing:
        raise ValueError(f"{label} weicht von Seed {rs[0]['seed']} ab bei Seeds {differing}")


def evaluate(results: Sequence[dict], seeds: Sequence[int]) -> dict:
    by_seed = {r["seed"]: r for r in results}
    missing = [s for s in seeds if s not in by_seed]
    if missing:
        raise ValueError(f"kein Ergebnis für Seeds {missing}")
    rs = [by_seed[s] for s in seeds]
    _require_identical(rs, "config", "Konfiguration")
    _require_identical(rs, "env", "Umgebung (env)")
    ok = [r for r in rs if r["premise"]["ok"]]
    failed = [r["seed"] for r in rs if not r["premise"]["ok"]]

    pairs: dict[str, dict[str, list]] = {n: {c: [] for c in CONDITIONS} for n in SYSTEMS}
    for r in ok:
        cfg = r["config"]
        switch, horizon = cfg["switch_episode"], cfg["n_deploy_episodes"] - cfg["switch_episode"]
        for n in SYSTEMS:
            for c in CONDITIONS:
                raw = r["conditions"][c][n]
                pairs[n][c].append((raw, stream_metrics(raw, c, n[-1], switch, horizon)))
    systems = {n: {c: _aggregate(c, pairs[n][c]) for c in CONDITIONS} for n in SYSTEMS}

    red_correct = systems["M3-B"]["red"]["n_correct"]
    # gescheiterte Prämisse zählt gegen M3-B: nicht richtig in red, geöffnet in global
    global_open = len(failed) + sum(m["n_opened"] > 0 for _, m in pairs["M3-B"]["global"])
    n_all = len(rs)
    latency_A, latency_B = (systems[n]["red"]["attr_latency_mean"] for n in ("M3-A", "M3-B"))
    misattr_A, misattr_B = (sum(systems[n][c]["misattr"] for c in CONDITIONS) for n in ("M3-A", "M3-B"))
    hits_B, hits_S1 = (systems[n]["red"]["n_correct"] for n in ("M3-B", "S1-B"))
    return {
        "P1": {"ok_seeds": [r["seed"] for r in ok], "failed_seeds": failed},
        "P2": {"count": red_correct, "fulfilled": red_correct >= P2_MIN},
        "P3": {"count": n_all - global_open, "fulfilled": n_all - global_open >= P3_MIN},
        "P4": {"latency_A": latency_A, "latency_B": latency_B, "misattr_A": misattr_A, "misattr_B": misattr_B,
               "fulfilled": bool(ok) and (latency_A > latency_B or misattr_A > misattr_B)},
        "P5": {"M3-B": hits_B, "S1-B": hits_S1, "fulfilled": bool(ok) and hits_B >= hits_S1},
        "abort": {"red_correct": red_correct, "global_open": global_open,
                  "triggered": red_correct < ABORT_RED_MIN or global_open > ABORT_GLOBAL_MAX},
        "systems": systems,
    }


def _f(x, nd: int = 1) -> str:
    if x is None:
        return "–"
    return str(x) if isinstance(x, int) else f"{x:.{nd}f}"


def _verdict(fulfilled: bool) -> str:
    return "erfüllt" if fulfilled else "nicht erfüllt"


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines + [""]


def report_markdown(ev: dict) -> str:
    p1 = ev["P1"]
    n_ok, n = len(p1["ok_seeds"]), len(p1["ok_seeds"]) + len(p1["failed_seeds"])
    p4, p5, ab, systems = ev["P4"], ev["P5"], ev["abort"], ev["systems"]
    failed = ", ".join(str(s) for s in p1["failed_seeds"]) or "keine"
    gap_lat = None if p4["latency_A"] is None else p4["latency_A"] - p4["latency_B"]
    out = ["## Auswertung", "", "### Vorhersagen", ""]
    out += _table(["Vorhersage", "Ergebnis", "Zahlen"], [
        ["P1 Prämissen", _verdict(not p1["failed_seeds"]), f"{n_ok}/{n} Seeds erfüllen die Prämissen; gescheitert: {failed}"],
        ["P2 M3-B schreibt `red` richtig zu", _verdict(ev["P2"]["fulfilled"]),
         f"{ev['P2']['count']}/{n} Seeds (Schwelle ≥ {P2_MIN})"],
        ["P3 M3-B öffnet bei `global` nichts", _verdict(ev["P3"]["fulfilled"]),
         f"{ev['P3']['count']}/{n} Seeds ohne Öffnung (Schwelle ≥ {P3_MIN})"],
        ["P4 M3-A langsamer oder mehr Fehlzuschreibungen als M3-B", _verdict(p4["fulfilled"]),
         f"Zuschreibungslatenz `red` (Mittel, zensiert am Horizont): M3-A {_f(p4['latency_A'])}, "
         f"M3-B {_f(p4['latency_B'])}, Abstand A − B {_f(gap_lat)} Episoden; "
         f"Fehlzuschreibungen insgesamt: M3-A {p4['misattr_A']}, M3-B {p4['misattr_B']}, "
         f"Abstand A − B {p4['misattr_A'] - p4['misattr_B']}"],
        ["P5 M3-B mindestens so treffsicher wie S1-B", _verdict(p5["fulfilled"]),
         f"Treffer bei `red`: M3-B {p5['M3-B']}, S1-B {p5['S1-B']} (von {n_ok} Seeds mit erfüllter Prämisse)"],
    ])
    out += ["Seeds mit gescheiterter Prämisse zählen bei P2, P3 und beim Abbruchkriterium gegen M3-B "
            "und fehlen in P4 und P5.", "", "### Abbruchkriterium", ""]
    out += _table(["Größe", "Wert", "Abbruch bei"], [
        ["Richtige Zuschreibung M3-B bei `red`", f"{ab['red_correct']}/{n} Seeds", f"< {ABORT_RED_MIN}"],
        ["M3-B öffnet bei `global` ein Merkmal", f"{ab['global_open']}/{n} Seeds", f"> {ABORT_GLOBAL_MAX}"],
    ])
    out.append("Abbruchkriterium ausgelöst: das Wiederöffnen per Modellvergleich funktioniert in diesem Aufbau nicht."
               if ab["triggered"] else "Abbruchkriterium nicht ausgelöst.")
    out += ["", f"### Kennzahlen je System und Bedingung ({n_ok} Seeds mit erfüllter Prämisse)", ""]
    rows = []
    for name in SYSTEMS:
        for cond in CONDITIONS:
            m = systems[name][cond]
            rows.append([name, cond, str(m["n_seeds"]), str(m["n_false_alarm"]), str(m["n_noticed"]),
                         _f(m["notice_latency_mean"]), _f(m["n_correct"]), _f(m["attr_latency_mean"]),
                         str(m["misattr"]), str(m["n_opened"])])
    out += _table(["System", "Bedingung", "Seeds", "Fehlalarme", "Bemerkt", "Latenz Bemerken (Mittel)",
                   "Richtig zugeschrieben", "Latenz Zuschreibung (Mittel)", "Fehlzuschreibungen", "Geöffnet"], rows)
    out += ["Latenzen in Episoden ab dem Wechsel; nicht bemerkt oder nicht zugeschrieben zählt als Horizont. "
            "Die Latenz des Bemerkens mittelt über Seeds ohne Fehlalarm und gilt nicht für `none`.", "",
            "### Kosten", ""]
    rows = []
    for name in SYSTEMS:
        for cond in CONDITIONS:
            m = systems[name][cond]
            rows.append([name, cond, str(m["buffer_bytes"]), str(m["n_fits"]), str(m["fit_size"]),
                         _f(m["check_sec_mean"], 3), _f(m["check_sec_max"], 3), _f(m["total_sec"], 2)])
    out += _table(["System", "Bedingung", "Puffer (Byte)", "Anpassungen", "Größe der Anpassungen",
                   "Prüfung Mittel (s)", "Prüfung Max (s)", "Gesamt (s)"], rows)
    return "\n".join(out)


def load_results(results_dir: str | Path, seeds: Sequence[int]) -> list[dict]:
    out = []
    for s in seeds:
        path = Path(results_dir) / f"seed_{s}.json"
        if not path.exists():
            raise FileNotFoundError(f"seed_{s}.json fehlt in {results_dir}")
        out.append(json.loads(path.read_text()))
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m farbversuch.analyze", description="Farbversuch: Ergebnisse auswerten")
    ap.add_argument("--results", required=True, help="Ordner mit seed_<n>.json")
    ap.add_argument("--seeds", required=True, help='z. B. "400-409"')
    args = ap.parse_args(argv)
    seeds = parse_seeds(args.seeds)
    print(report_markdown(evaluate(load_results(args.results, seeds), seeds)))


if __name__ == "__main__":
    main()
