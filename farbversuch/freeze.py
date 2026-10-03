"""Einfrieren: frozen_config.json schreiben und SHA-256 aller Quelldateien in freeze.sha256 festhalten."""
import argparse
import hashlib
import sys
from pathlib import Path

from farbversuch.config import Config

REPO_ROOT = Path(__file__).resolve().parent.parent
PKG = "farbversuch"
CONFIG_REL = f"{PKG}/frozen_config.json"
SUMS_REL = f"{PKG}/freeze.sha256"


def source_files(root: Path) -> list[Path]:
    """requirements.txt, pytest.ini und alle *.py unter farbversuch/ (inkl. Tests), sortiert, relativ zu root."""
    found = [Path(n) for n in ("requirements.txt", "pytest.ini") if (root / n).is_file()]
    found += [p.relative_to(root) for p in (root / PKG).rglob("*.py") if "__pycache__" not in p.parts]
    return sorted(found)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_freeze(root: Path, cfg: Config) -> None:
    """Schreibt frozen_config.json, danach freeze.sha256 im sha256sum-Format (prüfbar mit `sha256sum -c` im Repo-Wurzelordner)."""
    cfg.to_json(root / CONFIG_REL)
    rels = sorted({p.as_posix() for p in source_files(root)} | {CONFIG_REL})
    lines = [f"{_sha256(root / rel)}  {rel}\n" for rel in rels]
    (root / SUMS_REL).write_text("".join(lines))


def verify_freeze(root: Path) -> list[str]:
    """Abweichende oder fehlende Pfade, sortiert; [] = in Ordnung. Nach dem Einfrieren hinzugekommene Dateien werden nicht gemeldet."""
    bad = []
    for line in (root / SUMS_REL).read_text().splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        path = root / rel
        if not path.is_file() or _sha256(path) != digest:
            bad.append(rel)
    return sorted(bad)


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
    bad = verify_freeze(REPO_ROOT)
    if bad:
        print("\n".join(bad))
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
