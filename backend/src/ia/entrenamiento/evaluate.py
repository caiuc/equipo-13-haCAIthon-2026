from __future__ import annotations

from pathlib import Path
from simulacion.trafico.multi_agent_environment import MultiAgentTrafficEnv
from ia.modelos.agent_group import AgentGroup
from simulacion.metricas.metrics_collector import MetricsCollector


def evaluate(cfg: dict, logic: dict, seconds: float, checkpoints: str | Path | None = None, metrics_path: str | Path | None = None):
    env=MultiAgentTrafficEnv(cfg,logic,seconds); obs=env.reset(); group=None
    if checkpoints:
        candidate=AgentGroup(env,logic,cfg,seed=100)
        if candidate.load(checkpoints): group=candidate
    collector=MetricsCollector(cfg); done=False
    while not done:
        if group:
            actions=group.select_actions(obs,env.action_masks(),training=False)
        else:
            actions=env.heuristic_actions()
        obs,rewards,done,_=env.step(actions); collector.sample(env,rewards)
    summary=collector.summarize(env)
    if metrics_path: collector.write_json(env,metrics_path)
    return env,summary
