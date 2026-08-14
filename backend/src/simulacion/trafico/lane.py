from __future__ import annotations

from dataclasses import dataclass, field

from common.domain_models import Vehicle
from simulacion.percepcion.camera import SmartCamera


@dataclass
class RoadLane:
    link_id: str
    length_m: float
    speed_limit_mps: float
    stop_line_m: float | None
    camera: SmartCamera | None = None
    vehicles: list[Vehicle] = field(default_factory=list)

    def sort_front_to_back(self) -> None:
        self.vehicles.sort(key=lambda vehicle: -vehicle.position_m)

    def has_spawn_space(self, required_m: float) -> bool:
        if not self.vehicles:
            return True
        rear = min(self.vehicles, key=lambda vehicle: vehicle.position_m)
        return rear.position_m >= required_m

    def has_entry_space(self, position_m: float, required_m: float) -> bool:
        candidates = [v for v in self.vehicles if v.position_m >= position_m]
        if not candidates:
            return True
        nearest = min(candidates, key=lambda vehicle: vehicle.position_m)
        return nearest.position_m - position_m >= required_m
