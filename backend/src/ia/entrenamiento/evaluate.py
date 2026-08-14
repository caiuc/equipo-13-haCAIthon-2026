from __future__ import annotations

import math
from pathlib import Path

from ia.modelos.agent_group import AgentGroup
from simulacion.metricas.metrics_collector import MetricsCollector
from simulacion.telemetria.snapshot import build_network_snapshot
from simulacion.trafico.multi_agent_environment import MultiAgentTrafficEnv


def evaluate(cfg: dict, logic: dict, seconds: float, checkpoints: str | Path | None = None, max_frames: int = 120):
    env = MultiAgentTrafficEnv(cfg, logic, episode_seconds=seconds)
    observations = env.reset()
    group = None
    if checkpoints:
        candidate = AgentGroup(env, logic, cfg, seed=100)
        if not candidate.load(checkpoints):
            raise FileNotFoundError("Checkpoint incompleto")
        group = candidate

    total_decisions = max(1, math.ceil(seconds / env.decision_interval_s))
    capture_every = max(1, math.ceil(total_decisions / max_frames))
    timeline = [build_network_snapshot(cfg, env)]
    done = False
    decision = 0
    while not done:
        masks = env.action_masks()
        actions = group.select_actions(observations, masks, training=False) if group else env.heuristic_actions()
        observations, _, done, _ = env.step(actions)
        decision += 1
        if decision % capture_every == 0 or done:
            timeline.append(build_network_snapshot(cfg, env))

    return env, MetricsCollector(cfg).summarize(env), timeline
