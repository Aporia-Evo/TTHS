"""Einfrieren: frozen_config.json schreiben und SHA-256 aller Quelldateien in freeze.sha256 festhalten."""
import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

from farbversuch.config import Config

REPO_ROOT = Path(__file__).resolve().parent.parent
PKG = "farbversuch"
CONFIG_REL = f"{PKG}/frozen_config.json"
SUMS_REL = f"{PKG}/freeze.sha256"


_SUMS_LINE = re.compile(r"([0-9a-f]{64})  (\S.*)")


def source_files(root: Path) -> list[Path]:
    """requirements.txt, pytest.ini und jede *.py unter root (rekursiv, inkl. Tests und Wurzel: `python -m` legt das
    Arbeitsverzeichnis auf sys.path), sortiert, relativ zu root. Ausgenommen sind Pfade mit einer Komponente, die mit
    "." beginnt (.git, .superpowers, .pytest_cache ...) oder __pycache__ heißt."""
    found = [Path(n) for n in ("requirements.txt", "pytest.ini") if (root / n).is_file()]
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "__pycache__"]
        found += [Path(dirpath, f).relative_to(root) for f in filenames if f.endswith(".py") and not f.startswith(".")]
    return sorted(found)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_freeze(root: Path, cfg: Config) -> None:
    """Schreibt frozen_config.json, danach freeze.sha256 im sha256sum-Format (prüfbar mit `sha256sum -c` im Repo-Wurzelordner)."""
    cfg.to_json(root / CONFIG_REL)
    rels = sorted({p.as_posix() for p in source_files(root)} | {CONFIG_REL})
    lines = [f"{_sha256(root / rel)}  {rel}\n" for rel in rels]
    (root / SUMS_REL).write_text("".join(lines))


def _read_sums(root: Path) -> tuple[dict[str, str], bool]:
    """(Pfad -> Hash, intakt). Fehlende, unlesbare oder leere Datei, fehlerhafte Zeile oder doppelter Pfad: nicht intakt."""
    try:
        text = (root / SUMS_REL).read_text()
    except (OSError, UnicodeDecodeError):
        return {}, False
    sums, intact = {}, True
    for line in text.splitlines():
        if not line.strip():
            continue
        m = _SUMS_LINE.fullmatch(line)
        if m is None or m[2] in sums:
            intact = False
        else:
            sums[m[2]] = m[1]
    return sums, intact and bool(sums)


def _check(root: Path) -> tuple[list[str], list[str]]:
    """(geänderte, fehlende oder unbrauchbare Pfade; seit dem Einfrieren hinzugekommene Quelldateien), je sortiert."""
    sums, intact = _read_sums(root)
    if not sums:                                    # nichts zum Vergleichen: jede weitere Meldung wäre Rauschen
        return [SUMS_REL], []
    bad = [] if intact else [SUMS_REL]
    bad += [rel for rel, digest in sums.items() if not (root / rel).is_file() or _sha256(root / rel) != digest]
    new = [p.as_posix() for p in source_files(root) if p.as_posix() not in sums]
    return sorted(bad), sorted(new)


def verify_freeze(root: Path) -> list[str]:
    """Problempfade, sortiert; [] = in Ordnung. Schlägt bei jeder Unklarheit fehl: fehlende, leere oder fehlerhafte
    Prüfsummendatei (Pfad der Datei selbst), abweichende oder fehlende Dateien und jede nicht gelistete Quelldatei."""
    bad, new = _check(root)
    return sorted(bad + new)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m farbversuch.freeze", description="Farbversuch: Konfiguration und Quelldateien einfrieren")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write", help="frozen_config.json und freeze.sha256 schreiben")
    w.add_argument("--config", default=None, help="Konfigurations-JSON (Standard: Config())")
    sub.add_parser("verify", help="Prüfsummen prüfen (Exitcode 1 bei Abweichung)")
    args = ap.parse_args(argv)

    if args.cmd == "write":
        write_freeze(REPO_ROOT, Config.from_json(args.config) if args.config else Config())
        return
    bad, new = _check(REPO_ROOT)
    if bad or new:
        print("\n".join(line for _, line in sorted([(p, p) for p in bad] + [(p, f"neu: {p}") for p in new])))
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
