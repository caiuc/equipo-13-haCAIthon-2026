from __future__ import annotations


class RewardCalculator:
    def __init__(self, cfg: dict, headway_tracker):
        self.w = cfg['reward']
        self.tracker = headway_tracker

    def calculate(self, camera: dict, buses: list[dict], completed_count: int, phase_changed: bool) -> tuple[float, dict[str,float]]:
        congestion = sum(v.get('density',0.0) + 0.2*v.get('queue',0.0) for v in camera.values())
        waiting = sum(v.get('queue',0.0) for v in camera.values())
        bus_wait = sum(1.0 for b in buses if b.get('speed_mps',1) <= 0.5)
        bus_travel_pressure = sum(min(2.0, b.get('eta_s',0.0)/120.0) for b in buses)
        headway_penalty = 0.0
        deviations=[]
        risk_count = 0
        critical_count = 0
        target=max(float(self.tracker.target_s),1.0)
        for b in buses:
            hw = b.get('headway_s')
            trend = b.get('headway_trend',0.0)
            if hw is not None:
                deviations.append((hw-target)/target)
            headway_penalty += self.tracker.progressive_penalty(hw, trend)
            if b.get('status') == 'riesgo_bunching': risk_count += 1
            if b.get('status') == 'critico_bunching': critical_count += 1
        mean_abs_dev = sum(abs(x) for x in deviations)/len(deviations) if deviations else 0.0
        regularity = (sum(x*x for x in deviations)/len(deviations)) if deviations else 0.0

        components = {
            'vehicle_outflow': self.w['vehicle_outflow'] * completed_count,
            'congestion': self.w['congestion'] * congestion,
            'waiting': self.w['waiting'] * waiting,
            'bus_travel': self.w['bus_travel'] * bus_travel_pressure,
            'bus_waiting': self.w['bus_waiting'] * bus_wait,
            'headway_regularity': self.w['headway_regularity'] * regularity,
            'headway_deviation': self.w['headway_deviation'] * (mean_abs_dev + headway_penalty),
            'bunching_risk': self.w['bunching_risk'] * risk_count,
            'bunching_confirmed': self.w['bunching_confirmed'] * critical_count,
            'phase_change': self.w['phase_change'] * (1.0 if phase_changed else 0.0),
        }
        return sum(components.values()), components
