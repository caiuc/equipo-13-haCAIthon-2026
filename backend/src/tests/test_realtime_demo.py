from pathlib import Path
from types import SimpleNamespace

from common.domain_models import IntersectionLogic, Movement, Phase
from config.scenario_loader import load_config
from simulacion.telemetria.snapshot import build_network_snapshot
from simulacion.trafico.network import TrafficNetwork
from simulacion.trafico.signal_controller import SignalController


SCENARIO = Path(__file__).resolve().parents[1] / "config" / "scenarios" / "example_network.yaml"


def test_demo_spawns_and_moves_cars_and_buses_from_first_micro_step():
    cfg = load_config(SCENARIO)
    network = TrafficNetwork(cfg, {})
    network.reset()

    network.step(lambda *_: True)
    first = {vehicle.id: vehicle.position_m for vehicle in network.vehicles.values()}
    buses = [vehicle for vehicle in network.vehicles.values() if vehicle.kind.value == "BUS"]
    cars = [vehicle for vehicle in network.vehicles.values() if vehicle.kind.value == "CAR"]

    assert len(buses) >= 2
    # Los orígenes oeste/este pueden quedar temporalmente reservados por los buses
    # iniciales; los autos esperan en vez de aparecer físicamente superpuestos.
    assert len(cars) >= 4

    for _ in range(4):
        network.step(lambda *_: True)

    second = {vehicle.id: vehicle.position_m for vehicle in network.vehicles.values()}
    assert any(second.get(vehicle_id, position) > position for vehicle_id, position in first.items())


def test_snapshot_changes_branch_signal_green_yellow_red_during_transition():
    cfg = load_config(SCENARIO)
    west = Movement("i1", "w_through", "west", "east", "straight")
    north = Movement("i1", "n_through", "north", "south", "straight")
    logic = IntersectionLogic(
        "i1",
        [west, north],
        {frozenset((west.key, north.key))},
        [Phase(0, [west]), Phase(1, [north])],
    )
    controller = SignalController(logic, min_green_s=1.0, yellow_s=0.6, max_red_s=25.0)
    env = SimpleNamespace(
        network=SimpleNamespace(time_s=0.0, vehicles={}),
        controllers={"i1": controller},
        logic={"i1": logic},
        last_actions={"i1": 0},
        last_reward_components={},
        decision_count=1,
    )

    initial = build_network_snapshot(cfg, env)["intersections"]["i1"]["branchSignals"]
    assert initial["west"] == "GREEN"
    assert initial["north"] == "RED"

    controller.tick(1.0)
    env.last_actions = {"i1": 1}
    assert controller.request_phase(1)
    yellow = build_network_snapshot(cfg, env)["intersections"]["i1"]["branchSignals"]
    assert yellow["west"] == "YELLOW"
    assert yellow["north"] == "RED"

    controller.tick(0.6)
    changed = build_network_snapshot(cfg, env)["intersections"]["i1"]["branchSignals"]
    assert changed["west"] == "RED"
    assert changed["north"] == "GREEN"
