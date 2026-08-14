from __future__ import annotations

from collections import deque

FLOW_WINDOW_S = 30.0
AVG_VEHICLE_SPACE_M = 8.0


class SmartCamera:
    """Percepción restringida equivalente a la cámara del proyecto de referencia."""

    def __init__(self, roi_length_m: float, stop_line_m: float):
        self.roi_length_m = float(roi_length_m)
        self.stop_line_m = float(stop_line_m)
        self.entry_line_m = max(0.0, self.stop_line_m - self.roi_length_m)
        self._entry_crossings = deque()
        self._exit_crossings = deque()
        self.current_green_time_s = 0.0

    def record_motion(self, previous_m: float, current_m: float, sim_time_s: float) -> None:
        if previous_m < self.entry_line_m <= current_m:
            self._entry_crossings.append(sim_time_s)

    def record_exit(self, sim_time_s: float) -> None:
        self._exit_crossings.append(sim_time_s)

    def tick(self, sim_time_s: float, dt_s: float, green: bool) -> None:
        self.current_green_time_s = self.current_green_time_s + dt_s if green else 0.0
        while self._entry_crossings and sim_time_s - self._entry_crossings[0] > FLOW_WINDOW_S:
            self._entry_crossings.popleft()
        while self._exit_crossings and sim_time_s - self._exit_crossings[0] > FLOW_WINDOW_S:
            self._exit_crossings.popleft()

    def vehicles_in_roi(self, vehicles) -> list:
        return [v for v in vehicles if self.entry_line_m <= v.position_m <= self.stop_line_m]

    def state_vector(self, vehicles) -> list[float]:
        roi = self.vehicles_in_roi(vehicles)
        capacity = max(self.roi_length_m / AVG_VEHICLE_SPACE_M, 1.0)
        density = min(len(roi) / capacity, 1.5)
        max_wait = max((v.waiting_time_s for v in roi), default=0.0)
        return [
            float(density),
            min(len(self._entry_crossings) / 10.0, 2.0),
            min(len(self._exit_crossings) / 10.0, 2.0),
            min(self.current_green_time_s / 60.0, 2.0),
            min(max_wait / 120.0, 2.0),
        ]
