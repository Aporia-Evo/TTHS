import json

import pytest

from farbversuch.analyze import (MAIN_SEEDS, evaluate, is_colour, is_correct, load_results, main, report_markdown,
                                 stream_metrics)
from farbversuch.monitor import SYSTEMS
from farbversuch.run import CONDITIONS
from farbversuch.world import CH_COLOR, CH_GOAL, CH_WALL, C_SPECIAL, DELTAS, obs_index


def sysres(noticed=None, opened=()):
    return {"noticed": noticed, "opened": [{"cand": c, "name": "", "episode": e} for c, e in opened],
            "buffer_bytes": 0, "n_fits": 0, "fit_size": 0, "check_sec": [], "total_sec": 0.}


def fake_result(seed, red_ok=True, global_open=False, ok=True):
    conds = {c: {s: sysres() for s in SYSTEMS} for c in CONDITIONS}
    conds["red"]["M3-B"] = sysres(110, [(C_SPECIAL, 120)] if red_ok else [])
    conds["global"]["M3-B"] = sysres(110, [(4, 120)] if global_open else [])
    return {"seed": seed, "config": {"switch_episode": 100, "n_deploy_episodes": 400},
            "premise": {"ok": ok}, "conditions": conds if ok else None}


A_RED = 0 * 298 + obs_index(CH_COLOR[C_SPECIAL], -1, 0)       # Farbe 0 oben, Aktion oben


def test_is_correct():
    assert is_correct("B", C_SPECIAL) and not is_correct("B", 4)
    assert is_correct("A", A_RED) and not is_correct("A", 1 * 298 + obs_index(CH_COLOR[C_SPECIAL], -1, 0))


def test_latency_and_censoring():
    m = stream_metrics(sysres(130, [(C_SPECIAL, 140)]), "red", "B", 100, 300)
    assert (m["notice_latency"], m["correct"], m["attr_latency"], m["false_alarm"]) == (30, True, 40, False)
    assert stream_metrics(sysres(), "red", "B", 100, 300)["notice_latency"] == 300
    assert stream_metrics(sysres(250), "none", "B", 100, 300)["false_alarm"]


def test_prechange_alarm_in_red():               # Review Focus 4
    m = stream_metrics(sysres(90, [(C_SPECIAL, 120)]), "red", "B", 100, 300)
    assert m["false_alarm"] and m["notice_latency"] is None and m["correct"] and m["attr_latency"] == 20


def test_preswitch_opening_in_red_is_a_misattribution():
    # vor dem Wechsel sind alle vier Ströme gleich: eine frühe Öffnung kann keine Erkennung der roten Änderung sein
    m = stream_metrics(sysres(60, [(C_SPECIAL, 70)]), "red", "B", 100, 300)
    assert (m["correct"], m["attr_latency"], m["misattr"], m["n_opened"]) == (False, 300, 1, 1)
    # bei E = switch ist noch keine rote Episode abgeschlossen; E = switch + 1 ist die erste mögliche richtige
    assert not stream_metrics(sysres(80, [(C_SPECIAL, 100)]), "red", "B", 100, 300)["correct"]
    m = stream_metrics(sysres(80, [(C_SPECIAL, 101)]), "red", "B", 100, 300)
    assert m["correct"] and m["attr_latency"] == 1 and m["misattr"] == 0
    m = stream_metrics(sysres(60, [(C_SPECIAL, 70), (C_SPECIAL, 120)]), "red", "B", 100, 300)
    assert (m["correct"], m["attr_latency"], m["misattr"]) == (True, 20, 1)
    m = stream_metrics(sysres(60, [(A_RED, 70)]), "red", "A", 100, 300)
    assert (m["correct"], m["attr_latency"], m["misattr"]) == (False, 300, 1)


def test_preswitch_correct_opening_does_not_count_for_p2():
    seeds = list(range(400, 410))
    results = [fake_result(s) for s in seeds]
    sys_variant(results[0], "M3-B", "red", sysres(60, [(C_SPECIAL, 70)]))
    assert evaluate(results, seeds)["P2"]["count"] == 9


def test_misattribution_rules():
    assert stream_metrics(sysres(110, [(2, 120), (4, 130)]), "global", "B", 100, 300)["misattr"] == 1
    assert stream_metrics(sysres(110, [(4, 120), (C_SPECIAL, 130)]), "red", "B", 100, 300)["misattr"] == 1


