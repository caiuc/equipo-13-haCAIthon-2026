from __future__ import annotations

import json
from pathlib import Path

from ia.modelos.dqn import DQNAgent


class AgentGroup:
    """Un DQN independiente por intersección, como recomienda el prompt maestro."""

    architecture = "independent"

    def __init__(self, env, logic: dict, cfg: dict, seed: int = 42):
        self.logic = logic
        self.agents = {
            iid: DQNAgent(env.observation_size(iid), env.action_size(iid), cfg["rl"], seed=seed + index)
            for index, iid in enumerate(logic)
        }

    def select_actions(self, observations: dict, masks: dict, training: bool) -> dict[str, int]:
        return {
            iid: self.agents[iid].select_action(observations[iid], masks[iid], training=training)
            for iid in self.logic
        }

    def remember_and_learn(self, observations, actions, rewards, next_observations, done, next_masks):
        losses = {}
        for iid, agent in self.agents.items():
            agent.remember(observations[iid], actions[iid], rewards[iid], next_observations[iid], done, next_masks[iid])
            losses[iid] = agent.train_step()
        return losses

    def epsilons(self) -> dict[str, float]:
        return {iid: agent.current_epsilon() for iid, agent in self.agents.items()}

    def save(self, directory: str | Path) -> None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        for iid, agent in self.agents.items():
            agent.save(directory / f"{iid}.pt")
        metadata = {
            "architecture": self.architecture,
            "intersections": list(self.agents),
            "stateDimensions": {iid: agent.state_size for iid, agent in self.agents.items()},
            "actionDimensions": {iid: agent.action_size for iid, agent in self.agents.items()},
        }
        (directory / "agents.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    def load(self, directory: str | Path) -> bool:
        directory = Path(directory)
        for iid, agent in self.agents.items():
            path = directory / f"{iid}.pt"
            if not path.is_file():
                return False
            agent.load(path)
        return True
