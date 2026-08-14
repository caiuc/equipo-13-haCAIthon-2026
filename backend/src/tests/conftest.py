from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from common.domain_models import IntersectionLogic, Movement, Phase
from config.scenario_loader import load_config


@pytest.fixture
def cfg():
    path = Path(__file__).resolve().parents[1] / "config" / "scenarios" / "example_network.yaml"
    return load_config(path)


@pytest.fixture
def fast_cfg(cfg):
    value = deepcopy(cfg)
    value["rl"]["batch_size"] = 4
    value["rl"]["epsilon_decay_steps"] = 50
    return value


@pytest.fixture
def logic(cfg):
    result = {}
    for iid in cfg["intersections"]:
        movements = [
            Movement(iid, "north_in", "north", "south", "straight"),
            Movement(iid, "south_in", "south", "north", "straight"),
            Movement(iid, "east_in", "east", "west", "straight"),
            Movement(iid, "west_in", "west", "east", "straight"),
        ]
        phases = [Phase(0, movements[:2]), Phase(1, movements[2:])]
        conflicts = {frozenset((a.key, b.key)) for a in phases[0].movements for b in phases[1].movements}
        result[iid] = IntersectionLogic(iid, movements, conflicts, phases)
    return result
