import dataclasses
import json
import multiprocessing
import os
import pickle
import platform
import re
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import farbversuch.monitor as monitor
import farbversuch.run as run
from farbversuch.run import (CONDITIONS, THREAD_VARS, Prepared, bisect_to_target, deploy, env_block, find_p_global,
                             main, parse_seeds, prepare_seed, result_json, run_seed, stream_episodes)
from farbversuch.tests.helpers import TINY, strip_sec


def test_bisect_hits_target():
    p, ok, _ = bisect_to_target(lambda p: p * p, .25, .1, 1., .02, 30)
    assert ok and abs(p * p - .25) <= .005


def test_bisect_unbracketed():                   # Review Focus 5
    p, ok, n = bisect_to_target(lambda p: p, 5., .1, 1., .02, 30)
    assert (p, ok) == (1., False) and n <= 2


def test_bisect_target_below_range():
    p, ok, n = bisect_to_target(lambda p: p, .01, .1, 1., .02, 30)
    assert (p, ok) == (.1, False) and n == 2


def test_bisect_max_iter_reached():
    calls = []
    def f(p):
        calls.append(p)
        return p * p
    p, ok, n = bisect_to_target(f, .25, .1, 1., 1e-12, 4)
    assert not ok and n == len(calls) == 2 + 4 and .1 < p < 1.


def test_bisect_fallback_is_the_closest_evaluated_point_including_both_ends():
    # Treppenfunktionen: keine Mitte trifft, der Rand mit dem kleinsten Abstand gewinnt
    p, hit, n = bisect_to_target(lambda p: 0. if p < 1. else 1.4, 1., 0., 1., 1e-9, 3)
    assert (p, hit, n) == (1., False, 5)
    p, hit, n = bisect_to_target(lambda p: .9 if p == 0. else 5., 1., 0., 1., 1e-9, 3)
    assert (p, hit, n) == (0., False, 5)


def _fake_p1(curve, red):
    """Phase1-Attrappe: Die Überraschung hängt nur von p_slip (curve) und red_active (red) ab."""
    def surprise(Z, A, D):
        return np.where(Z[:, 1] > 0, red, curve(Z[:, 0]))
    return SimpleNamespace(routine=SimpleNamespace(encode=lambda X: X), forward=SimpleNamespace(surprise=surprise))


@pytest.mark.parametrize("curve, red, changes, expected", [
    (lambda p: p, .5, {}, dict(hit=True, bracketed=True)),                                  # Mitte getroffen
    (lambda p: p, 1., {}, dict(hit=True, bracketed=True, p_global=1.)),                     # oberer Rand getroffen
    (lambda p: p, .1, {}, dict(hit=True, bracketed=True, p_global=.1)),                     # unterer Rand getroffen
    (lambda p: p, 5., {}, dict(hit=False, bracketed=False, p_global=1., evals=1)),          # Ziel oberhalb von f(1)
    (lambda p: p, .01, {}, dict(hit=False, bracketed=False, p_global=.1, evals=2)),         # Ziel unterhalb von f(0,1)
    (lambda p: p, .3, dict(pglobal_tol=1e-9, pglobal_max_iter=3),
     dict(hit=False, bracketed=True, evals=5)),                                             # max_iter erschöpft
    (lambda p: np.where(p < 1., 0., 1.4), 1., dict(pglobal_tol=1e-9, pglobal_max_iter=3),
     dict(hit=False, bracketed=True, p_global=1.)),                                         # Rückfall: oberer Rand
])
def test_find_p_global_reports_hit_and_bracketed_separately(monkeypatch, curve, red, changes, expected):
    def fake_rollouts(routine, seed, tag, n_episodes, cfg, *, p_slip, red_active=False, stream=0):
        traj = SimpleNamespace(obs=np.array([[p_slip, float(red_active)]]), actions=np.array([0]),
                               disps=np.array([0]))
        return [(None, traj)]
    monkeypatch.setattr(run, "routine_rollouts", fake_rollouts)
    r = find_p_global(0, dataclasses.replace(TINY, **changes), _fake_p1(curve, red))
    assert set(r) == {"p_global", "red_surprise", "hit", "bracketed", "evals"}
    assert type(r["hit"]) is bool and type(r["bracketed"]) is bool and r["red_surprise"] == red
    assert {k: r[k] for k in expected} == expected
    assert json.loads(json.dumps(r)) == r


def test_parse_seeds():
    assert parse_seeds("400-402") == [400, 401, 402] and parse_seeds("0") == [0] and parse_seeds("1,5") == [1, 5]