def test_predictions_and_abort():
    seeds = list(range(400, 410))
    ev = evaluate([fake_result(s, red_ok=s != 400, global_open=s == 401) for s in seeds], seeds)
    assert ev["P2"] == {"count": 9, "fulfilled": True} and ev["P3"]["fulfilled"] and not ev["abort"]["triggered"]
    ev = evaluate([fake_result(s, red_ok=s < 404) for s in seeds], seeds)
    assert not ev["P2"]["fulfilled"] and ev["abort"]["triggered"]
    ev = evaluate([fake_result(s, global_open=s < 404) for s in seeds], seeds)
    assert not ev["P3"]["fulfilled"] and ev["abort"]["triggered"]


def test_failed_premise_counts_against_m3b():
    seeds = list(range(400, 410))
    ev = evaluate([fake_result(s, ok=s != 409) for s in seeds], seeds)
    assert ev["P1"]["failed_seeds"] == [409] and ev["P2"]["count"] == 9 and ev["abort"]["global_open"] == 1


# --- über die Vorgabe hinaus ---

def test_colour_features_and_arm_a_misattribution():
    assert [is_colour("B", c) for c in range(6)] == [True] * 4 + [False] * 2
    colour_bit = 2 * 298 + obs_index(CH_COLOR[3], 2, -3)          # irgendein Farbbit, Aktion unten
    wall_bit = obs_index(CH_WALL, -1, 0)
    goal_bit = obs_index(CH_GOAL, 0, 1)
    assert is_colour("A", colour_bit)
    assert not is_colour("A", wall_bit) and not is_colour("A", goal_bit) and not is_colour("A", 3 * 298 + 297)
    assert stream_metrics(sysres(110, [(colour_bit, 120), (wall_bit, 125)]), "walls", "A", 100, 300)["misattr"] == 1
    # red, Arm A: jede Öffnung außer der richtigen (auch Wandbit) ist Fehlzuschreibung
    m = stream_metrics(sysres(110, [(wall_bit, 120), (A_RED, 130), (colour_bit, 140)]), "red", "A", 100, 300)
    assert m["correct"] and m["attr_latency"] == 30 and m["misattr"] == 2 and m["n_opened"] == 3


def test_opening_before_switch_is_not_correct_and_none_gives_horizon():
    m = stream_metrics(sysres(80, [(C_SPECIAL, 90)]), "red", "B", 100, 300)
    assert m["attr_latency"] == 300 and not m["correct"] and m["misattr"] == 1
    m = stream_metrics(sysres(110, [(4, 120)]), "red", "B", 100, 300)
    assert not m["correct"] and m["attr_latency"] == 300
    m = stream_metrics(sysres(110, [(C_SPECIAL, 150), (C_SPECIAL, 130)]), "red", "B", 100, 300)
    assert m["attr_latency"] == 30                                # frühestes richtiges Öffnen zählt
    m = stream_metrics(sysres(110, [(C_SPECIAL, 120)]), "global", "B", 100, 300)
    assert m["correct"] is None and m["attr_latency"] is None and m["misattr"] == 1 and m["n_opened"] == 1


def test_none_condition_every_notice_is_false_alarm():
    m = stream_metrics(sysres(250), "none", "B", 100, 300)
    assert m["false_alarm"] and m["notice_latency"] is None
    assert not stream_metrics(sysres(), "none", "B", 100, 300)["false_alarm"]


def test_failed_premise_counts_as_global_open_and_misses_red():
    seeds = list(range(400, 410))
    ev = evaluate([fake_result(s, ok=s >= 406) for s in seeds], seeds)
    assert ev["P1"]["ok_seeds"] == [406, 407, 408, 409] and ev["P1"]["failed_seeds"] == [400, 401, 402, 403, 404, 405]
    assert ev["P2"]["count"] == 4 and ev["P3"]["count"] == 4 and not ev["P3"]["fulfilled"]
    assert ev["abort"] == {"red_correct": 4, "global_open": 6, "triggered": True}


def sys_variant(res, name, cond, sr):
    res["conditions"][cond][name] = sr
    return res


