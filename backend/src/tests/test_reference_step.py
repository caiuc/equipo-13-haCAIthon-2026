from simulacion.telemetria.snapshot import build_network_snapshot
from simulacion.trafico.multi_agent_environment import MultiAgentTrafficEnv


def test_one_dqn_step_emits_25_real_substeps(cfg, logic):
    env = MultiAgentTrafficEnv(cfg, logic, episode_seconds=30, seed=42)
    frames = []
    env.step({"i1": 0, "i2": 0}, on_substep=lambda current: frames.append(build_network_snapshot(cfg, current)) or True)
    assert len(frames) == 25
    assert frames[0]["timeS"] == 0.2
    assert round(frames[-1]["timeS"], 6) == 5.0


def test_vehicles_move_between_microframes_and_buses_exist_from_start(cfg, logic):
    env = MultiAgentTrafficEnv(cfg, logic, episode_seconds=30, seed=42)
    ids = {vehicle.id for vehicle in env.active_vehicles()}
    assert "B1-1" in ids and "B2-1" in ids
    frames = []
    env.step({"i1": 0, "i2": 0}, on_substep=lambda current: frames.append(build_network_snapshot(cfg, current)) or True)
    first = {v["id"]: (v["x"], v["y"]) for v in frames[0]["vehicles"]}
    fifth = {v["id"]: (v["x"], v["y"]) for v in frames[4]["vehicles"]}
    common = set(first) & set(fifth)
    assert common
    assert any(first[vid] != fifth[vid] for vid in common)
