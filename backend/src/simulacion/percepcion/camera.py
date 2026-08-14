from __future__ import annotations

from collections import defaultdict


class CameraPerception:
    """Percepción limitada a una ROI; nunca revela rutas completas de autos."""
    def __init__(self, cfg: dict, network):
        self.cfg = cfg
        self.network = network
        self.roi_m = float(cfg['simulation'].get('camera_roi_m', 60.0))
        self._prev_counts = defaultdict(int)

    def observe(self, intersection_id: str, dt_window: float) -> dict[str, dict[str, float]]:
        result = defaultdict(lambda: {'density':0.0,'inflow':0.0,'outflow':0.0,'queue':0.0,'mean_speed':0.0})
        speeds = defaultdict(list)
        current_counts = defaultdict(int)
        for car in self.network.active_cars():
            movement = self.network._next_movement(car)
            if movement is None or movement[0] != intersection_id:
                continue
            link = self.cfg['links'][car.current_link]
            distance = float(link['length_m']) - car.position_m
            if 0 <= distance <= self.roi_m:
                key = f'{movement[1]}->{movement[2]}'
                current_counts[key] += 1
                speeds[key].append(car.speed_mps)
                if car.speed_mps < 0.5:
                    result[key]['queue'] += 1.0

        for key,count in current_counts.items():
            prev = self._prev_counts[(intersection_id,key)]
            # La diferencia de conteo solo es una aproximación de línea de conteo.
            delta = count - prev
            result[key]['inflow'] = max(0.0, delta) / max(dt_window, 1e-6)
            result[key]['outflow'] = max(0.0, -delta) / max(dt_window, 1e-6)
            result[key]['density'] = count / max(self.roi_m, 1.0)
            result[key]['mean_speed'] = sum(speeds[key])/len(speeds[key]) if speeds[key] else 0.0
            self._prev_counts[(intersection_id,key)] = count
        return dict(result)
