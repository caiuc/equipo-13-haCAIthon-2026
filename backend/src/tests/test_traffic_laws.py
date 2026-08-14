from pathlib import Path

from common.domain_models import IntersectionLogic, Movement, Phase, Vehicle, VehicleKind
from config.scenario_loader import load_config
from simulacion.trafico.network import TrafficNetwork


SCENARIO = Path(__file__).resolve().parents[1] / 'config' / 'scenarios' / 'example_network.yaml'


def _quiet_network():
    cfg = load_config(SCENARIO)
    network = TrafficNetwork(cfg, {})
    network.reset()
    network._bus_schedule = []
    network._car_next_spawn = {origin: float('inf') for origin in network._od_by_origin}
    return cfg, network


def _vehicle(vehicle_id: str, route: list[str], position: float, speed: float = 10.0):
    return Vehicle(
        id=vehicle_id,
        kind=VehicleKind.CAR,
        route_id=None,
        route_links=route,
        position_m=position,
        speed_mps=speed,
        desired_speed_mps=13.0,
        length_m=4.5,
        max_accel=2.0,
        comfortable_decel=3.0,
        reaction_time_s=1.0,
    )


def test_red_light_stops_front_before_intersection_square():
    _, network = _quiet_network()
    car = _vehicle('red-car', ['w_i1', 'i1_i2', 'i2_e'], 330.0, 12.0)
    network.vehicles[car.id] = car
    stop_line = network._stop_line_position(car)
    assert stop_line is not None

    for _ in range(80):
        network.step(lambda *_: False)

    assert car.current_link == 'w_i1'
    assert car.position_m <= stop_line + 1e-9
    assert car.speed_mps == 0.0
    # El frente queda fuera del cuadrado: 380 - (37 + 4) = 339 m.
    assert stop_line < 380.0 - network._intersection_half_extent_m('i1')


def test_conflicting_vehicle_waits_until_intersection_is_clear():
    _, network = _quiet_network()
    west = Movement('i1', 'w_through', 'west', 'east', 'straight')
    north = Movement('i1', 'n_through', 'north', 'south', 'straight')
    logic = IntersectionLogic(
        'i1',
        [west, north],
        {frozenset((west.key, north.key))},
        [Phase(0, [west]), Phase(1, [north])],
    )
    network.logic['i1'] = logic

    west_car = _vehicle('west-car', ['w_i1', 'i1_i2', 'i2_e'], 338.8, 10.0)
    north_car = _vehicle('north-car', ['n1_i1', 'i1_s1'], 348.8, 10.0)
    network.vehicles = {west_car.id: west_car, north_car.id: north_car}

    # Se fuerza callback verde para ambos para comprobar que la caja de conflicto
    # sigue protegiendo físicamente la intersección incluso ante una entrada hostil.
    network.step(lambda *_: True)

    entries = [v.metadata.get('intersection_entry') for v in network.vehicles.values()]
    active = [entry for entry in entries if entry]
    assert len(active) == 1
    waiting = west_car if not west_car.metadata.get('intersection_entry') else north_car
    waiting_stop_line = network._stop_line_position(waiting)
    assert waiting_stop_line is not None
    assert waiting.position_m <= waiting_stop_line + 1e-9


def test_same_lane_vehicles_never_overlap_after_safety_pass():
    _, network = _quiet_network()
    route = ['w_i1', 'i1_i2', 'i2_e']
    leader = _vehicle('leader', route, 100.0, 0.0)
    follower = _vehicle('follower', route, 98.0, 8.0)
    network.vehicles = {leader.id: leader, follower.id: follower}

    network._enforce_minimum_separation()

    gap = leader.position_m - leader.length_m - follower.position_m
    assert gap >= network.minimum_gap_m - 1e-9
    assert follower.speed_mps <= leader.speed_mps


def test_lane_assignment_is_stable_and_not_visual_hash_based():
    _, network = _quiet_network()
    left = _vehicle('anything-a', ['w_i1', 'i1_n1'], 10.0)
    straight = _vehicle('anything-b', ['w_i1', 'i1_i2', 'i2_e'], 10.0)
    assert network.lane_slot(left) == 0
    assert network.lane_id(left) == 'w_left'
    assert network.lane_slot(straight) == 1
    assert network.lane_id(straight) == 'w_through'
