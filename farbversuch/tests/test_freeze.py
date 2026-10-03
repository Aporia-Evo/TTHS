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


def test_verify_ignores_files_added_after_freezing(tmp_path):
    root = tree(tmp_path); write_freeze(root, Config())
    (root / "farbversuch" / "new.py").write_text("x")
    assert verify_freeze(root) == []


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


def test_cli_write_default_config(tmp_path, monkeypatch):
    root = tree(tmp_path)
    monkeypatch.setattr("farbversuch.freeze.REPO_ROOT", root)
    main(["write"])
    assert Config.from_json(root / "farbversuch" / "frozen_config.json") == Config()
