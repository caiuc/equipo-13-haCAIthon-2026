from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import random
import numpy as np


@dataclass
class Transition:
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool
    next_mask: np.ndarray


class ReplayBuffer:
    def __init__(self, capacity: int, seed: int = 42):
        self.data = deque(maxlen=int(capacity))
        self.rng = random.Random(seed)

    def __len__(self):
        return len(self.data)

    def push(self, *args):
        self.data.append(Transition(*args))

    def sample(self, n: int) -> list[Transition]:
        return self.rng.sample(self.data, n)