def test_p4_p5_compare_only_premise_ok_seeds():
    seeds = list(range(400, 410))
    results = []
    for s in seeds:
        r = fake_result(s, ok=s != 409)
        if r["conditions"]:
            # M3-A: spät (Latenz 80 statt 20) und eine Fehlzuschreibung in none
            sys_variant(r, "M3-A", "red", sysres(110, [(A_RED, 180)]))
            sys_variant(r, "M3-A", "none", sysres(110, [(2 * 298 + obs_index(CH_COLOR[1], 0, 0), 120)]))
            # S1-B trifft nur in 5 Seeds
            sys_variant(r, "S1-B", "red", sysres(105, [(C_SPECIAL, 106)] if s < 405 else []))
        results.append(r)
    ev = evaluate(results, seeds)
    assert ev["P4"] == {"latency_A": 80.0, "latency_B": 20.0, "misattr_A": 9, "misattr_B": 0, "fulfilled": True}
    assert ev["P5"] == {"M3-B": 9, "S1-B": 5, "fulfilled": True}
    # S1-B besser als M3-B: P5 nicht erfüllt
    results = [fake_result(s, red_ok=s != 400) for s in seeds]
    for r in results:
        sys_variant(r, "S1-B", "red", sysres(105, [(C_SPECIAL, 106)]))
    ev = evaluate(results, seeds)
    assert ev["P5"] == {"M3-B": 9, "S1-B": 10, "fulfilled": False}


def test_p4_fulfilled_by_either_gap_and_not_by_neither():
    seeds = list(range(400, 410))
    base = [fake_result(s) for s in seeds]                      # M3-A: nie öffnen (Horizont 300) -> langsamer
    assert evaluate(base, seeds)["P4"]["fulfilled"]
    equal = []
    for s in seeds:
        r = fake_result(s)
        sys_variant(r, "M3-A", "red", sysres(110, [(A_RED, 120)]))
        equal.append(r)
    ev = evaluate(equal, seeds)["P4"]
    assert (ev["latency_A"], ev["latency_B"], ev["misattr_A"], ev["misattr_B"]) == (20.0, 20.0, 0, 0)
    assert not ev["fulfilled"]
    more_misattr = []
    for s in seeds:
        r = fake_result(s)
        sys_variant(r, "M3-A", "red", sysres(110, [(A_RED, 120), (1 * 298 + 297, 130)]))
        more_misattr.append(r)
    ev = evaluate(more_misattr, seeds)["P4"]
    assert ev["latency_A"] == ev["latency_B"] and ev["misattr_A"] == 10 and ev["fulfilled"]


def test_system_metrics_and_costs():
    seeds = [400, 401]
    results = [fake_result(s) for s in seeds]
    for k, r in enumerate(results):
        r["conditions"]["red"]["M3-B"].update(buffer_bytes=1000, n_fits=3 + k, fit_size=100 * (k + 1),
                                              check_sec=[0.5, 1.5] if k == 0 else [2.5], total_sec=2.0 + k)
    m = evaluate(results, seeds)["systems"]["M3-B"]["red"]
    assert (m["n_seeds"], m["n_noticed"], m["n_false_alarm"], m["n_correct"]) == (2, 2, 0, 2)
    assert (m["notice_latency_mean"], m["attr_latency_mean"], m["misattr"], m["n_opened"]) == (10.0, 20.0, 0, 2)
    assert (m["n_fits"], m["fit_size"], m["buffer_bytes"], m["total_sec"]) == (7, 300, 1000, 5.0)
    assert m["check_sec_mean"] == pytest.approx(1.5) and m["check_sec_max"] == 2.5
    ev = evaluate(results, seeds)["systems"]
    assert set(ev) == set(SYSTEMS) and all(set(ev[n]) == set(CONDITIONS) for n in SYSTEMS)
    assert ev["M3-B"]["none"]["notice_latency_mean"] is None and ev["M3-B"]["global"]["n_correct"] is None


def test_report_markdown_lists_predictions_numbers_and_costs():
    seeds = list(range(400, 410))
    ev = evaluate([fake_result(s, red_ok=s != 400, global_open=s == 401, ok=s != 409) for s in seeds], seeds)
    md = report_markdown(ev)
    for label in ("P1", "P2", "P3", "P4", "P5", "Abbruchkriterium"):
        assert label in md
    assert "nicht erfüllt" in md and "erfüllt" in md
    assert "409" in md                                          # gescheiterter Seed wird genannt
    for name in SYSTEMS:
        assert name in md
    for word in ("Puffer", "Anpassungen", "Prüfung", "Gesamt"):
        assert word in md
    assert "|" in md and "---" in md


