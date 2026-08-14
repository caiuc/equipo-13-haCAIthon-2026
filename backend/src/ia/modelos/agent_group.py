from __future__ import annotations

from pathlib import Path
import json
import numpy as np

from ia.modelos.dqn import DQNAgent


class AgentGroup:
    """Gestiona DQN independientes o una única red compartida con padding.

    El modo compartido permite topologías con distintos tamaños de estado/acción:
    los estados se rellenan con ceros hasta `max_state_dim` y las fases inexistentes
    quedan bloqueadas en el action mask hasta `max_action_dim`.
    """
    def __init__(self, env, logic: dict, cfg: dict, seed: int = 42):
        self.env=env; self.logic=logic; self.cfg=cfg
        self.architecture=str(cfg['rl'].get('agent_architecture','independent')).lower()
        if self.architecture not in {'independent','shared'}:
            raise ValueError('rl.agent_architecture debe ser independent o shared')
        self.state_dims={iid:env.encoders[iid].size for iid in logic}
        self.action_dims={iid:len(logic[iid].phases) for iid in logic}
        if self.architecture=='shared':
            self.max_state_dim=max(self.state_dims.values())
            self.max_action_dim=max(self.action_dims.values())
            self.shared=DQNAgent(self.max_state_dim,self.max_action_dim,cfg['rl'],seed=seed)
            self.agents={}
        else:
            self.max_state_dim=None; self.max_action_dim=None; self.shared=None
            self.agents={iid:DQNAgent(self.state_dims[iid],self.action_dims[iid],cfg['rl'],seed=seed+k)
                         for k,iid in enumerate(logic)}

    def _state(self,iid: str,state: np.ndarray) -> np.ndarray:
        if self.architecture=='independent': return state
        out=np.zeros(self.max_state_dim,dtype=np.float32); out[:len(state)]=state; return out

    def _mask(self,iid: str,mask) -> np.ndarray:
        arr=np.asarray(mask,dtype=bool)
        if self.architecture=='independent': return arr
        out=np.zeros(self.max_action_dim,dtype=bool); out[:len(arr)]=arr; return out

    def select_actions(self, observations: dict, masks: dict, training: bool) -> dict[str,int]:
        actions={}
        for iid in self.logic:
            agent=self.shared if self.architecture=='shared' else self.agents[iid]
            actions[iid]=agent.select_action(self._state(iid,observations[iid]),self._mask(iid,masks[iid]),training=training)
            if actions[iid] >= self.action_dims[iid]:
                raise AssertionError('Action masking compartido permitió una fase inexistente')
        return actions

    def remember_and_learn(self, observations, actions, rewards, next_observations, done, next_masks) -> dict[str,float | None]:
        losses={}
        for iid in self.logic:
            agent=self.shared if self.architecture=='shared' else self.agents[iid]
            agent.remember(self._state(iid,observations[iid]),actions[iid],rewards[iid],
                           self._state(iid,next_observations[iid]),done,self._mask(iid,next_masks[iid]))
            losses[iid]=agent.learn()
        return losses

    def save(self, directory: str | Path) -> None:
        directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
        if self.architecture=='shared':
            self.shared.save(directory/'shared.pt')
        else:
            for iid,a in self.agents.items(): a.save(directory/f'{iid}.pt')
        meta={'architecture':self.architecture,'state_dims':self.state_dims,'action_dims':self.action_dims,
              'max_state_dim':self.max_state_dim,'max_action_dim':self.max_action_dim}
        (directory/'agents.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')

    def load(self, directory: str | Path) -> bool:
        directory=Path(directory)
        if self.architecture=='shared':
            p=directory/'shared.pt'
            if not p.exists(): return False
            self.shared.load(p); return True
        for iid,a in self.agents.items():
            p=directory/f'{iid}.pt'
            if not p.exists(): return False
            a.load(p)
        return True
