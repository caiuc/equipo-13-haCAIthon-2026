from pathlib import Path
import random
from config.scenario_loader import load_config
from simulacion.rutas.route_planner import RoutePlanner


def test_generated_routes_are_topologically_legal():
    cfg=load_config(str(Path(__file__).resolve().parents[1] / 'config' / 'scenarios' / 'example_network.yaml'))
    planner=RoutePlanner(cfg,random.Random(1))
    route=planner.route('west_src','north2_dst')
    assert route
    assert planner.is_legal_link_route(route)
