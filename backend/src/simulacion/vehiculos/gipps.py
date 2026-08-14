from __future__ import annotations

import math


def gipps_next_speed(
    speed: float,
    desired_speed: float,
    max_accel: float,
    comfortable_decel: float,
    reaction_time: float,
    gap: float | None,
    leader_speed: float = 0.0,
    leader_decel: float = 3.0,
) -> float:
    """Velocidad siguiente según una forma estable del modelo de Gipps.

    Si no hay líder, domina el término de aceleración libre. Con líder se aplica
    además el límite de frenado seguro. Todas las magnitudes están en SI.
    """
    v = max(0.0, float(speed))
    V = max(0.1, float(desired_speed))
    a = max(0.05, float(max_accel))
    b = max(0.05, float(comfortable_decel))
    tau = max(0.05, float(reaction_time))

    v_free = v + 2.5 * a * tau * (1 - v / V) * math.sqrt(max(0.0, 0.025 + v / V))
    v_next = min(V, max(0.0, v_free))

    if gap is not None:
        s = max(0.0, float(gap))
        bhat = max(0.05, float(leader_decel))
        inside = max(0.0, b*b*tau*tau - b * (2*s - v*tau - (leader_speed**2)/bhat))
        v_safe = b * tau + math.sqrt(inside)
        v_next = min(v_next, max(0.0, v_safe))
    return v_next
