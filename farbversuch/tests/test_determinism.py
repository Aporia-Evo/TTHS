import pytest

from farbversuch.run import run_seed
from farbversuch.tests.helpers import TINY


def strip_sec(x):
    if isinstance(x, dict): return {k: strip_sec(v) for k, v in x.items() if not k.endswith("_sec")}
    if isinstance(x, list): return [strip_sec(v) for v in x]
    return x


@pytest.mark.slow
def test_same_seed_same_result():
    assert strip_sec(run_seed(0, TINY)) == strip_sec(run_seed(0, TINY))
