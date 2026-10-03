import ast
import inspect
from pathlib import Path

import pytest

from farbversuch.monitor import Monitor
from farbversuch.routine import Routine

FORBIDDEN = {"C_SPECIAL", "condition", "switch_episode", "red_active", "p_global", "env_params", "Config", "CONDITIONS"}
ALLOWED_WORLD = {"DELTAS", "N_ACTIONS", "OBS_DIM", "CH_WALL", "CH_GOAL", "CH_COLOR", "N_DISP", "obs_index"}


@pytest.mark.parametrize("mod", ["routine", "forward", "monitor"])
def test_no_access_to_condition_switch_or_special(mod):
    tree = ast.parse((Path(__file__).parents[1] / f"{mod}.py").read_text())
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name): names.add(n.id)
        if isinstance(n, ast.Attribute): names.add(n.attr)
        if isinstance(n, ast.arg): names.add(n.arg)
        if isinstance(n, (ast.Import, ast.ImportFrom)): names |= {a.name for a in n.names}
        if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("farbversuch"):
            assert n.module in ("farbversuch.world", "farbversuch.forward", "farbversuch.seeds")
            if n.module == "farbversuch.world":
                assert {a.name for a in n.names} <= ALLOWED_WORLD
        if isinstance(n, ast.Import):
            assert not any(a.name.startswith("farbversuch") for a in n.names)
    assert not names & FORBIDDEN


def test_agent_and_monitor_see_only_experience():
    assert list(inspect.signature(Routine.act).parameters) == ["self", "obs"]
    assert list(inspect.signature(Monitor.add_step).parameters) == ["self", "obs", "action", "disp"]
