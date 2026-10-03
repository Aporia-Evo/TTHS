import re

import pytest

from farbversuch.config import Config
from farbversuch.freeze import main, source_files, verify_freeze, write_freeze


def tree(tmp_path):
    (tmp_path / "farbversuch" / "tests").mkdir(parents=True)
    for p in ("farbversuch/a.py", "farbversuch/tests/t.py", "requirements.txt", "pytest.ini"):
        (tmp_path / p).write_text(p)
    return tmp_path


def test_write_then_verify_clean(tmp_path):
    root = tree(tmp_path); write_freeze(root, Config(epochs=3))
    assert verify_freeze(root) == [] and Config.from_json(root / "farbversuch" / "frozen_config.json") == Config(epochs=3)


def test_verify_reports_change(tmp_path):
    root = tree(tmp_path); write_freeze(root, Config()); (root / "farbversuch" / "a.py").write_text("x")
    assert verify_freeze(root) == ["farbversuch/a.py"]


def test_sha256sum_format(tmp_path):
    root = tree(tmp_path); write_freeze(root, Config())
    lines = (root / "farbversuch" / "freeze.sha256").read_text().splitlines()
    assert len(lines) == 5 and all(re.fullmatch(r"[0-9a-f]{64}  \S+", l) for l in lines)


def test_source_files_sorted_relative_without_pycache(tmp_path):
    root = tree(tmp_path)
    (root / "farbversuch" / "__pycache__").mkdir()
    (root / "farbversuch" / "__pycache__" / "a.cpython-311.py").write_text("x")
    (root / "farbversuch" / "notes.txt").write_text("x")
    names = [p.as_posix() for p in source_files(root)]
    assert names == ["farbversuch/a.py", "farbversuch/tests/t.py", "pytest.ini", "requirements.txt"]


def test_freeze_files_cover_frozen_config_and_stay_stable(tmp_path):
    root = tree(tmp_path); write_freeze(root, Config())
    lines = (root / "farbversuch" / "freeze.sha256").read_text().splitlines()
    paths = [l.split("  ", 1)[1] for l in lines]
    assert paths == sorted(paths) and "farbversuch/frozen_config.json" in paths
    assert "farbversuch/freeze.sha256" not in paths
    write_freeze(root, Config())  # erneutes Schreiben ändert die Quelldateien nicht
    assert verify_freeze(root) == []


def test_verify_reports_missing_and_changed_config(tmp_path):
    root = tree(tmp_path); write_freeze(root, Config())
    (root / "pytest.ini").unlink()
    (root / "farbversuch" / "frozen_config.json").write_text("{}\n")
    assert verify_freeze(root) == ["farbversuch/frozen_config.json", "pytest.ini"]


SUMS = "farbversuch/freeze.sha256"


def test_verify_reports_py_files_added_after_freezing(tmp_path):
    root = tree(tmp_path); write_freeze(root, Config())
    (root / "farbversuch" / "x.py").write_text("x")                      # Python könnte dies statt des Eingefrorenen laden
    (root / "y.py").write_text("y")                                      # Wurzel: `python -m` legt das Arbeitsverzeichnis auf sys.path
    (root / "farbversuch" / "tests" / "deep" / "er").mkdir(parents=True)
    (root / "farbversuch" / "tests" / "deep" / "er" / "z.py").write_text("z")
    assert verify_freeze(root) == ["farbversuch/tests/deep/er/z.py", "farbversuch/x.py", "y.py"]


def test_verify_ignores_hidden_dirs_pycache_and_non_python_files(tmp_path):
    root = tree(tmp_path); write_freeze(root, Config())
    for d in (".superpowers/sdd", ".git/hooks", ".pytest_cache", "farbversuch/.cache", "farbversuch/tests/__pycache__",
              "__pycache__"):
        (root / d).mkdir(parents=True)
        (root / d / "ignored.py").write_text("x")
    (root / "farbversuch" / "notes.txt").write_text("x")
    (root / "farbversuch" / "results").mkdir()
    (root / "farbversuch" / "results" / "seed_0.json").write_text("{}")
    assert verify_freeze(root) == []


def test_verify_untouched_tree_is_clean(tmp_path):
    root = tree(tmp_path); write_freeze(root, Config())
    assert verify_freeze(root) == []


def test_source_files_recursive_from_root_without_hidden_and_pycache(tmp_path):
    root = tree(tmp_path)
    (root / "y.py").write_text("y")
    (root / "tools" / "sub").mkdir(parents=True)
    (root / "tools" / "sub" / "w.py").write_text("w")
    for d in (".superpowers", ".git/hooks", "farbversuch/tests/__pycache__", "tools/.venv"):
        (root / d).mkdir(parents=True, exist_ok=True)
        (root / d / "ignored.py").write_text("x")
    (root / "tools" / "readme.md").write_text("x")
    names = [p.as_posix() for p in source_files(root)]
    assert names == ["farbversuch/a.py", "farbversuch/tests/t.py", "pytest.ini", "requirements.txt", "tools/sub/w.py", "y.py"]