def test_parse_seeds_mixed_and_invalid():
    assert parse_seeds("1-2,7") == [1, 2, 7]
    with pytest.raises(ValueError):
        parse_seeds("5-3")


@pytest.mark.parametrize("spec, dup", [("1,1", "[1]"), ("1-3,2", "[2]"), ("400-402,401,402", "[401, 402]"),
                                       ("7,3,7,3", "[3, 7]")])
def test_parse_seeds_rejects_duplicates_and_names_them(spec, dup):
    with pytest.raises(ValueError, match="doppelte Seeds") as exc:
        parse_seeds(spec)
    assert dup in str(exc.value)


def test_parse_seeds_unique_mixed_specs_still_work():
    assert parse_seeds("3,1-2") == [3, 1, 2] and parse_seeds("1-2,4-5") == [1, 2, 4, 5]


def test_cli_rejects_duplicate_seeds_before_running_anything(tmp_path, monkeypatch):
    monkeypatch.setattr(run.multiprocessing, "get_context", lambda *a: pytest.fail("kein Worker darf starten"))
    with pytest.raises(ValueError, match="doppelte Seeds.*1"):
        main(["--seeds", "1,1", "--out", str(tmp_path / "o")])
    assert not list((tmp_path / "o").glob("*"))


def test_atomic_write_temp_file_name_includes_the_process_id(tmp_path, monkeypatch):
    seen = []
    real_replace = os.replace
    monkeypatch.setattr(os, "replace", lambda src, dst: (seen.append(os.path.basename(src)), real_replace(src, dst)))
    for pid in (1111, 2222):                      # zwei Prozesse mit demselben Ziel kollidieren nicht auf einer Datei
        monkeypatch.setattr(os, "getpid", lambda pid=pid: pid)
        run._write_atomic(tmp_path / "seed_5.json", json.dumps({"seed": 5}))
    run._write_atomic(tmp_path / "x.bin", b"\x00\x01")
    assert seen == ["seed_5.json.1111.tmp", "seed_5.json.2222.tmp", "x.bin.2222.tmp"]
    assert sorted(x.name for x in tmp_path.iterdir()) == ["seed_5.json", "x.bin"]          # nichts bleibt liegen
    assert json.loads((tmp_path / "seed_5.json").read_text()) == {"seed": 5}
    assert (tmp_path / "x.bin").read_bytes() == b"\x00\x01"


@pytest.mark.slow
def test_streams_share_maps_before_switch(tiny_phase1):
    s = {c: list(stream_episodes(0, TINY, tiny_phase1, .4, c)) for c in ("none", "red")}
    sw = TINY.switch_episode
    assert all(np.array_equal(a.positions, b.positions) for a, b in zip(s["none"][:sw], s["red"][:sw]))
    assert any((t.disps >= 5).any() for t in s["red"][sw:]) and not any((t.disps >= 5).any() for t in s["none"])


@pytest.mark.slow
def test_find_p_global_plain_and_reproducible(tiny_phase1):
    a = find_p_global(0, TINY, tiny_phase1)
    assert a == find_p_global(0, TINY, tiny_phase1)
    assert set(a) == {"p_global", "red_surprise", "hit", "bracketed", "evals"}
    assert type(a["p_global"]) is float and type(a["red_surprise"]) is float
    assert type(a["hit"]) is bool and type(a["bracketed"]) is bool and type(a["evals"]) is int
    assert TINY.p_slip <= a["p_global"] <= 1. and 2 <= a["evals"] <= 2 + TINY.pglobal_max_iter
    assert json.loads(json.dumps(a)) == a


@pytest.mark.slow
def test_deploy_hands_ontology_and_configured_permutations_to_the_monitor(monkeypatch, tiny_phase1):
    seen = []
    monkeypatch.setattr(monitor, "s1_explain", lambda S, F, opened, rng, n_perm, alpha, max_new, chunk:
                        seen.append((F.shape[1], list(opened), n_perm, alpha, max_new, chunk)) or [])
    cfg = dataclasses.replace(TINY, n_perm=123, n_perm_A=77, perm_chunk=50, alpha=.01, n_deploy_episodes=10)
    practice = {**tiny_phase1.practice, "S1-B": [1, 4], "S1-A": [7, 300]}
    p1 = dataclasses.replace(tiny_phase1, cusum_h=-1., practice=practice)    # S1 bemerkt sofort; Prüfpunkt bei E = 10
    r = deploy(0, cfg, p1, .4, "none")
    assert sorted(seen) == [(6, [1, 4], 123, .01, cfg.max_open, 50), (1192, [7, 300], 77, .01, cfg.max_open, 50)]
    assert r["M3-B"]["delta"] == p1.deltas["M3-B"] and r["S1-B"]["delta"] is None
    assert r["S1-A"]["practice"] == [{"cand": 7, "name": monitor.candidate_name("A", 7)},
                                     {"cand": 300, "name": monitor.candidate_name("A", 300)}]


