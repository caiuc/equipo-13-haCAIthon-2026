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
    def __init__(self, target_s: float, critical_s: float, risk_s: float, imminent_s: float):
        self.target_s = float(target_s)
        self.critical_s = float(critical_s)
        self.risk_s = float(risk_s)
        self.imminent_s = float(imminent_s)
        self.history: dict[str, deque[tuple[float, float]]] = defaultdict(lambda: deque(maxlen=8))
        self.events: list[dict] = []
        self._active_bunching: set[tuple[str, str]] = set()

    def classify(self, headway_s: float | None, trend: float = 0.0) -> BusStatus:
        if headway_s is None:
            return BusStatus.NORMAL
        if headway_s < self.critical_s:
            return BusStatus.CRITICAL
        if headway_s < self.imminent_s or (headway_s < self.risk_s and trend < -0.25):
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
            hist = self.history[key]
            hist.append((now_s, headway_s))
            if len(hist) >= 2:
                dt = hist[-1][0] - hist[0][0]
                if dt > 0:
                    trend = (hist[-1][1] - hist[0][1]) / dt
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
    def summarize(headways: list[float]) -> dict[str, float]:
        if not headways:
            return {'mean':0.0,'std':0.0}
        return {'mean':statistics.fmean(headways), 'std':statistics.pstdev(headways) if len(headways)>1 else 0.0}