def test_missing_seed_file_names_the_seed(tmp_path):
    for s in (400, 401):
        (tmp_path / f"seed_{s}.json").write_text(json.dumps(fake_result(s)))
    with pytest.raises(FileNotFoundError, match="seed_402"):
        load_results(tmp_path, [400, 401, 402])
    assert [r["seed"] for r in load_results(tmp_path, [400, 401])] == [400, 401]


def test_evaluate_rejects_unlisted_seed():
    with pytest.raises(ValueError, match="402"):
        evaluate([fake_result(400), fake_result(401)], [400, 401, 402])


def test_main_prints_markdown(tmp_path, capsys):
    for s in range(400, 403):
        (tmp_path / f"seed_{s}.json").write_text(json.dumps(fake_result(s)))
    main(["--results", str(tmp_path), "--seeds", "400-402"])
    out = capsys.readouterr().out
    assert "P2" in out and "M3-B" in out
    with pytest.raises(FileNotFoundError, match="seed_403"):
        main(["--results", str(tmp_path), "--seeds", "400-403"])


def test_evaluate_requires_identical_config_and_env():
    seeds = [400, 401, 402]
    env = {"OMP_NUM_THREADS": "1", "numpy": "2.4.0"}

    def results(**changes):
        rs = [{**fake_result(s), "env": dict(env)} for s in seeds]
        for seed, change in changes.items():
            rs[seeds.index(int(seed[1:]))].update(change)
        return rs

    assert evaluate(results(), seeds)["P2"]["count"] == 3
    with pytest.raises(ValueError, match="Konfiguration.*401") as exc:
        evaluate(results(s401={"config": {"switch_episode": 100, "n_deploy_episodes": 300}}), seeds)
    assert "402" not in str(exc.value)
    with pytest.raises(ValueError, match="Umgebung.*402") as exc:
        evaluate(results(s402={"env": {**env, "OMP_NUM_THREADS": "3"}}), seeds)
    assert "401" not in str(exc.value)
    with pytest.raises(ValueError, match="Umgebung.*401.*402"):       # fehlendes "env" zählt als None
        evaluate(results(s401={"env": None}, s402={"env": {"numpy": "9"}}), seeds)
    plain = [fake_result(s) for s in seeds]                           # alle ohne "env": einheitlich None
    assert evaluate(plain, seeds)["P2"]["count"] == 3
    mixed = [fake_result(400), {**fake_result(401), "env": env}, fake_result(402)]
    with pytest.raises(ValueError, match="Umgebung.*401"):
        evaluate(mixed, seeds)


def test_evaluate_compares_only_the_listed_seeds():
    results = [fake_result(s) for s in (400, 401)] + [{**fake_result(999), "env": {"other": 1}}]
    assert evaluate(results, [400, 401])["P2"]["count"] == 2


# --- Review des Nutzers: doppelte Seeds (U1) ---

def test_evaluate_rejects_duplicate_requested_seeds():
    # ein erfolgreiches Ergebnis, zehnmal angefordert, darf nicht als "10/10 Treffer" zählen
    with pytest.raises(ValueError, match="400"):
        evaluate([fake_result(400)], [400] * 10)
    with pytest.raises(ValueError, match="Seeds.*401") as exc:
        evaluate([fake_result(s) for s in (400, 401, 402)], [400, 401, 401, 402])
    assert "400" not in str(exc.value) and "402" not in str(exc.value)     # nur die doppelten werden genannt


def test_evaluate_rejects_several_results_for_one_seed():
    results = [fake_result(400), fake_result(401), fake_result(401, red_ok=False)]
    with pytest.raises(ValueError, match="Ergebnis.*401") as exc:
        evaluate(results, [400, 401])
    assert "400" not in str(exc.value)
    with pytest.raises(ValueError, match="999"):                          # auch für nicht angeforderte Seeds
        evaluate([fake_result(400), fake_result(999), fake_result(999)], [400])


def test_cli_rejects_duplicate_seeds(tmp_path):
    (tmp_path / "seed_400.json").write_text(json.dumps(fake_result(400)))
    with pytest.raises(ValueError, match="400"):
        main(["--results", str(tmp_path), "--seeds", "400,400"])
    with pytest.raises(ValueError, match="400"):                          # auch ohne parse_seeds: load_results + evaluate
        evaluate(load_results(tmp_path, [400, 400]), [400, 400])


# --- Review des Nutzers: vorregistrierte Urteile nur für die Hauptseeds (U2) ---

VERDICTS = (("P2", "fulfilled"), ("P3", "fulfilled"), ("P4", "fulfilled"), ("P5", "fulfilled"), ("abort", "triggered"))


