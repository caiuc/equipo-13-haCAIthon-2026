from __future__ import annotations

from simulacion.metricas.metrics_collector import MetricsCollector
from simulacion.trafico.multi_agent_environment import MultiAgentTrafficEnv


def run_baseline_simulation(cfg: dict, logic: dict, seconds: float):
    env = MultiAgentTrafficEnv(cfg, logic, seconds)
    env.reset()
    collector = MetricsCollector(cfg)
    done = False
    while not done:
        actions = env.heuristic_actions()
        _, rewards, done, _ = env.step(actions)
        collector.sample(env, rewards)
    return env, collector.summarize(env)
