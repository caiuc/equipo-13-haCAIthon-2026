from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class VehicleKind(str, Enum):
    CAR = "CAR"
    BUS = "BUS"


class SignalMode(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"


class BusStatus(str, Enum):
    NORMAL = "normal"
    EARLY = "adelantado"
    LATE = "atrasado"
    RISK = "riesgo_bunching"
    CRITICAL = "critico_bunching"


@dataclass(frozen=True)
class Movement:
    intersection_id: str
    lane_id: str
    from_branch: str
    to_branch: str
    turn: str

    @property
    def key(self) -> str:
        return f"{self.lane_id}->{self.to_branch}"


@dataclass
class Phase:
    index: int
    movements: list[Movement]


@dataclass
class IntersectionLogic:
    intersection_id: str
    movements: list[Movement]
    conflicts: set[frozenset[str]]
    phases: list[Phase]


@dataclass
class Vehicle:
    id: str
    kind: VehicleKind
    route_id: str | None
    route_links: list[str]
    link_index: int = 0
    position_m: float = 0.0
    speed_mps: float = 0.0
    desired_speed_mps: float = 13.9
    length_m: float = 4.5
    max_accel: float = 2.0
    comfortable_decel: float = 3.0
    reaction_time_s: float = 1.0
    created_at_s: float = 0.0
    waiting_time_s: float = 0.0
    finished_at_s: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def current_link(self) -> str:
        return self.route_links[self.link_index]

    @property
    def finished(self) -> bool:
        return self.finished_at_s is not None


@dataclass
class Bus(Vehicle):
    next_stop_index: int = 0
    dwell_remaining_s: float = 0.0
    headway_s: float | None = None
    headway_trend_s_per_s: float = 0.0
    status: BusStatus = BusStatus.NORMAL


@dataclass
class NeighborMessage:
    sender_id: str
    timestamp_s: float
    congestion: float
    congested_movements: list[str]
    current_phase: int
    upcoming_buses: list[dict[str, Any]]
    critical_events: list[str]