def verdicts(ev):
    return {f"{k}.{f}": ev[k][f] for k, f in VERDICTS}


def test_main_seeds_are_the_preregistered_ten():
    assert MAIN_SEEDS == tuple(range(400, 410))


@pytest.mark.parametrize("seeds", [list(MAIN_SEEDS), list(reversed(MAIN_SEEDS)), [405, 400, 409, 401, 408, 402, 407, 403, 406, 404]])
def test_preregistered_for_exactly_the_main_seeds_in_any_order(seeds):
    ev = evaluate([fake_result(s) for s in seeds], seeds)
    assert ev["preregistered"] is True
    assert all(isinstance(v, bool) for v in verdicts(ev).values())
    assert ev["P2"] == {"count": 10, "fulfilled": True} and ev["abort"]["triggered"] is False


@pytest.mark.parametrize("seeds", [[0], [400], list(range(400, 409)), list(range(401, 411)), list(range(400, 420)),
                                   list(range(399, 410))])
def test_other_seed_sets_are_explorative_with_counts_but_no_verdicts(seeds):
    ev = evaluate([fake_result(s) for s in seeds], seeds)
    assert ev["preregistered"] is False
    assert verdicts(ev) == dict.fromkeys(verdicts(ev))                   # alles None
    assert ev["P2"]["count"] == len(seeds) and ev["P3"]["count"] == len(seeds)
    assert ev["abort"]["red_correct"] == len(seeds) and ev["abort"]["global_open"] == 0
    assert ev["P1"]["ok_seeds"] == sorted(seeds) and ev["systems"]["M3-B"]["red"]["n_seeds"] == len(seeds)
    assert ev["P5"]["M3-B"] == len(seeds) and ev["P4"]["latency_B"] == 20.0


def test_nine_hits_among_twenty_seeds_is_not_a_p2_verdict():
    seeds = list(range(400, 420))
    ev = evaluate([fake_result(s, red_ok=s < 409) for s in seeds], seeds)
    assert ev["P2"] == {"count": 9, "fulfilled": None} and ev["abort"]["triggered"] is None


def test_single_pilot_seed_gets_no_abort_verdict():
    ev = evaluate([fake_result(0)], [0])                              # früher: "Aufbau funktioniert nicht"
    assert ev["abort"] == {"red_correct": 1, "global_open": 0, "triggered": None}


def row(md, label):
    return next(ln for ln in md.splitlines() if ln.startswith(f"| {label}"))


def test_report_marks_explorative_evaluation_and_prints_no_verdicts():
    seeds = [0, 1]
    md = report_markdown(evaluate([fake_result(s, red_ok=s == 0) for s in seeds], seeds))
    assert md.splitlines()[0] == "## Auswertung"
    head = "\n".join(md.splitlines()[:5])                              # gut sichtbar, vor den Tabellen
    assert ("Explorative Auswertung (Seeds 0, 1) – keine Prüfung der vorregistrierten Vorhersagen; "
            "diese gilt nur für die Seeds 400–409.") in head
    for label in ("P2", "P3", "P4", "P5"):
        cells = [c.strip() for c in row(md, label).split("|")]
        assert cells[2] == "–" and "erfüllt" not in cells[2]
    assert "ausgelöst" not in md and "funktioniert nicht" not in md
    assert "1/2 Seeds" in row(md, "P2") and "Abbruchkriterium" in md   # Zahlen bleiben


def test_report_for_main_seeds_keeps_verdicts_and_abort_sentence():
    seeds = list(MAIN_SEEDS)
    md = report_markdown(evaluate([fake_result(s) for s in seeds], seeds))
    assert "Explorative" not in md and "vorregistriert" not in md
    assert "| erfüllt |" in row(md, "P2") and "Abbruchkriterium nicht ausgelöst." in md
    md = report_markdown(evaluate([fake_result(s, red_ok=s < 404) for s in seeds], seeds))
    assert "nicht erfüllt" in row(md, "P2") and "Abbruchkriterium ausgelöst:" in md


def test_main_marks_a_partial_evaluation_as_explorative(tmp_path, capsys):
    for s in (400, 401):
        (tmp_path / f"seed_{s}.json").write_text(json.dumps(fake_result(s)))
    main(["--results", str(tmp_path), "--seeds", "400-401"])
    out = capsys.readouterr().out
    assert "Explorative Auswertung (Seeds 400, 401)" in out and "ausgelöst" not in out
