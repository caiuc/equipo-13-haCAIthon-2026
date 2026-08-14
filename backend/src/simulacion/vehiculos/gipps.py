"""Modelo de seguimiento de Gipps adaptado del proyecto de referencia Empresa.zip."""
from __future__ import annotations

import math
from common.domain_models import Vehicle

B_LEADER_ASSUMED = 3.0


def acceleration_speed(vehicle: Vehicle) -> float:
    v = max(vehicle.speed_mps, 0.0)
    desired = max(vehicle.desired_speed_mps, 0.1)
    ratio = min(max(v / desired, 0.0), 1.0)
    return v + 2.5 * vehicle.max_accel * vehicle.reaction_time_s * (1.0 - ratio) * math.sqrt(0.025 + ratio)


def braking_speed(vehicle: Vehicle, leader: Vehicle | None, stop_position_m: float | None) -> float:
    b_n = max(vehicle.comfortable_decel, 0.1)
    tau = max(vehicle.reaction_time_s, 0.1)
    v_n = max(vehicle.speed_mps, 0.0)
    result = float("inf")

    if leader is not None:
        gap = max(leader.position_m - leader.length_m - vehicle.position_m - vehicle.safe_gap_m, 0.0)
        v_lead = max(leader.speed_mps, 0.0)
        inner = b_n * b_n * tau * tau + b_n * (2.0 * gap - v_n * tau - (v_lead * v_lead) / B_LEADER_ASSUMED)
        result = min(result, -b_n * tau + math.sqrt(inner) if inner >= 0 else 0.0)

    if stop_position_m is not None:
        gap = max(stop_position_m - vehicle.position_m, 0.0)
        inner = b_n * b_n * tau * tau + b_n * (2.0 * gap - v_n * tau)
        result = min(result, -b_n * tau + math.sqrt(inner) if inner >= 0 else 0.0)

    return max(result, 0.0)


def update_vehicle(vehicle: Vehicle, dt_s: float, leader: Vehicle | None, stop_position_m: float | None) -> None:
    """Avanza un vehículo sin permitir atravesar líder ni línea de detención."""
    old_position = vehicle.position_m
    accel_v = acceleration_speed(vehicle)
    brake_v = braking_speed(vehicle, leader, stop_position_m)
    new_v = max(0.0, min(accel_v, brake_v, vehicle.desired_speed_mps))
    new_position = old_position + 0.5 * (vehicle.speed_mps + new_v) * dt_s

    if stop_position_m is not None and old_position <= stop_position_m:
        new_position = min(new_position, stop_position_m)
        if new_position >= stop_position_m - 1e-4:
            new_v = 0.0

    if leader is not None:
        max_position = leader.position_m - leader.length_m - vehicle.safe_gap_m
        if new_position > max_position:
            new_position = max(old_position, max_position)
            new_v = min(new_v, leader.speed_mps)

    vehicle.position_m = max(0.0, new_position)
    vehicle.speed_mps = max(0.0, new_v)
    if vehicle.speed_mps < 0.3:
        vehicle.waiting_time_s += dt_s
    else:
        vehicle.waiting_time_s = 0.0
