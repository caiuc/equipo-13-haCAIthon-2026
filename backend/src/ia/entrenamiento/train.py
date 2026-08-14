from __future__ import annotations

from pathlib import Path
import json
import logging

from simulacion.trafico.multi_agent_environment import MultiAgentTrafficEnv
from ia.modelos.agent_group import AgentGroup
from simulacion.metricas.metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)


def train(cfg: dict, logic: dict, episodes: int, seconds: float, out_dir: str | Path) -> dict:
    env=MultiAgentTrafficEnv(cfg,logic,seconds)
    group=AgentGroup(env,logic,cfg,seed=int(cfg['simulation'].get('seed',42)))
    history=[]; out_dir=Path(out_dir); out_dir.mkdir(parents=True,exist_ok=True)
    for ep in range(1,int(episodes)+1):
        obs=env.reset(); totals={iid:0.0 for iid in logic}; losses={iid:[] for iid in logic}
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
        row={'episode':ep,'architecture':group.architecture,'reward':totals,
             'loss':{iid:(sum(x)/len(x) if x else None) for iid,x in losses.items()},
             'bunching_events':len([e for e in env.headways.events if e['type']=='bunching_start'])}
        history.append(row)
        group.save(out_dir)
        logger.info("Episode %s/%s [%s]: reward=%s bunching=%s", ep, episodes, group.architecture, totals, row["bunching_events"])
    (out_dir/'training_history.json').write_text(json.dumps(history,indent=2,ensure_ascii=False),encoding='utf-8')
    metrics=MetricsCollector(cfg); metrics.write_json(env,out_dir/'last_episode_metrics.json')
    return {'history':history,'group':group,'env':env}
