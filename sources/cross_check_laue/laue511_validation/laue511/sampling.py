from __future__ import annotations

import random
from collections import Counter
from typing import Mapping


def sample_branch(p_abs: float, p_diff: float, p_trans: float, rng: random.Random) -> str:
    u = rng.random()
    if u < p_abs:
        return "ABSORB"
    if u < p_abs + p_diff:
        return "DIFFRACT"
    return "TRANSMIT"


def sample_branch_counts(probabilities: Mapping[str, float], n: int, seed: int) -> Counter[str]:
    rng = random.Random(seed)
    return Counter(
        sample_branch(
            float(probabilities["p_abs"]),
            float(probabilities["p_diff"]),
            float(probabilities["p_trans"]),
            rng,
        )
        for _ in range(n)
    )
