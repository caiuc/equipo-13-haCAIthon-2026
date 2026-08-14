from pathlib import Path
import pytest
from config.scenario_loader import load_config
from ia.clingo.asp_engine import ClingoTopologyEngine, clingo

pytestmark=pytest.mark.skipif(clingo is None, reason='clingo no está instalado en este entorno')


def test_clingo_derives_safe_phases():
    cfg=load_config(str(Path(__file__).resolve().parents[1] / 'config' / 'scenarios' / 'example_network.yaml'))
    logic=ClingoTopologyEngine().solve(cfg)
    assert set(logic)=={'i1','i2'}
    for lg in logic.values():
        assert len(lg.movements)==12
        assert lg.phases
        ClingoTopologyEngine.assert_safe(lg)
