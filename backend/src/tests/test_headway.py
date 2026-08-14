from simulacion.buses.headway import HeadwayTracker
from common.domain_models import BusStatus


def tracker(): return HeadwayTracker(360,180,240,200)


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
