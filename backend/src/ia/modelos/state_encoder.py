from __future__ import annotations

import numpy as np
from common.domain_models import BusStatus


class StateEncoder:
    """Vector fijo por intersección a partir de cantidades variables de entidades."""
    PER_MOVEMENT = 6
    BUS_FEATURES = 8
    NEIGHBOR_FEATURES = 6

    def __init__(self, logic, cfg: dict):
        self.logic = logic
        self.cfg = cfg
        self.movement_keys = [m.key for m in logic.movements]
        self.size = len(self.movement_keys)*self.PER_MOVEMENT + self.BUS_FEATURES + self.NEIGHBOR_FEATURES + len(logic.phases) + 2

    def encode(self, camera: dict, buses: list[dict], messages: list, controller) -> np.ndarray:
        values: list[float] = []
        roi = float(self.cfg['simulation'].get('camera_roi_m',60))
        for key in self.movement_keys:
            m = camera.get(key,{})
            values.extend([
                min(1.0, m.get('density',0)*roi/12.0),
                min(1.0, m.get('inflow',0)*5.0),
                min(1.0, m.get('outflow',0)*5.0),
                min(1.0, m.get('queue',0)/10.0),
                min(1.0, m.get('mean_speed',0)/20.0),
                min(1.0, m.get('green_time',0)/max(float(self.cfg['signals']['max_red_s']),1.0)),
            ])

        target = float(self.cfg['transit']['target_headway_s'])
        if buses:
            closest = min(buses,key=lambda b:b['eta_s'])
            late = sum(1 for b in buses if b['status']==BusStatus.LATE.value)
            early = sum(1 for b in buses if b['status']==BusStatus.EARLY.value)
            risky = sum(1 for b in buses if b['status'] in (BusStatus.RISK.value,BusStatus.CRITICAL.value))
            hw = closest.get('headway_s') or target
            values.extend([
                min(1.0,len(buses)/6.0), min(1.0,closest['distance_m']/max(self.cfg['transit']['gps_horizon_m'],1)),
                min(1.0,closest['eta_s']/120.0), np.clip((hw-target)/target,-1,1),
                np.clip(closest.get('headway_trend',0)/2,-1,1), min(1,late/3), min(1,early/3), min(1,risky/3),
            ])
        else:
            values.extend([0.0]*self.BUS_FEATURES)

        if messages:
            congestion = max(m.congestion for m in messages)
            up_buses = sum(len(m.upcoming_buses) for m in messages)
            critical = sum(len(m.critical_events) for m in messages)
            values.extend([min(1,congestion), min(1,up_buses/6), min(1,critical/3),
                           min(1,len(messages)/4),
                           min(1,sum(1 for m in messages if m.upcoming_buses)/3),
                           min(1,sum(len(m.congested_movements) for m in messages)/8)])
        else:
            values.extend([0.0]*self.NEIGHBOR_FEATURES)

        values.extend([1.0 if i==controller.phase_index else 0.0 for i in range(len(self.logic.phases))])
        values.extend([min(1.0,controller.elapsed_s/60.0), 1.0 if controller.mode.value=='YELLOW' else 0.0])
        arr = np.asarray(values,dtype=np.float32)
        assert arr.shape == (self.size,)
        return arr
