"""Konfiguration des Farbversuchs; alle Werte stehen in frozen_config.json fest."""
import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path


@dataclass(frozen=True)
class Config:
    wall_p: float = 0.15; wall_p_dense: float = 0.30; p_slip: float = 0.10; red_p: float = 0.5
    min_dist: int = 5; max_steps: int = 40
    n_teacher_episodes: int = 4000; k: int = 32; lr: float = 0.5; epochs: int = 1000; wd: float = 1e-3; init_std: float = 0.01
    n_forward_episodes: int = 1000; fwd_l2: float = 1e-3; logreg_tol: float = 1e-6; logreg_max_iter: int = 500
    n_null_streams: int = 20; n_null_episodes: int = 400; max_null_alarms: int = 0; cusum_sd_factor: float = 0.5
    n_invariance_maps: int = 500; min_invariance: float = 0.95; n_premise_fwd_episodes: int = 300
    n_pglobal_episodes: int = 300; pglobal_tol: float = 0.02; pglobal_max_iter: int = 30
    n_deploy_episodes: int = 400; switch_episode: int = 100; buffer_size: int = 2000
    notice_window: int = 500; check_interval: int = 10
    n_folds: int = 5; max_open: int = 3; n_perm: int = 1000; alpha: float = 0.05
    n_perm_A: int = 25000; perm_chunk: int = 1000; pre_open_delta: float = 0.01; max_pre_open: int = 8
    max_restanteil: float = 0.15; max_shift: float = 0.25; n_shift_positions: int = 500
    systems: tuple[str, ...] = ("M3-B", "M3-A", "S1-B", "S1-A")

    def as_dict(self) -> dict:
        """JSON-fähig: Tupel als Liste."""
        return {k: list(v) if isinstance(v, tuple) else v for k, v in asdict(self).items()}

    def to_json(self, path) -> None:
        Path(path).write_text(json.dumps(self.as_dict(), indent=2) + "\n")

    @classmethod
    def from_json(cls, path) -> "Config":
        """Fehlende Schlüssel nehmen den Standard, ein unbekannter Schlüssel ist ein Fehler."""
        raw = json.loads(Path(path).read_text())
        unknown = sorted(set(raw) - {f.name for f in fields(cls)})
        if unknown:
            raise ValueError(f"unbekannte Konfigurationsschlüssel: {unknown}")
        return cls(**{k: tuple(v) if isinstance(v, list) else v for k, v in raw.items()})
