import pytest

from farbversuch.run import run_seed
from farbversuch.tests.helpers import TINY, strip_sec


@pytest.mark.slow
def test_same_seed_same_result():
    assert strip_sec(run_seed(0, TINY)) == strip_sec(run_seed(0, TINY))
