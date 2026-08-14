from __future__ import annotations

import json
from pathlib import Path
import statistics

from common.domain_models import Bus


def _mean(values) -> float:
    values = list(values)
    return float(statistics.fmean(values)) if values else 0.0


class MetricsCollector:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def summarize(self, env) -> dict:
        active = env.active_vehicles()
        buses = [vehicle for vehicle in active if isinstance(vehicle, Bus)]
        cars = [vehicle for vehicle in active if not isinstance(vehicle, Bus)]
        headways = [float(value) for value in env.headway_samples if value is not None]
        critical = float(self.cfg["transit"].get("critical_headway_s", 25.0))
        queue = [vehicle for vehicle in active if vehicle.speed_mps < 0.3]
        return {
            "simulation": {
                "time_s": env.sim_time_s,
                "active_vehicles": len(active),
                "spawned_cars": int(env.stats["spawnedCars"]),
                "spawned_buses": int(env.stats["spawnedBuses"]),
                "completed_cars": int(env.stats["completedCars"]),
                "completed_buses": int(env.stats["completedBuses"]),
            },
            "public_transport": {
                "active_buses": len(buses),
                "mean_travel_time_s": _mean(env.stats["busTravelTimes"]),
                "mean_waiting_time_s": _mean(bus.waiting_time_s for bus in buses),
                "mean_headway_s": _mean(headways),
                "headway_std_s": float(statistics.pstdev(headways)) if len(headways) > 1 else 0.0,
                "headways_below_critical_pct": (100.0 * sum(value < critical for value in headways) / len(headways)) if headways else 0.0,
                "bunching_events": int(env.stats["bunchingEvents"]),
            },
            "general_traffic": {
                "active_cars": len(cars),
                "mean_speed_mps": _mean(vehicle.speed_mps for vehicle in active),
                "mean_car_travel_time_s": _mean(env.stats["carTravelTimes"]),
                "queue_vehicles": len(queue),
                "mean_current_wait_s": _mean(vehicle.waiting_time_s for vehicle in active),
            },
            "signal_control": {
                "phase_changes": {iid: int(value) for iid, value in env.stats["phaseChanges"].items()},
                "intersection_crossings": {iid: int(value) for iid, value in env.stats["intersectionCrossings"].items()},
                "current_phase": {iid: controller.current_phase for iid, controller in env.controllers.items()},
            },
            "rewards": dict(env.last_rewards),
        }

    def write_json(self, env, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.summarize(env), indent=2, ensure_ascii=False), encoding="utf-8")
