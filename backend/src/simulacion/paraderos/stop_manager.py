from __future__ import annotations

import random

from common.domain_models import Bus


class StopManager:
    """Gestiona detenciones de buses sin acoplar paraderos al motor de tráfico."""

    def __init__(self, cfg: dict, rng: random.Random, dt_s: float):
        self.cfg = cfg
        self.rng = rng
        self.dt_s = float(dt_s)

    def handle(self, bus: Bus, now_s: float) -> bool:
        if bus.dwell_remaining_s > 0:
            bus.dwell_remaining_s = max(0.0, bus.dwell_remaining_s - self.dt_s)
            bus.speed_mps = 0.0
            bus.waiting_time_s += self.dt_s
            return True

        stop_ids = bus.metadata.get("stop_ids", [])
        if bus.next_stop_index >= len(stop_ids):
            return False

        stop_id = stop_ids[bus.next_stop_index]
        stop = self.cfg["stops"][stop_id]
        if stop["link"] != bus.current_link or bus.position_m < float(stop["position_m"]):
            return False

        transit = self.cfg["transit"]
        dwell_s = self.rng.uniform(float(transit["dwell_min_s"]), float(transit["dwell_max_s"]))
        bus.dwell_remaining_s = dwell_s
        bus.speed_mps = 0.0
        bus.next_stop_index += 1
        bus.metadata.setdefault("visited_stops", []).append(
            {"id": stop_id, "arrival_s": now_s, "dwell_s": dwell_s}
        )
        return True
