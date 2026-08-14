import pytest

from ia.clingo.asp_engine import ClingoTopologyEngine, clingo


def test_facts_are_parametric_for_both_intersections(cfg):
    engine = ClingoTopologyEngine()
    for iid, intersection in cfg["intersections"].items():
        facts, _ = engine._facts_for_intersection(iid, intersection)
        assert f"intersection({iid})." in facts
        assert "lane_allows" in facts
        assert "straight" in facts


@pytest.mark.skipif(clingo is None, reason="clingo no está instalado en este entorno")
def test_clingo_derives_two_safe_axis_phases(cfg):
    logic = ClingoTopologyEngine().solve(cfg)
    assert set(logic) == {"i1", "i2"}
    for item in logic.values():
        assert len(item.phases) == 2
        ClingoTopologyEngine.assert_safe(item)
