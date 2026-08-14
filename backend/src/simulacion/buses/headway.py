from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import statistics

from common.domain_models import Bus, BusStatus


@dataclass
class HeadwaySnapshot:
    route_id: str
    bus_id: str
    leader_id: str | None
    headway_s: float | None
    target_s: float
    deviation_s: float
    trend_s_per_s: float
    status: BusStatus


class HeadwayTracker:
    def __init__(
        self,
        target_s: float,
        critical_s: float,
        risk_s: float,
        imminent_s: float,
        position_sample_s: float = 1.0,
        trend_sample_s: float = 5.0,
        trend_window_s: float = 60.0,
        dangerous_trend_s_per_s: float = -0.15,
    ):
        self.target_s = float(target_s)
        self.critical_s = float(critical_s)
        self.risk_s = float(risk_s)
        self.imminent_s = float(imminent_s)
        self.position_sample_s = float(position_sample_s)
        self.trend_sample_s = float(trend_sample_s)
        self.trend_window_s = float(trend_window_s)
        self.dangerous_trend_s_per_s = float(dangerous_trend_s_per_s)
        # Trayectoria (tiempo, progreso_m) por bus, muestreada cada `position_sample_s`,
        # usada para derivar el headway temporal real (sin asumir una velocidad fija).
        self._progress_history: dict[str, deque[tuple[float, float]]] = defaultdict(lambda: deque(maxlen=600))
        # Historial de headway por par (route, follower) acotado a `trend_window_s` para la regresión de tendencia.
        trend_capacity = max(2, int(self.trend_window_s / max(self.trend_sample_s, 0.1)) + 2)
        self.history: dict[str, deque[tuple[float, float]]] = defaultdict(lambda: deque(maxlen=trend_capacity))
        # Todas las observaciones válidas de headway del episodio, para métricas agregadas.
        self.observations: list[float] = []
        self.events: list[dict] = []
        self._active_bunching: set[tuple[str, str]] = set()

    def record_progress(self, bus_id: str, now_s: float, progress_m: float) -> None:
        """Guarda una muestra de trayectoria del bus (cada `position_sample_s`)."""
        hist = self._progress_history[bus_id]
        if hist and now_s - hist[-1][0] < self.position_sample_s:
            return
        hist.append((now_s, progress_m))

    def temporal_headway(self, leader_id: str, follower_progress_m: float, now_s: float) -> float | None:
        """Headway temporal real: instante en que el líder pasó por `follower_progress_m`.

        Interpola linealmente entre las dos muestras de trayectoria del líder que
        rodean ese progreso. No asume ninguna velocidad; si no hay historial
        suficiente devuelve None en vez de aproximar con un dato incorrecto.
        """
        hist = self._progress_history.get(leader_id)
        if not hist:
            return None
        points = list(hist)
        if follower_progress_m < points[0][1] - 1e-6:
            return None
        if follower_progress_m > points[-1][1] + 1e-6:
            return None
        for (t1, p1), (t2, p2) in zip(points, points[1:]):
            if p1 - 1e-6 <= follower_progress_m <= p2 + 1e-6:
                if p2 - p1 < 1e-9:
                    t_at = t2
                else:
                    frac = (follower_progress_m - p1) / (p2 - p1)
                    t_at = t1 + frac * (t2 - t1)
                return max(0.0, now_s - t_at)
        t_last, p_last = points[-1]
        if abs(follower_progress_m - p_last) <= 1e-6:
            return max(0.0, now_s - t_last)
        return None

    def _trend(self, key: str, now_s: float, headway_s: float) -> float:
        """Pendiente (s de headway / s de simulación) mediante regresión lineal simple
        sobre la ventana `trend_window_s`, muestreada cada `trend_sample_s`."""
        hist = self.history[key]
        if not hist or now_s - hist[-1][0] >= self.trend_sample_s:
            hist.append((now_s, headway_s))
        cutoff = now_s - self.trend_window_s
        while hist and hist[0][0] < cutoff:
            hist.popleft()
        if len(hist) < 2:
            return 0.0
        mean_t = sum(t for t, _ in hist) / len(hist)
        mean_h = sum(h for _, h in hist) / len(hist)
        num = sum((t - mean_t) * (h - mean_h) for t, h in hist)
        den = sum((t - mean_t) ** 2 for t, _ in hist)
        return num / den if den > 1e-9 else 0.0

    def classify(self, headway_s: float | None, trend: float = 0.0) -> BusStatus:
        if headway_s is None:
            return BusStatus.NORMAL
        if headway_s < self.critical_s:
            return BusStatus.CRITICAL
        if headway_s < self.imminent_s or (headway_s < self.risk_s and trend < self.dangerous_trend_s_per_s):
            return BusStatus.RISK
        if headway_s > self.target_s * 1.25:
            return BusStatus.LATE
        if headway_s < self.target_s * 0.75:
            return BusStatus.EARLY
        return BusStatus.NORMAL

    def update_pair(self, route_id: str, follower: Bus, leader: Bus | None, now_s: float, headway_s: float | None) -> HeadwaySnapshot:
        key = f'{route_id}:{follower.id}'
        trend = 0.0
        if headway_s is not None:
            trend = self._trend(key, now_s, headway_s)
            self.observations.append(headway_s)
        status = self.classify(headway_s, trend)
        follower.headway_s = headway_s
        follower.headway_trend_s_per_s = trend
        follower.status = status

        pair = (route_id, follower.id)
        if status == BusStatus.CRITICAL and pair not in self._active_bunching:
            self._active_bunching.add(pair)
            self.events.append({'type':'bunching_start','route':route_id,'bus':follower.id,'time_s':now_s})
        elif status != BusStatus.CRITICAL and pair in self._active_bunching:
            self._active_bunching.remove(pair)
            self.events.append({'type':'bunching_end','route':route_id,'bus':follower.id,'time_s':now_s})

        deviation = 0.0 if headway_s is None else headway_s - self.target_s
        return HeadwaySnapshot(route_id, follower.id, leader.id if leader else None, headway_s,
                               self.target_s, deviation, trend, status)

    def progressive_penalty(self, headway_s: float | None, trend: float = 0.0) -> float:
        if headway_s is None:
            return 0.0
        # Penaliza desviación simétrica y hace que la zona crítica domine.
        normalized_dev = abs(headway_s - self.target_s) / max(self.target_s, 1.0)
        penalty = normalized_dev ** 1.5
        if headway_s < self.risk_s:
            risk_ratio = (self.risk_s - headway_s) / max(self.risk_s - self.critical_s, 1.0)
            penalty += 2.5 * max(0.0, risk_ratio) ** 2
        if headway_s < self.critical_s:
            critical_ratio = (self.critical_s - headway_s) / max(self.critical_s, 1.0)
            penalty += 10.0 + 30.0 * critical_ratio ** 2
        if trend < 0:
            penalty += min(5.0, abs(trend) * 2.0)
        return penalty

    @staticmethod
    def summarize(headways: list[float]) -> dict[str, float | None]:
        if not headways:
            return {'mean':None,'std':None}
        return {'mean':statistics.fmean(headways), 'std':statistics.pstdev(headways) if len(headways)>1 else 0.0}
