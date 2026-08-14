from __future__ import annotations

from simulacion.metricas.metrics_collector import MetricsCollector
from simulacion.telemetria.snapshot import build_network_snapshot
from simulacion.trafico.multi_agent_environment import MultiAgentTrafficEnv


def run_baseline_simulation(cfg: dict, logic: dict, seconds: float, max_frames: int = 120):
    env = MultiAgentTrafficEnv(cfg, logic, episode_seconds=seconds)
    observations = env.reset()
    del observations
    timeline = [build_network_snapshot(cfg, env)]
    done = False
    decision = 0
    capture_every = max(1, int(max(1, seconds / env.decision_interval_s) / max_frames))
    while not done:
        actions = env.heuristic_actions()
        _, _, done, _ = env.step(actions)
        decision += 1
        if decision % capture_every == 0 or done:
            timeline.append(build_network_snapshot(cfg, env))
    return env, MetricsCollector(cfg).summarize(env), timeline
