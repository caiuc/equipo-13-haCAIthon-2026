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


def build_network_snapshot(cfg: dict, env) -> dict:
    """DTO de visualización. React decide cómo representarlo; Python solo expone estado."""
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
        intersections[intersection_id] = {
            "phaseIndex": controller.phase_index,
            "mode": controller.mode.value,
            "elapsedS": controller.elapsed_s,
            "activeMovements": [movement.key for movement in phase.movements],
            "actionMask": controller.action_mask(),
        }

    return {
        "timeS": env.network.time_s,
        "nodes": cfg["nodes"],
        "links": cfg["links"],
        "stops": cfg.get("stops", {}),
        "busRoutes": cfg.get("bus_routes", {}),
        "vehicles": vehicles,
        "intersections": intersections,
        "cameraRoiM": float(cfg["simulation"].get("camera_roi_m", 60.0)),
    }
