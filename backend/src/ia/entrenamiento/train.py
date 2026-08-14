from __future__ import annotations

import json
import logging
from pathlib import Path

from ia.modelos.agent_group import AgentGroup
from simulacion.metricas.metrics_collector import MetricsCollector
from simulacion.trafico.multi_agent_environment import MultiAgentTrafficEnv

logger = logging.getLogger(__name__)


def train(cfg: dict, logic: dict, episodes: int, seconds: float, out_dir: str | Path) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base_seed = int(cfg["simulation"].get("seed", 42))
    env = MultiAgentTrafficEnv(cfg, logic, episode_seconds=seconds, seed=base_seed)
    group = AgentGroup(env, logic, cfg, seed=base_seed)
    history = []

    for episode in range(1, int(episodes) + 1):
        observations = env.reset(seed=base_seed + episode - 1)
        totals = {iid: 0.0 for iid in logic}
        losses = {iid: [] for iid in logic}
        done = False
        decisions = 0

        while not done:
            masks = env.action_masks()
            actions = group.select_actions(observations, masks, training=True)
            next_observations, rewards, done, _ = env.step(actions)
            next_masks = env.action_masks()
            learned = group.remember_and_learn(
                observations, actions, rewards, next_observations, done, next_masks,
            )
            for iid in logic:
                totals[iid] += float(rewards[iid])
                if learned[iid] > 0.0:
                    losses[iid].append(float(learned[iid]))
            observations = next_observations
            decisions += 1

        row = {
            "episode": episode,
            "reward": totals,
            "totalReward": sum(totals.values()),
            "loss": {iid: (sum(values) / len(values) if values else 0.0) for iid, values in losses.items()},
            "epsilon": group.epsilons(),
            "bunchingEvents": int(env.stats["bunchingEvents"]),
            "completedCars": int(env.stats["completedCars"]),
            "completedBuses": int(env.stats["completedBuses"]),
            "decisions": decisions,
        }
        history.append(row)
        logger.info(
            "episode=%s/%s reward=%.2f bunching=%s eps=%s",
            episode, episodes, row["totalReward"], row["bunchingEvents"], row["epsilon"],
        )

    group.save(out_dir)
    (out_dir / "training_history.json").write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    MetricsCollector(cfg).write_json(env, out_dir / "last_episode_metrics.json")
    manifest = {
        "architecture": group.architecture,
        "episodes": int(episodes),
        "secondsPerEpisode": float(seconds),
        "seed": base_seed,
        "dtS": env.dt_s,
        "decisionIntervalS": env.decision_interval_s,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"history": history, "group": group, "env": env}
