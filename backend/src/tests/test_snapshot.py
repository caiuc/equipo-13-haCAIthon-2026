from pathlib import Path
from types import SimpleNamespace

from config.scenario_loader import load_config
from common.domain_models import Bus, BusStatus, VehicleKind
from simulacion.telemetria.snapshot import build_network_snapshot


def test_snapshot_is_frontend_friendly():
    cfg = load_config(Path(__file__).resolve().parents[1] / "config" / "scenarios" / "example_network.yaml")
    bus = Bus(
        id="bus-x",
        kind=VehicleKind.BUS,
        route_id="r1",
        route_links=[next(iter(cfg["links"]))],
        status=BusStatus.NORMAL,
    )
    controller = SimpleNamespace(
        phase_index=0,
        mode=SimpleNamespace(value="GREEN"),
        elapsed_s=2.0,
        action_mask=lambda: [True],
    )
    movement = SimpleNamespace(key="lane->east")
    logic = {"i1": SimpleNamespace(phases=[SimpleNamespace(movements=[movement])])}
    env = SimpleNamespace(
        network=SimpleNamespace(time_s=1.0, vehicles={bus.id: bus}),
        controllers={"i1": controller},
        logic=logic,
    )
    snapshot = build_network_snapshot(cfg, env)
    assert snapshot["vehicles"][0]["kind"] == "BUS"
    assert snapshot["intersections"]["i1"]["activeMovements"] == ["lane->east"]
    assert "nodes" in snapshot and "links" in snapshot
