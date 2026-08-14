from __future__ import annotations


def serialize_topology(logic: dict) -> dict:
    intersections = {}
    for intersection_id, item in logic.items():
        intersections[intersection_id] = {
            "movements": [
                {
                    "key": movement.key,
                    "laneId": movement.lane_id,
                    "fromBranch": movement.from_branch,
                    "toBranch": movement.to_branch,
                    "turn": movement.turn,
                }
                for movement in item.movements
            ],
            "conflicts": [sorted(conflict) for conflict in sorted(item.conflicts, key=lambda x: sorted(x))],
            "phases": [
                {
                    "index": phase.index,
                    "movements": [movement.key for movement in phase.movements],
                }
                for phase in item.phases
            ],
        }
    return {"intersections": intersections}