def test_source_files_judges_only_the_path_below_the_root(tmp_path):       # Repo darf unter einem Punkt-Ordner liegen
    base = tmp_path / ".hidden_parent" / "repo"; base.mkdir(parents=True)
    root = tree(base)
    assert [p.as_posix() for p in source_files(root)] == ["farbversuch/a.py", "farbversuch/tests/t.py", "pytest.ini", "requirements.txt"]


def test_verify_fails_closed_on_missing_sums_file(tmp_path):
    root = tree(tmp_path)
    assert verify_freeze(root) == [SUMS]


def test_verify_fails_closed_on_empty_sums_file(tmp_path):
    root = tree(tmp_path); write_freeze(root, Config())
    (root / SUMS).write_text("")
    assert verify_freeze(root) == [SUMS]
    (root / SUMS).write_text("\n  \n")                                   # nur Leerzeilen: auch keine Einträge
    assert verify_freeze(root) == [SUMS]


GOOD = "0" * 64


@pytest.mark.parametrize("bad_line", [
    "garbage",
    f"{GOOD[:-1]}  farbversuch/a.py",              # Hash zu kurz
    f"{GOOD} farbversuch/a.py",                    # nur ein Leerzeichen
    f"{GOOD.replace('0', 'G')}  farbversuch/a.py", # kein Hex
    f"{GOOD}  ",                                   # kein Pfad
])
def test_verify_fails_closed_on_malformed_line_without_traceback(tmp_path, bad_line):
    root = tree(tmp_path); write_freeze(root, Config())
    (root / SUMS).write_text((root / SUMS).read_text() + bad_line + "\n")
    assert SUMS in verify_freeze(root)
    (root / SUMS).write_text(bad_line + "\n")
    assert SUMS in verify_freeze(root)


def test_verify_fails_closed_on_undecodable_or_directory_sums_file(tmp_path):
    root = tree(tmp_path); write_freeze(root, Config())
    (root / SUMS).write_bytes(b"\xff\xfe\x00garbage")
    assert verify_freeze(root) == [SUMS]
    (root / SUMS).unlink(); (root / SUMS).mkdir()
    assert verify_freeze(root) == [SUMS]


def test_verify_fails_closed_on_duplicate_entry(tmp_path):
    root = tree(tmp_path); write_freeze(root, Config())
    first = (root / SUMS).read_text().splitlines()[0]
    (root / SUMS).write_text((root / SUMS).read_text() + first + "\n")
    assert verify_freeze(root) == [SUMS]


def test_cli_write_and_verify(tmp_path, monkeypatch, capsys):
    root = tree(tmp_path)
    monkeypatch.setattr("farbversuch.freeze.REPO_ROOT", root)
    cfg_file = tmp_path / "cfg.json"; Config(epochs=7).to_json(cfg_file)
    main(["write", "--config", str(cfg_file)])
    assert Config.from_json(root / "farbversuch" / "frozen_config.json") == Config(epochs=7)
    main(["verify"])
    assert capsys.readouterr().out.strip() == "OK"
    (root / "farbversuch" / "a.py").write_text("x")
    with pytest.raises(SystemExit) as exc:
        main(["verify"])
    assert exc.value.code == 1
    assert "farbversuch/a.py" in capsys.readouterr().out


def verify_fails(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["verify"])
    assert exc.value.code == 1
    return capsys.readouterr().out.splitlines()


def test_cli_verify_marks_new_files_and_exits_1(tmp_path, monkeypatch, capsys):
    root = tree(tmp_path)
    monkeypatch.setattr("farbversuch.freeze.REPO_ROOT", root)
    main(["write"]); capsys.readouterr()
    (root / "farbversuch" / "new.py").write_text("x"); (root / "y.py").write_text("y")
    (root / "farbversuch" / "a.py").write_text("changed")
    assert verify_fails(capsys) == ["farbversuch/a.py", "neu: farbversuch/new.py", "neu: y.py"]


@pytest.mark.parametrize("content", [None, "", "garbage\n"])
def test_cli_verify_fails_closed_without_usable_sums(tmp_path, monkeypatch, capsys, content):
    root = tree(tmp_path)
    monkeypatch.setattr("farbversuch.freeze.REPO_ROOT", root)
    if content is not None:
        (root / SUMS).write_text(content)
    out = verify_fails(capsys)
    assert SUMS in out and "OK" not in out


def test_cli_write_default_config(tmp_path, monkeypatch):
    root = tree(tmp_path)
    monkeypatch.setattr("farbversuch.freeze.REPO_ROOT", root)
    main(["write"])
    assert Config.from_json(root / "farbversuch" / "frozen_config.json") == Config()
