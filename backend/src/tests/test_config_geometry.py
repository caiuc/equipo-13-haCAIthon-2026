from pathlib import Path
from config.scenario_loader import load_config
from ia.clingo.geometry import build_candidates, geometric_conflicts, target_branch


def test_example_config_loads():
    cfg=load_config(str(Path(__file__).resolve().parents[1] / 'config' / 'scenarios' / 'example_network.yaml'))
    assert len(cfg['intersections'])==2
    assert target_branch(cfg['intersections']['i1']['branches'],'west','straight')=='east'
    assert target_branch(cfg['intersections']['i1']['branches'],'west','left')=='north'


def test_geometry_generates_movements_and_conflicts():
    cfg=load_config(str(Path(__file__).resolve().parents[1] / 'config' / 'scenarios' / 'example_network.yaml'))
    candidates=build_candidates(cfg['intersections']['i1'])
    assert len(candidates)==12
    conflicts=geometric_conflicts(candidates)
    assert conflicts
