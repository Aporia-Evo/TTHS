import pytest

from farbversuch.tests.helpers import TINY


@pytest.fixture(scope="session")
def tiny_phase1():
    from farbversuch.run import phase1
    return phase1(0, TINY)
