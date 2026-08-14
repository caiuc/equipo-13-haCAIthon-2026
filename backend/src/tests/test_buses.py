from common.domain_models import Bus
from simulacion.trafico.multi_agent_environment import MultiAgentTrafficEnv


def test_second_bus_is_dispatched_and_headway_is_measured(cfg, logic):
    env = MultiAgentTrafficEnv(cfg, logic, episode_seconds=90, seed=4)
    for _ in range(14):
        env.step(env.heuristic_actions())
    buses = [v for v in env.active_vehicles() if isinstance(v, Bus)]
    assert env.stats["spawnedBuses"] >= 4
    assert any(bus.headway_s is not None for bus in buses) or env.headway_samples
