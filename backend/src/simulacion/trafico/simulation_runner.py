from __future__ import annotations

import math

from simulacion.metricas.metrics_collector import MetricsCollector
from simulacion.telemetria.snapshot import build_network_snapshot
from simulacion.trafico.multi_agent_environment import MultiAgentTrafficEnv


def _should_capture(step_index: int, total_steps: int, max_frames: int) -> bool:
    if max_frames <= 0:
        return False
    every = max(1, math.ceil(total_steps / max_frames))
    return step_index % every == 0 or step_index >= total_steps


def run_baseline_simulation(cfg: dict, logic: dict, seconds: float, max_frames: int = 140):
    env = MultiAgentTrafficEnv(cfg, logic, seconds)
    env.reset()
    collector = MetricsCollector(cfg)
    total_steps = max(1, math.ceil(float(seconds) / env.decision_interval))
    timeline = [build_network_snapshot(cfg, env)]

    done = False
    step_index = 0
    while not done:
        actions = env.heuristic_actions()
        _, rewards, done, _ = env.step(actions)
        collector.sample(env, rewards)
        step_index += 1
        if _should_capture(step_index, total_steps, max_frames):
            timeline.append(build_network_snapshot(cfg, env))

    if not timeline or timeline[-1]["timeS"] != env.network.time_s:
        timeline.append(build_network_snapshot(cfg, env))
    return env, collector.summarize(env), timeline
