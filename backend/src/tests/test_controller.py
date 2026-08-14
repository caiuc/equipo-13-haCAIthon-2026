from simulacion.trafico.signal_controller import SignalController
from common.domain_models import IntersectionLogic, Movement, Phase, SignalMode


def make_logic():
    a=Movement('i','a','west','east','straight')
    b=Movement('i','b','north','south','straight')
    return IntersectionLogic('i',[a,b],{frozenset((a.key,b.key))},[Phase(0,[a]),Phase(1,[b])])


def test_min_green_and_yellow_are_enforced():
    c=SignalController(make_logic(),10,3,90)
    assert c.action_mask()==[True,False]
    c.tick(10)
    assert c.action_mask()==[True,True]
    assert c.request_phase(1)
    assert c.mode==SignalMode.YELLOW
    assert not c.is_green('b','south')
    c.tick(3)
    assert c.mode==SignalMode.GREEN and c.phase_index==1
    assert c.is_green('b','south')


def test_runtime_safety_check():
    c=SignalController(make_logic(),1,1,90)
    c.assert_safe_phase(0)
    c.assert_safe_phase(1)
