from __future__ import annotations

import math
from pathlib import Path

from ia.modelos.agent_group import AgentGroup
from simulacion.metricas.metrics_collector import MetricsCollector
from simulacion.telemetria.snapshot import build_network_snapshot
from simulacion.trafico.multi_agent_environment import MultiAgentTrafficEnv


def evaluate(cfg: dict, logic: dict, seconds: float, checkpoints: str | Path | None = None, metrics_path: str | Path | None = None, max_frames: int = 140, seed: int | None = None):
    env = MultiAgentTrafficEnv(cfg, logic, seconds)
    obs = env.reset(seed=seed)
    group = None
    if checkpoints:
        candidate = AgentGroup(env, logic, cfg, seed=100)
        if candidate.load(checkpoints):
            group = candidate

    collector = MetricsCollector(cfg)
    total_steps = max(1, math.ceil(float(seconds) / env.decision_interval))
    capture_every = max(1, math.ceil(total_steps / max(1, max_frames)))
    timeline = [build_network_snapshot(cfg, env)]

    done = False
    step_index = 0
    while not done:
        actions = group.select_actions(obs, env.action_masks(), training=False) if group else env.heuristic_actions()
        obs, rewards, done, _ = env.step(actions)
        collector.sample(env, rewards)
        step_index += 1
        if step_index % capture_every == 0 or done:
            timeline.append(build_network_snapshot(cfg, env))

    if not timeline or timeline[-1]["timeS"] != env.network.time_s:
        timeline.append(build_network_snapshot(cfg, env))

    summary = collector.summarize(env)
    if metrics_path:
        collector.write_json(env, metrics_path)
    return env, summary, timeline