@pytest.mark.slow
def test_deploy_reproducible_and_complete(tiny_phase1):
    def strip(r):                                # Wandzeiten dürfen abweichen
        return {k: {kk: vv for kk, vv in v.items() if not kk.endswith("_sec")} for k, v in r.items()}
    a = deploy(0, TINY, tiny_phase1, .4, "global")
    assert set(a) == set(TINY.systems)
    assert strip(a) == strip(deploy(0, TINY, tiny_phase1, .4, "global"))


def test_env_block_is_plain_and_reflects_the_environment(monkeypatch):
    monkeypatch.setenv("OMP_NUM_THREADS", "1")
    monkeypatch.setenv("OPENBLAS_NUM_THREADS", "3")
    monkeypatch.delenv("MKL_NUM_THREADS", raising=False)
    env = env_block()
    assert set(env) == {*THREAD_VARS, "numpy", "blas", "python"}
    assert (env["OMP_NUM_THREADS"], env["OPENBLAS_NUM_THREADS"], env["MKL_NUM_THREADS"]) == ("1", "3", None)
    assert env["numpy"] == np.__version__ and env["python"] == platform.python_version()
    assert env["blas"] is None or (type(env["blas"]) is str and env["blas"])
    assert json.loads(json.dumps(env)) == env


@pytest.mark.slow
def test_run_seed_schema():
    r = run_seed(0, TINY)
    assert set(r["conditions"]) == set(CONDITIONS) and set(r["conditions"]["red"]) == set(TINY.systems)
    assert set(r["env"]) == {*THREAD_VARS, "numpy", "blas", "python"}
    assert json.loads(json.dumps(r)) == r


@pytest.mark.slow
def test_run_seed_v2_schema():
    r = run_seed(0, TINY)
    assert set(r["practice"]) == set(TINY.systems) and set(r["delta"]) == {"M3-B"}
    assert {"practice", "delta"} <= set(r["conditions"]["red"]["M3-B"]) and json.loads(json.dumps(r)) == r
    assert {"restanteil", "shift"} <= set(r["premise"])
    for name, cands in r["practice"].items():
        assert all(set(c) == {"cand", "name"} for c in cands)
        assert r["conditions"]["red"][name]["practice"] == cands
    assert all(type(d) is float and d >= 0 for d in r["delta"].values())
    red = r["conditions"]["red"]
    assert red["M3-B"]["delta"] == r["delta"]["M3-B"] and red["S1-B"]["delta"] is None


@pytest.mark.slow
def test_non_finite_p1b_values_become_null_in_the_result(monkeypatch, tiny_phase1):
    # JSON hat kein NaN: nicht endliche Restanteil-/Verschiebungswerte stehen als null im Ergebnis
    monkeypatch.setattr(run, "phase1", lambda seed, cfg: tiny_phase1)
    monkeypatch.setattr(run, "premise_checks", lambda seed, cfg, p1: {
        "ok": False, "color_invariance": 1., "fwd_surprise": 1., "freq_surprise": 2.,
        "restanteil": float("nan"), "shift": float("inf")})
    r = run_seed(0, TINY)
    assert r["premise"]["restanteil"] is None and r["premise"]["shift"] is None and r["premise"]["ok"] is False
    assert r["conditions"] is None and json.loads(json.dumps(r, allow_nan=False)) == r


@pytest.mark.slow
def test_run_seed_content():
    r = run_seed(0, TINY)
    assert list(r) == ["seed", "config", "env", "premise", "calibration", "practice", "delta", "p_global",
                       "conditions", "phase1_sec", "total_sec"]
    assert r["seed"] == 0 and r["config"] == TINY.as_dict() and r["premise"]["ok"] is True
    assert set(r["calibration"]) == {"m3_threshold", "cusum_k", "cusum_h"}
    assert set(r["p_global"]) == {"p_global", "red_surprise", "hit", "bracketed", "evals"}
    assert 0 < r["phase1_sec"] <= r["total_sec"]


