from simulacion.vehiculos.gipps import gipps_next_speed


def test_gipps_accelerates_in_free_flow():
    v=gipps_next_speed(5,15,2,3,1,None)
    assert 5 < v <= 15


def test_gipps_reacts_to_close_stopped_leader():
    free=gipps_next_speed(10,15,2,3,1,None)
    constrained=gipps_next_speed(10,15,2,3,1,3,0)
    assert constrained < free
    assert constrained >= 0
