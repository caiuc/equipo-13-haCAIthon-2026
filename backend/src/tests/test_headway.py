from simulacion.buses.headway import HeadwayTracker
from common.domain_models import Bus, BusStatus, VehicleKind


def tracker(**overrides):
    kwargs = dict(target_s=360, critical_s=180, risk_s=240, imminent_s=200)
    kwargs.update(overrides)
    return HeadwayTracker(**kwargs)


def _follower(bus_id):
    return Bus(id=bus_id, kind=VehicleKind.BUS, route_id='B1', route_links=['a'])


def test_progressive_bunching_penalty_dominates():
    t=tracker()
    normal=t.progressive_penalty(350,0)
    risk=t.progressive_penalty(220,-0.2)
    critical=t.progressive_penalty(120,-0.5)
    assert normal < risk < critical


def test_classification():
    t=tracker()
    assert t.classify(360)==BusStatus.NORMAL
    assert t.classify(160)==BusStatus.CRITICAL
    assert t.classify(500)==BusStatus.LATE


# Test 1 — headway exacto: el líder pasó por progress=1255 en t=105, el seguidor
# pasa por el mismo progress en t=465 -> headway == 360 s.
def test_temporal_headway_matches_manual_example():
    t = tracker()
    t.record_progress('leader', 100.0, 1200.0)
    t.record_progress('leader', 105.0, 1255.0)
    t.record_progress('leader', 110.0, 1310.0)
    hw = t.temporal_headway('leader', 1255.0, 465.0)
    assert hw is not None
    assert abs(hw - 360.0) < 1.0


# Test 2 — independiente de la velocidad: el mismo resultado (360 s) debe darse
# aunque el líder se haya movido a velocidades completamente distintas.
def test_temporal_headway_independent_of_leader_speed():
    slow = tracker()
    slow.record_progress('leader', 0.0, 0.0)
    slow.record_progress('leader', 100.0, 500.0)  # 5 m/s
    hw_slow = slow.temporal_headway('leader', 500.0, 460.0)

    fast = tracker()
    fast.record_progress('leader', 0.0, 0.0)
    fast.record_progress('leader', 50.0, 500.0)  # 10 m/s
    hw_fast = fast.temporal_headway('leader', 500.0, 410.0)

    assert hw_slow is not None and hw_fast is not None
    assert abs(hw_slow - 360.0) < 1e-6
    assert abs(hw_fast - 360.0) < 1e-6


def test_temporal_headway_none_without_enough_history():
    t = tracker()
    assert t.temporal_headway('leader', 500.0, 100.0) is None


# Test 3 — tendencia negativa clara para una serie de headways decrecientes.
def test_trend_negative_for_shrinking_headway():
    t = tracker()
    follower = _follower('f1')
    trend = 0.0
    for i, hw in enumerate([360, 352, 345, 337, 330]):
        snap = t.update_pair('B1', follower, None, i * t.trend_sample_s, float(hw))
        trend = snap.trend_s_per_s
    assert trend < -0.1


# Test 4 — tendencia cercana a cero para oscilaciones pequeñas de ruido.
def test_trend_stable_for_noisy_headway():
    t = tracker()
    follower = _follower('f2')
    trend = 0.0
    for i, hw in enumerate([360, 359, 361, 360, 358, 361, 360]):
        snap = t.update_pair('B1', follower, None, i * t.trend_sample_s, float(hw))
        trend = snap.trend_s_per_s
    assert abs(trend) < 0.05


# Test 5 — clasificación crítica sigue funcionando bajo el umbral configurado.
def test_critical_classification_below_threshold():
    t = tracker()
    assert t.classify(179.0) == BusStatus.CRITICAL
    assert t.classify(180.0) != BusStatus.CRITICAL
