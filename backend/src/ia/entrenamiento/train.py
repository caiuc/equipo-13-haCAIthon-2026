from __future__ import annotations

from pathlib import Path
import json
import logging
import time

from simulacion.trafico.multi_agent_environment import MultiAgentTrafficEnv
from ia.modelos.agent_group import AgentGroup
from simulacion.buses.headway import HeadwayTracker
from simulacion.metricas.metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)


def _agent_epsilon(group: AgentGroup) -> float:
    agent = group.shared if group.architecture == 'shared' else next(iter(group.agents.values()))
    return agent.epsilon


def _agent_steps(group: AgentGroup) -> int:
    if group.architecture == 'shared':
        return group.shared.steps
    return sum(a.steps for a in group.agents.values())


def train(cfg: dict, logic: dict, episodes: int, seconds: float, out_dir: str | Path) -> dict:
    env=MultiAgentTrafficEnv(cfg,logic,seconds)
    base_seed=int(cfg['simulation'].get('seed',42))
    group=AgentGroup(env,logic,cfg,seed=base_seed)
    history=[]; out_dir=Path(out_dir); out_dir.mkdir(parents=True,exist_ok=True)
    for ep in range(1,int(episodes)+1):
        print(f"Episodio {ep}/{episodes}")
        # Cada episodio varía la semilla del entorno (llegadas, dwell, jitter) mientras
        # la red conserva su semilla base; así los 100 episodios no son simulaciones idénticas.
        episode_seed=base_seed+(ep-1)
        started=time.perf_counter()
        obs=env.reset(seed=episode_seed); totals={iid:0.0 for iid in logic}; losses={iid:[] for iid in logic}
        done=False
        while not done:
            masks=env.action_masks()
            actions=group.select_actions(obs,masks,training=True)
            next_obs,rewards,done,info=env.step(actions)
            next_masks=env.action_masks()
            learned=group.remember_and_learn(obs,actions,rewards,next_obs,done,next_masks)
            for iid in logic:
                if learned[iid] is not None: losses[iid].append(learned[iid])
                totals[iid]+=rewards[iid]
            obs=next_obs
        wall_time_s=time.perf_counter()-started
        headway_stats=HeadwayTracker.summarize(env.headways.observations)
        mean_headway=headway_stats['mean']; headway_std=headway_stats['std']
        headway_cv=(headway_std/mean_headway) if mean_headway and headway_std is not None and mean_headway>0 else None
        row={
            'episode':ep,
            'simulation_seed':episode_seed,
            'architecture':group.architecture,
            'epsilon':_agent_epsilon(group),
            'agent_steps':_agent_steps(group),
            'reward':totals,
            'loss':{iid:(sum(x)/len(x) if x else None) for iid,x in losses.items()},
            'bunching_events':len([e for e in env.headways.events if e['type']=='bunching_start']),
            'mean_headway_s':mean_headway,
            'headway_std_s':headway_std,
            'headway_cv':headway_cv,
            'wall_time_s':wall_time_s,
        }
        history.append(row)
        group.save(out_dir)
        logger.info(
            "Episode %s/%s seed=%s epsilon=%.3f steps=%s reward=%s bunching=%s headway=%s cv=%s wall=%.1fs",
            ep, episodes, episode_seed, row['epsilon'], row['agent_steps'], totals, row['bunching_events'],
            mean_headway, headway_cv, wall_time_s,
        )
    (out_dir/'training_history.json').write_text(json.dumps(history,indent=2,ensure_ascii=False),encoding='utf-8')
    metrics=MetricsCollector(cfg); metrics.write_json(env,out_dir/'last_episode_metrics.json')
    return {'history':history,'group':group,'env':env}