@pytest.mark.slow
def test_premise_failure_stops_seed(capsys):
    r = run_seed(0, dataclasses.replace(TINY, min_invariance=1.01))
    assert r["premise"]["ok"] is False and r["conditions"] is None and r["p_global"] is None
    lines = capsys.readouterr().err.splitlines()
    assert len(lines) == 2 and "Prämisse nicht erfüllt" in lines[1]          # keine Bedingungszeilen


@pytest.mark.slow
def test_run_seed_logs_progress_to_stderr(capsys):
    r = run_seed(3, TINY)
    cap = capsys.readouterr()
    lines = cap.err.splitlines()
    assert cap.out == "" and all(re.match(r"\d\d:\d\d:\d\d seed 3 ", ln) for ln in lines)
    assert len(lines) == 2 + len(CONDITIONS)
    assert "gestartet" in lines[0]
    assert "Phase 1 fertig" in lines[1] and "Prämisse ok" in lines[1]
    for cond, ln in zip(CONDITIONS, lines[2:]):
        assert re.search(rf"Bedingung {cond} fertig \(\d+ s", ln)
    assert set(r["conditions"]) == set(CONDITIONS)                            # Ergebnis unverändert


@pytest.mark.slow
def test_cli_writes_and_skips(tmp_path):
    cfg = tmp_path / "c.json"; TINY.to_json(cfg)
    args = ["--config", str(cfg), "--seeds", "0", "--out", str(tmp_path / "o")]
    main(args); f = tmp_path / "o" / "seed_0.json"; t = f.stat().st_mtime_ns
    main(args); assert f.stat().st_mtime_ns == t


def _seed_file(out, seed, config):
    out.mkdir(exist_ok=True)
    f = out / f"seed_{seed}.json"
    f.write_text(json.dumps({"seed": seed, "config": config}))
    return f, (f.read_bytes(), f.stat().st_mtime_ns)


@pytest.mark.parametrize("config", [{**TINY.as_dict(), "k": 99}, None])      # andere Konfiguration / keine
def test_resume_refuses_foreign_config_and_leaves_the_file_alone(tmp_path, config):
    f, before = _seed_file(tmp_path / "o", 0, config)
    cfg = tmp_path / "c.json"; TINY.to_json(cfg)
    with pytest.raises(SystemExit, match="seed_0.json"):
        main(["--config", str(cfg), "--seeds", "0-1", "--out", str(tmp_path / "o")])
    assert (f.read_bytes(), f.stat().st_mtime_ns) == before
    assert sorted(x.name for x in (tmp_path / "o").iterdir()) == ["seed_0.json"]     # Seed 1 wurde nicht gestartet


def test_resume_skips_matching_seed_with_a_message(tmp_path, capsys):
    f, before = _seed_file(tmp_path / "o", 0, TINY.as_dict())
    cfg = tmp_path / "c.json"; TINY.to_json(cfg)
    main(["--config", str(cfg), "--seeds", "0", "--out", str(tmp_path / "o")])
    cap = capsys.readouterr()
    assert "seed 0 übersprungen (vorhanden)" in cap.err and "seed 0" not in cap.out
    assert (f.read_bytes(), f.stat().st_mtime_ns) == before


@pytest.mark.slow
def test_cli_pins_blas_threads_even_with_one_job(tmp_path, monkeypatch):
    for k in THREAD_VARS:
        monkeypatch.setenv(k, "8")               # monkeypatch stellt nach dem Test wieder her
    cfg = tmp_path / "c.json"; TINY.to_json(cfg)
    main(["--config", str(cfg), "--seeds", "0", "--out", str(tmp_path / "o")])
    r = json.loads((tmp_path / "o" / "seed_0.json").read_text())
    assert [os.environ[k] for k in THREAD_VARS] == ["1"] * 3
    assert [r["env"][k] for k in THREAD_VARS] == ["1"] * 3          # so gesehen im Worker


@pytest.mark.slow
def test_cli_parallel_matches_serial(tmp_path, monkeypatch):
    for k in THREAD_VARS:
        monkeypatch.setenv(k, "8")
    cfg = tmp_path / "c.json"; TINY.to_json(cfg)
    base = ["--config", str(cfg)]
    main([*base, "--seeds", "0-1", "--out", str(tmp_path / "par"), "--jobs", "2"])
    assert (tmp_path / "par" / "seed_0.json").exists()
    main([*base, "--seeds", "1", "--out", str(tmp_path / "ser")])    # --jobs 1: ebenfalls im festgelegten Worker

    def strip(x):
        return {k: strip(v) for k, v in x.items() if not k.endswith("_sec")} if isinstance(x, dict) else x
    par, ser = (json.loads((tmp_path / d / "seed_1.json").read_text()) for d in ("par", "ser"))
    assert strip(par) == strip(ser)


