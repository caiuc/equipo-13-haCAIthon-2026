from __future__ import annotations

import math

from common.domain_models import Bus, SignalColor


def _link_geometry(cfg: dict, link_id: str):
    link = cfg["links"][link_id]
    a = cfg["nodes"][link["from"]]
    b = cfg["nodes"][link["to"]]
    ax, ay = float(a["x"]), float(a["y"])
    bx, by = float(b["x"]), float(b["y"])
    dx, dy = bx - ax, by - ay
    norm = math.hypot(dx, dy) or 1.0
    ux, uy = dx / norm, dy / norm
    # Desplazamiento a la derecha del sentido de circulación: separa las dos pistas.
    nx, ny = -uy, ux
    return link, (ax, ay), (bx, by), (ux, uy), (nx, ny)


def link_world_point(cfg: dict, link_id: str, position_m: float, lane_offset_m: float = 3.2):
    link, a, _, unit, normal = _link_geometry(cfg, link_id)
    length = max(float(link["length_m"]), 1e-6)
    distance = max(0.0, min(float(position_m), length))
    x = a[0] + unit[0] * distance + normal[0] * lane_offset_m
    y = a[1] + unit[1] * distance + normal[1] * lane_offset_m
    heading = math.degrees(math.atan2(unit[1], unit[0]))
    return x, y, heading


def _quadratic(p0, p1, p2, t: float):
    u = 1.0 - t
    x = u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0]
    y = u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]
    dx = 2 * u * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0])
    dy = 2 * u * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1])
    heading = math.degrees(math.atan2(dy, dx)) if abs(dx) + abs(dy) > 1e-9 else 0.0
    return x, y, heading


def _vehicle_pose(cfg: dict, env, vehicle):
    transit = env.transit_for_vehicle(vehicle.id)
    if not transit:
        x, y, heading = link_world_point(cfg, vehicle.current_link, vehicle.position_m)
        return x, y, heading, vehicle.current_link, False

    from_lane = env.lanes[transit.from_link]
    p0 = link_world_point(cfg, transit.from_link, from_lane.stop_line_m or from_lane.length_m)[:2]
    p2 = link_world_point(cfg, transit.to_link, env.intersection_half_size_m)[:2]
    node = cfg["nodes"][transit.intersection_id]
    p1 = (float(node["x"]), float(node["y"]))
    x, y, heading = _quadratic(p0, p1, p2, transit.progress)
    return x, y, heading, transit.from_link, True


def _signal_heads(cfg: dict, env, iid: str):
    result = []
    controller = env.controllers[iid]
    for branch in env.BRANCH_ORDER:
        lane = env._incoming_lane_for_branch(iid, branch)
        if not lane or lane.stop_line_m is None:
            continue
        x, y, heading = link_world_point(cfg, lane.link_id, lane.stop_line_m)
        result.append({
            "branch": branch,
            "x": x,
            "y": y,
            "headingDeg": heading,
            "color": controller.branch_color(branch).value,
        })
    return result


def build_network_snapshot(cfg: dict, env) -> dict:
    vehicles = []
    for vehicle in env.active_vehicles():
        x, y, heading, link_id, inside = _vehicle_pose(cfg, env, vehicle)
        item = {
            "id": vehicle.id,
            "kind": vehicle.kind.value,
            "x": x,
            "y": y,
            "headingDeg": heading,
            "speedMps": vehicle.speed_mps,
            "lengthM": vehicle.length_m,
            "widthM": vehicle.width_m,
            "linkId": link_id,
            "routeId": vehicle.route_id,
            "insideIntersection": inside,
            "waitingTimeS": vehicle.waiting_time_s,
        }
        if isinstance(vehicle, Bus):
            item.update({
                "status": vehicle.status.value,
                "headwayS": vehicle.headway_s,
                "headwayTrendSPerS": vehicle.headway_trend_s_per_s,
                "dwellRemainingS": vehicle.dwell_remaining_s,
            })
        vehicles.append(item)

    intersections = {}
    for iid, controller in env.controllers.items():
        phase = env.logic[iid].phases[controller.current_phase]
        intersections[iid] = {
            "label": cfg["intersections"][iid].get("label", iid),
            "phaseIndex": controller.current_phase,
            "requestedPhase": env.last_actions.get(iid, controller.current_phase),
            "pendingPhase": controller.pending_phase,
            "mode": controller.color_state.value,
            "timeInPhaseS": controller.time_in_phase_s,
            "actionMask": controller.legal_action_mask(),
            "activeMovements": [movement.key for movement in phase.movements],
            "signals": {branch: controller.branch_color(branch).value for branch in env.BRANCH_ORDER},
            "signalHeads": _signal_heads(cfg, env, iid),
            "reward": env.last_rewards.get(iid, 0.0),
            "rewardBreakdown": env.last_reward_breakdown.get(iid, {}),
        }

    return {
        "timeS": env.sim_time_s,
        "vehicles": vehicles,
        "intersections": intersections,
        "stops": cfg.get("stops", {}),
        "trafficRules": {
            "minimumGapM": env.minimum_gap_m,
            "dtS": env.dt_s,
            "decisionIntervalS": env.decision_interval_s,
            "intersectionHalfSizeM": env.intersection_half_size_m,
        },
    }
