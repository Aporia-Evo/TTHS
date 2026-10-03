"""Zufallsschlüssel: jeder Strom heißt np.random.default_rng([seed, TAG, ...])."""
import numpy as np

TEACHER, INIT, FORWARD, NULL, INVARIANCE, RECOLOR, PREMISE_FWD, PGLOBAL, DEPLOY, CV, PERM = range(1, 12)


def rng(*keys: int) -> np.random.Generator:
    return np.random.default_rng(list(keys))


def episode_rngs(seed: int, tag: int, stream: int, episode: int) -> tuple[np.random.Generator, np.random.Generator]:
    """(Karte, Dynamik) einer Episode; Teil 0 zieht die Karte, Teil 1 die Dynamik."""
    return rng(seed, tag, stream, episode, 0), rng(seed, tag, stream, episode, 1)