def _in_fresh_process(monkeypatch, fn, *args):
    """fn(*args) in einem frischen Prozess mit festen BLAS-Threads, wie die Worker von main. Im Testprozess ist numpy
    schon geladen, seine Threadzahl lässt sich nicht mehr ändern und verschiebt die Gleitkommareihenfolge (Abweichung
    ab der sechsten Stelle); ein Vergleich mit Rechnung im Testprozess hinge von dessen Threads ab."""
    for k in THREAD_VARS:
        monkeypatch.setenv(k, "1")
    with multiprocessing.get_context("spawn").Pool(1) as pool:
        return pool.apply(fn, args)


def _sequential_reference(seed, cfg, monkeypatch):
    return json.loads(json.dumps(_in_fresh_process(monkeypatch, run_seed, seed, cfg)))


@pytest.mark.slow
def test_staged_equals_sequential(tmp_path, monkeypatch):
    cfg = tmp_path / "c.json"; TINY.to_json(cfg)
    main(["--config", str(cfg), "--seeds", "0", "--out", str(tmp_path / "o"), "--jobs", "3"])
    staged = json.loads((tmp_path / "o" / "seed_0.json").read_text())
    assert strip_sec(staged) == strip_sec(_sequential_reference(0, TINY, monkeypatch))
    assert not any((tmp_path / "o" / ".work").glob("seed_0.*"))


@pytest.mark.slow
def test_staged_premise_failure(tmp_path):                     # Review Focus 5
    cfg = tmp_path / "c.json"; dataclasses.replace(TINY, min_invariance=1.01).to_json(cfg)
    main(["--config", str(cfg), "--seeds", "0", "--out", str(tmp_path / "o"), "--jobs", "2"])
    r = json.loads((tmp_path / "o" / "seed_0.json").read_text())
    assert r["premise"]["ok"] is False and r["conditions"] is None
    assert r["p_global"] is None and not any((tmp_path / "o" / ".work").glob("seed_0.*"))


@pytest.mark.slow
def test_stale_prep_is_not_reused(tmp_path):                    # Review Focus 4
    work = tmp_path / "o" / ".work"; work.mkdir(parents=True)
    stale = prepare_seed(0, dataclasses.replace(TINY, epochs=5))
    (work / "seed_0.prep.pkl").write_bytes(pickle.dumps(stale))
    cfg = tmp_path / "c.json"; TINY.to_json(cfg)
    main(["--config", str(cfg), "--seeds", "0", "--out", str(tmp_path / "o"), "--jobs", "2"])
    assert json.loads((tmp_path / "o" / "seed_0.json").read_text())["config"] == TINY.as_dict()


@pytest.mark.slow
def test_staged_run_resumes_from_partial_work_files(tmp_path, monkeypatch):
    out = tmp_path / "o"; (out / ".work").mkdir(parents=True)
    # Stufe 1 und ein Teil von Stufe 2 liegen schon da
    assert _in_fresh_process(monkeypatch, run._prepare_job, (0, TINY, str(out))) == (0, True)
    _in_fresh_process(monkeypatch, run._deploy_job, (0, TINY, str(out), "red"))
    assert sorted(x.name for x in (out / ".work").iterdir()) == ["seed_0.prep.pkl", "seed_0.red.json"]
    cfg = tmp_path / "c.json"; TINY.to_json(cfg)
    main(["--config", str(cfg), "--seeds", "0", "--out", str(out), "--jobs", "2"])
    staged = json.loads((out / "seed_0.json").read_text())
    assert strip_sec(staged) == strip_sec(_sequential_reference(0, TINY, monkeypatch))
    assert not any((out / ".work").glob("seed_0.*"))


def _stub_prep(cfg=TINY, ok=True, seed=0, fingerprint=None):
    """Prepared mit Attrappen, die sich pickeln lassen (SimpleNamespace statt echter Phase 1); Herkunft: jetzt."""
    p1 = SimpleNamespace(m3_threshold=1., cusum_k=2., cusum_h=3., practice={"M3-B": [1, 4]}, deltas={"M3-B": .5},
                         sec=2.)
    premise = {"ok": ok, "color_invariance": 1., "fwd_surprise": 1., "freq_surprise": 2.,
               "restanteil": float("nan"), "shift": .1}
    return Prepared(seed=seed, config=cfg.as_dict(), fingerprint=fingerprint or run.fingerprint(), p1=p1,
                    premise=premise, p_global={"p_global": .4} if ok else None, sec=3.)


