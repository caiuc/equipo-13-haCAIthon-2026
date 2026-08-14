from __future__ import annotations

from common.domain_models import Bus


def _vehicle_position(cfg: dict, vehicle) -> dict:
    link = cfg["links"][vehicle.current_link]
    origin = cfg["nodes"][link["from"]]
    destination = cfg["nodes"][link["to"]]
    length_m = max(float(link["length_m"]), 1.0)
    fraction = max(0.0, min(1.0, vehicle.position_m / length_m))
    x = float(origin["x"]) + (float(destination["x"]) - float(origin["x"])) * fraction
    y = float(origin["y"]) + (float(destination["y"]) - float(origin["y"])) * fraction
    return {"x": x, "y": y, "linkId": vehicle.current_link, "progress": fraction}


def _branch_signals(cfg: dict, env, intersection_id: str, controller) -> dict[str, str]:
    """Proyecta el controlador por fase a cuatro cabezales de aproximación.

    Cada rama se muestra en verde cuando la fase activa contiene al menos un
    movimiento originado en ella. Durante la transición, esas aproximaciones se
    muestran en amarillo. Todas las demás permanecen en rojo.
    """
    branches = cfg["intersections"][intersection_id].get("branches", {})
    result = {branch: "RED" for branch in branches}
    phase = env.logic[intersection_id].phases[controller.phase_index]
    active_from = {getattr(movement, "from_branch", None) for movement in phase.movements}
    active_from.discard(None)
    color = "YELLOW" if controller.mode.value == "YELLOW" else "GREEN"
    for branch in active_from:
        if branch in result:
            result[branch] = color
    return result



def _action_mask_snapshot(controller):
    try:
        return controller.action_mask(record_restriction=False)
    except TypeError:
        return controller.action_mask()


def build_network_snapshot(cfg: dict, env) -> dict:
    """DTO puro para React; contiene estado real, no decisiones visuales inventadas."""
    vehicles = []
    for vehicle in env.network.vehicles.values():
        position = _vehicle_position(cfg, vehicle)
        item = {
            "id": vehicle.id,
            "kind": vehicle.kind.value,
            "speedMps": vehicle.speed_mps,
            "routeId": vehicle.route_id,
            "routeLinks": list(vehicle.route_links),
            **position,
        }
        if isinstance(vehicle, Bus):
            item.update(
                {
                    "status": vehicle.status.value,
                    "headwayS": vehicle.headway_s,
                    "headwayTrendSPerS": vehicle.headway_trend_s_per_s,
                    "nextStopIndex": vehicle.next_stop_index,
                    "leaderId": vehicle.metadata.get("leader_id"),
                    "followerId": vehicle.metadata.get("follower_id"),
                }
            )
        vehicles.append(item)

    intersections = {}
    for intersection_id, controller in env.controllers.items():
        phase = env.logic[intersection_id].phases[controller.phase_index]
        last_actions = getattr(env, "last_actions", {})
        selected_phase = int(last_actions.get(intersection_id, controller.phase_index))
        intersections[intersection_id] = {
            "phaseIndex": controller.phase_index,
            "selectedPhase": selected_phase,
            "pendingPhase": getattr(controller, "pending_phase", None),
            "mode": controller.mode.value,
            "elapsedS": controller.elapsed_s,
            "decisionCount": int(getattr(env, "decision_count", 0)),
            "activeMovements": [movement.key for movement in phase.movements],
            "activeBranches": sorted({getattr(movement, "from_branch", "") for movement in phase.movements if getattr(movement, "from_branch", "")}),
            "branchSignals": _branch_signals(cfg, env, intersection_id, controller),
            "actionMask": _action_mask_snapshot(controller),
            "rewardComponents": getattr(env, "last_reward_components", {}).get(intersection_id, {}),
        }

    return {
        "timeS": env.network.time_s,
        "nodes": cfg["nodes"],
        "links": cfg["links"],
        "intersectionsConfig": cfg.get("intersections", {}),
        "stops": cfg.get("stops", {}),
        "busRoutes": cfg.get("bus_routes", {}),
        "display": cfg.get("display", {}),
        "vehicles": vehicles,
        "intersections": intersections,
        "cameraRoiM": float(cfg["simulation"].get("camera_roi_m", 60.0)),
    }
