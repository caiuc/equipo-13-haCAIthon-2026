import random

from common.domain_models import Bus, VehicleKind
from simulacion.paraderos.stop_manager import StopManager


def test_stop_manager_starts_dwell_when_bus_reaches_stop():
    cfg = {
        "stops": {"s1": {"link": "l1", "position_m": 10}},
        "transit": {"dwell_min_s": 12, "dwell_max_s": 12},
    }
    bus = Bus(
        id="b1",
        kind=VehicleKind.BUS,
        route_id="r1",
        route_links=["l1"],
        position_m=10,
        metadata={"stop_ids": ["s1"], "visited_stops": []},
    )
    manager = StopManager(cfg, random.Random(1), 0.2)
    assert manager.handle(bus, 30.0)
    assert bus.dwell_remaining_s == 12
    assert bus.next_stop_index == 1
    assert bus.metadata["visited_stops"][0]["id"] == "s1"