def test_total_sec_is_preparation_plus_the_condition_times():       # Festlegung 9
    prep = _stub_prep()
    r = result_json(prep, {"none": {}, "red": {}}, {"none": 1.5, "red": 2.})
    assert r["total_sec"] == prep.sec + 3.5 and r["phase1_sec"] == prep.p1.sec
    assert r["premise"]["restanteil"] is None and r["premise"]["shift"] == .1       # nan wird zu null
    assert r["practice"]["M3-B"][0]["cand"] == 1 and r["delta"] == {"M3-B": .5}
    failed = result_json(_stub_prep(ok=False), None, {})
    assert failed["conditions"] is None and failed["p_global"] is None and failed["total_sec"] == 3.
    assert json.loads(json.dumps(r, allow_nan=False)) == r


def test_prepare_job_reuses_a_pickle_with_the_same_config(tmp_path, monkeypatch):
    work = tmp_path / ".work"; work.mkdir()
    f = work / "seed_0.prep.pkl"; f.write_bytes(pickle.dumps(_stub_prep()))
    before = (f.read_bytes(), f.stat().st_mtime_ns)
    monkeypatch.setattr(run, "prepare_seed", lambda seed, cfg: pytest.fail("darf nicht neu rechnen"))
    assert run._prepare_job((0, TINY, str(tmp_path))) == (0, True)
    assert (f.read_bytes(), f.stat().st_mtime_ns) == before


def test_prepare_job_recomputes_a_pickle_with_another_config(tmp_path, monkeypatch):
    work = tmp_path / ".work"; work.mkdir()
    f = work / "seed_0.prep.pkl"; f.write_bytes(pickle.dumps(_stub_prep(dataclasses.replace(TINY, epochs=5))))
    monkeypatch.setattr(run, "prepare_seed", lambda seed, cfg: _stub_prep(cfg, ok=False, seed=seed))
    assert run._prepare_job((0, TINY, str(tmp_path))) == (0, False)
    assert pickle.loads(f.read_bytes()).config == TINY.as_dict()
    assert sorted(x.name for x in work.iterdir()) == ["seed_0.prep.pkl"]          # keine Temp-Datei übrig


def test_prepare_job_recomputes_a_pickle_from_other_code_or_environment(tmp_path, monkeypatch):
    work = tmp_path / ".work"; work.mkdir()
    f = work / "seed_0.prep.pkl"; f.write_bytes(pickle.dumps(_stub_prep(fingerprint="0" * 64)))   # gleiche Konfiguration
    calls = []
    monkeypatch.setattr(run, "prepare_seed", lambda seed, cfg: calls.append(seed) or _stub_prep(cfg, seed=seed))
    assert run._prepare_job((0, TINY, str(tmp_path))) == (0, True)
    assert calls == [0] and pickle.loads(f.read_bytes()).fingerprint == run.fingerprint()
    run._prepare_job((0, TINY, str(tmp_path)))                       # jetzt passt die Herkunft: kein zweites Mal
    assert calls == [0]


def test_prepare_job_recomputes_a_pickle_without_a_fingerprint(tmp_path, monkeypatch):
    work = tmp_path / ".work"; work.mkdir()
    old = _stub_prep(); del old.fingerprint                                   # Pickle aus der Zeit vor dem Fingerabdruck
    (work / "seed_0.prep.pkl").write_bytes(pickle.dumps(old))
    calls = []
    monkeypatch.setattr(run, "prepare_seed", lambda seed, cfg: calls.append(seed) or _stub_prep(cfg, seed=seed))
    run._prepare_job((0, TINY, str(tmp_path)))
    assert calls == [0]


def test_prepare_seed_stores_the_current_fingerprint(monkeypatch):
    monkeypatch.setattr(run, "phase1", lambda seed, cfg: SimpleNamespace(sec=1.))
    monkeypatch.setattr(run, "premise_checks", lambda seed, cfg, p1: {"ok": False})
    assert prepare_seed(0, TINY).fingerprint == run.fingerprint()


def test_fingerprint_follows_source_and_environment_but_not_tests(tmp_path, monkeypatch):
    src = tmp_path / "farbversuch"; (src / "tests").mkdir(parents=True)
    (src / "a.py").write_text("x = 1\n"); (src / "b.py").write_text("y = 2\n")
    (src / "tests" / "t.py").write_text("t = 0\n")
    monkeypatch.setattr(run, "_SRC_DIR", src)
    monkeypatch.setenv("OMP_NUM_THREADS", "1")
    base = run.fingerprint()
    assert re.fullmatch(r"[0-9a-f]{64}", base) and run.fingerprint() == base
    (src / "tests" / "t.py").write_text("t = 5\n")                           # Tests gehören nicht zur Herkunft
    assert run.fingerprint() == base
    (src / "b.py").write_text("y = 3\n")                                     # Quelltext
    changed = run.fingerprint()
    assert changed != base
    monkeypatch.setenv("OMP_NUM_THREADS", "2")                               # Umgebung
    assert run.fingerprint() not in (base, changed)


def test_fingerprint_covers_the_package_sources():
    assert run._SRC_DIR == Path(run.__file__).resolve().parent and (run._SRC_DIR / "run.py").exists()


def test_prepare_job_creates_the_work_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "prepare_seed", lambda seed, cfg: _stub_prep(cfg, seed=seed))
    assert run._prepare_job((0, TINY, str(tmp_path / "o"))) == (0, True)
    assert (tmp_path / "o" / ".work" / "seed_0.prep.pkl").exists()


def _cond_file(config=None, fingerprint="current", sec=7.):
    """Inhalt einer Bedingungsdatei; fingerprint "current" = Herkunft dieses Prozesses, None = Schlüssel fehlt."""
    d = {"config": config or TINY.as_dict(), "result": {"kept": 1}, "sec": sec}
    if fingerprint is not None:
        d["fingerprint"] = run.fingerprint() if fingerprint == "current" else fingerprint
    return d


def test_deploy_job_reuses_a_condition_file_with_the_same_config_and_origin_only(tmp_path, monkeypatch):
    work = tmp_path / ".work"; work.mkdir()
    f = work / "seed_0.red.json"
    monkeypatch.setattr(run, "deploy",
                        lambda seed, cfg, p1, p_global, condition: {"fresh": [seed, p_global, condition]})
    f.write_text(json.dumps(_cond_file()))
    run._deploy_job((0, TINY, str(tmp_path), "red"))              # ohne Prep-Pickle: sie wird nicht einmal geladen
    assert json.loads(f.read_text()) == _cond_file()
    f.write_text(json.dumps(_cond_file({**TINY.as_dict(), "k": 99})))
    (work / "seed_0.prep.pkl").write_bytes(pickle.dumps(_stub_prep()))
    run._deploy_job((0, TINY, str(tmp_path), "red"))
    got = json.loads(f.read_text())
    assert got["config"] == TINY.as_dict() and got["result"] == {"fresh": [0, .4, "red"]} and got["sec"] >= 0
    assert got["fingerprint"] == run.fingerprint()
    assert sorted(x.name for x in work.iterdir()) == ["seed_0.prep.pkl", "seed_0.red.json"]


@pytest.mark.parametrize("fingerprint", ["0" * 64, None])     # anderer Code/andere Umgebung / Datei ohne Fingerabdruck
def test_deploy_job_recomputes_a_condition_file_from_other_code_or_environment(tmp_path, monkeypatch, fingerprint):
    work = tmp_path / ".work"; work.mkdir()
    (work / "seed_0.prep.pkl").write_bytes(pickle.dumps(_stub_prep()))
    f = work / "seed_0.red.json"; f.write_text(json.dumps(_cond_file(fingerprint=fingerprint)))   # gleiche Konfiguration
    monkeypatch.setattr(run, "deploy",
                        lambda seed, cfg, p1, p_global, condition: {"fresh": [seed, p_global, condition]})
    run._deploy_job((0, TINY, str(tmp_path), "red"))
    got = json.loads(f.read_text())
    assert got["result"] == {"fresh": [0, .4, "red"]} and got["fingerprint"] == run.fingerprint()
    assert sorted(x.name for x in work.iterdir()) == ["seed_0.prep.pkl", "seed_0.red.json"]


def test_finish_job_writes_the_result_and_removes_only_this_seeds_work_files(tmp_path):
    work = tmp_path / ".work"; work.mkdir()
    (work / "seed_0.prep.pkl").write_bytes(pickle.dumps(_stub_prep()))
    for c, sec in zip(reversed(CONDITIONS), (1., 2., 3., 4.)):
        (work / f"seed_0.{c}.json").write_text(json.dumps({"config": TINY.as_dict(), "result": {"c": c}, "sec": sec}))
    (work / "seed_0.prep.pkl.99.tmp").write_bytes(b"")                       # liegengebliebene Temp-Datei
    others = ["seed_10.prep.pkl", "seed_1.prep.pkl", "seed_10.red.json"]
    for name in others:
        (work / name).write_bytes(b"")
    assert run._finish_job((0, TINY, str(tmp_path))) == 0
    r = json.loads((tmp_path / "seed_0.json").read_text())
    assert list(r["conditions"]) == list(CONDITIONS) and r["conditions"]["red"] == {"c": "red"}
    assert r["total_sec"] == 3. + 10.
    assert sorted(x.name for x in work.iterdir()) == sorted(others)
    assert sorted(x.name for x in tmp_path.iterdir() if x.name != ".work") == ["seed_0.json"]


def test_finish_job_without_conditions_for_a_failed_premise(tmp_path):
    work = tmp_path / ".work"; work.mkdir()
    (work / "seed_0.prep.pkl").write_bytes(pickle.dumps(_stub_prep(ok=False)))
    run._finish_job((0, TINY, str(tmp_path)))
    r = json.loads((tmp_path / "seed_0.json").read_text())
    assert r["conditions"] is None and r["p_global"] is None and r["total_sec"] == 3.
    assert list(work.iterdir()) == []


def test_main_runs_no_pool_when_every_seed_is_done(tmp_path, monkeypatch):
    _seed_file(tmp_path / "o", 0, TINY.as_dict())
    cfg = tmp_path / "c.json"; TINY.to_json(cfg)
    monkeypatch.setattr(run.multiprocessing, "get_context", lambda *a: pytest.fail("kein Pool nötig"))
    main(["--config", str(cfg), "--seeds", "0", "--out", str(tmp_path / "o")])
    assert sorted(x.name for x in (tmp_path / "o").iterdir()) == ["seed_0.json"]


@pytest.mark.parametrize("contents", [b"", b"broken pickle", pickle.dumps({}), pickle.dumps(None)])
def test_prepare_job_recomputes_unusable_intermediate_files(tmp_path, monkeypatch, contents):
    work = tmp_path / ".work"
    work.mkdir()
    path = work / "seed_0.prep.pkl"
    path.write_bytes(contents)
    calls = []
    monkeypatch.setattr(run, "prepare_seed", lambda seed, cfg: calls.append(seed) or _stub_prep(cfg, seed=seed))
    assert run._prepare_job((0, TINY, str(tmp_path))) == (0, True)
    assert calls == [0] and isinstance(pickle.loads(path.read_bytes()), Prepared)


@pytest.mark.parametrize("contents", [b"", b'{"config":', b"\xff", b"[]", b"null"])
def test_deploy_job_recomputes_unusable_intermediate_files(tmp_path, monkeypatch, contents):
    work = tmp_path / ".work"
    work.mkdir()
    (work / "seed_0.prep.pkl").write_bytes(pickle.dumps(_stub_prep()))
    path = work / "seed_0.red.json"
    path.write_bytes(contents)
    calls = []
    monkeypatch.setattr(run, "deploy", lambda seed, cfg, p1, pg, condition: calls.append(condition) or {"fresh": True})
    run._deploy_job((0, TINY, str(tmp_path), "red"))
    assert calls == ["red"] and json.loads(path.read_text())["result"] == {"fresh": True}


@pytest.mark.parametrize("missing", ["result", "sec"])
def test_deploy_job_recomputes_incomplete_intermediate_files(tmp_path, monkeypatch, missing):
    stored = _cond_file()
    del stored[missing]
    test_deploy_job_recomputes_unusable_intermediate_files(tmp_path, monkeypatch, json.dumps(stored).encode())


def test_intermediate_recovery_still_propagates_calculation_errors(tmp_path, monkeypatch):
    work = tmp_path / ".work"
    work.mkdir()
    path = work / "seed_0.prep.pkl"
    path.write_bytes(b"broken pickle")

    def fail(seed, cfg):
        raise RuntimeError("Berechnung fehlgeschlagen")

    monkeypatch.setattr(run, "prepare_seed", fail)
    with pytest.raises(RuntimeError, match="Berechnung fehlgeschlagen"):
        run._prepare_job((0, TINY, str(tmp_path)))
    assert path.read_bytes() == b"broken pickle"
