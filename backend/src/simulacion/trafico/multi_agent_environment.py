from __future__ import annotations

from collections import defaultdict
import statistics

from simulacion.trafico.signal_controller import SignalController
from common.domain_models import Bus, NeighborMessage
from simulacion.percepcion.camera import CameraPerception
from simulacion.percepcion.gps import GPSPerception
from simulacion.comunicacion.message_bus import MessageBus
from simulacion.recompensas.reward_calculator import RewardCalculator
from ia.modelos.state_encoder import StateEncoder
from simulacion.trafico.network import TrafficNetwork
from simulacion.buses.headway import HeadwayTracker


class MultiAgentTrafficEnv:
    def __init__(self, cfg: dict, logic: dict, episode_seconds: float = 900.0):
        self.cfg=cfg; self.logic=logic; self.episode_seconds=float(episode_seconds)
        self.decision_interval=float(cfg['rl'].get('decision_interval_s',5.0))
        self.encoders={iid:StateEncoder(lg,cfg) for iid,lg in logic.items()}
        self._build_runtime()

    def _build_runtime(self):
        self.network=TrafficNetwork(self.cfg,self.logic); self.network.reset()
        s=self.cfg['signals']
        effective_min=max(float(s['min_green_s']),float(s.get('pedestrian_min_green_s',0)))
        self.controllers={iid:SignalController(lg,effective_min,s['yellow_s'],s['max_red_s']) for iid,lg in self.logic.items()}
        t=self.cfg['transit']
        self.headways=HeadwayTracker(t['target_headway_s'],t['critical_headway_s'],t['risk_headway_s'],t['imminent_headway_s'])
        self.camera=CameraPerception(self.cfg,self.network); self.gps=GPSPerception(self.cfg,self.network)
        self.messages=MessageBus(self.cfg)
        self.rewards={iid:RewardCalculator(self.cfg,self.headways) for iid in self.logic}
        self.last_reward_components={}
        self.last_observations={}
        self.last_raw={}
        self._last_completed=0

    def reset(self):
        self._build_runtime()
        self._update_headways()
        obs=self._observe_and_message()
        self.last_observations=obs
        return obs

    def action_masks(self) -> dict[str,list[bool]]:
        return {iid:c.action_mask() for iid,c in self.controllers.items()}

    def signal_green(self,iid,lane,to)->bool:
        c=self.controllers.get(iid)
        return c.is_green(lane,to) if c else True

    def _route_progress(self,b: Bus) -> float:
        route=b.route_links
        return sum(float(self.cfg['links'][lid]['length_m']) for lid in route[:b.link_index]) + b.position_m

    def _update_headways(self):
        by_route=defaultdict(list)
        for b in self.network.active_buses():
            by_route[b.route_id].append(b)
        nominal_speed=8.0
        for rid,buses in by_route.items():
            buses=sorted(buses,key=self._route_progress,reverse=True)
            for i,b in enumerate(buses):
                leader=buses[i-1] if i>0 else None
                follower=buses[i+1] if i+1<len(buses) else None
                hw=None
                if leader is not None:
                    spatial=max(0.0,self._route_progress(leader)-self._route_progress(b))
                    hw=spatial/nominal_speed
                following_hw=None
                if follower is not None:
                    following_hw=max(0.0,self._route_progress(b)-self._route_progress(follower))/nominal_speed
                b.metadata['leader_id']=leader.id if leader else None
                b.metadata['follower_id']=follower.id if follower else None
                b.metadata['following_headway_s']=following_hw
                self.headways.update_pair(rid,b,leader,self.network.time_s,hw)

    def _observe_and_message(self):
        observations={}; raw={}
        for iid,c in self.controllers.items():
            cam=self.camera.observe(iid,self.decision_interval)
            for m in self.logic[iid].movements:
                entry=cam.setdefault(m.key, {'density':0.0,'inflow':0.0,'outflow':0.0,'queue':0.0,'mean_speed':0.0})
                entry['green_time']=c.elapsed_s if c.is_green(m.lane_id,m.to_branch) else 0.0
            buses=self.gps.observe(iid)
            msgs=self.messages.receive(iid)
            observations[iid]=self.encoders[iid].encode(cam,buses,msgs,c)
            raw[iid]=(cam,buses,msgs)

        # Publica después de observar para que el siguiente ciclo reciba mensajes.
        for iid,c in self.controllers.items():
            cam,buses,_=raw[iid]
            congestion=min(1.0,sum(x.get('density',0)*self.cfg['simulation'].get('camera_roi_m',60)/12 for x in cam.values()))
            congested=[k for k,v in cam.items() if v.get('queue',0)>=3]
            critical=[f"{b['id']}:{b['status']}" for b in buses if 'bunching' in b['status']]
            self.messages.broadcast(NeighborMessage(iid,self.network.time_s,congestion,congested,c.phase_index,buses[:6],critical))
        self.last_raw=raw
        return observations

    def step(self, actions: dict[str,int]):
        before_changes={iid:c.phase_changes for iid,c in self.controllers.items()}
        for iid,action in actions.items():
            self.controllers[iid].request_phase(int(action))

        target=self.network.time_s+self.decision_interval
        while self.network.time_s < target and self.network.time_s < self.episode_seconds:
            for c in self.controllers.values(): c.tick(self.network.dt)
            self.network.step(self.signal_green)
            self._update_headways()

        completed_delta=len(self.network.completed)-self._last_completed
        self._last_completed=len(self.network.completed)
        obs=self._observe_and_message()
        rewards={}; components={}
        for iid,c in self.controllers.items():
            cam,buses,_=self.last_raw[iid]
            changed=c.phase_changes>before_changes[iid]
            r,comp=self.rewards[iid].calculate(cam,buses,completed_delta/max(1,len(self.controllers)),changed)
            rewards[iid]=r; components[iid]=comp
        self.last_reward_components=components; self.last_observations=obs
        done=self.network.time_s>=self.episode_seconds
        info={'time_s':self.network.time_s,'completed':len(self.network.completed),'reward_components':components,
              'bunching_events':list(self.headways.events)}
        return obs,rewards,done,info

    def heuristic_actions(self) -> dict[str,int]:
        """Baseline seguro: prioriza la fase del bus atrasado/riesgoso más cercano; si no, la cola mayor."""
        actions={}
        for iid,c in self.controllers.items():
            mask=c.action_mask(); valid=[i for i,v in enumerate(mask) if v]
            if len(valid)==1: actions[iid]=valid[0]; continue
            buses=self.gps.observe(iid); cam=self.camera.observe(iid,self.decision_interval)
            score={i:0.0 for i in valid}
            for i in valid:
                keys={m.key for m in self.logic[iid].phases[i].movements}
                score[i]+=sum(cam.get(k,{}).get('queue',0) for k in keys)
                for b in buses:
                    if b['status'] in ('atrasado','riesgo_bunching','critico_bunching'):
                        # Estima movimiento del bus si ya está en aproximación inmediata.
                        bus=next((x for x in self.network.active_buses() if x.id==b['id']),None)
                        if bus:
                            mov=self.network._next_movement(bus)
                            if mov and mov[0]==iid and f'{mov[1]}->{mov[2]}' in keys:
                                score[i]+=20.0 if b['status']=='atrasado' else 12.0
                    elif b['status']=='adelantado':
                        bus=next((x for x in self.network.active_buses() if x.id==b['id']),None)
                        if bus:
                            mov=self.network._next_movement(bus)
                            if mov and mov[0]==iid and f'{mov[1]}->{mov[2]}' in keys:
                                score[i]-=8.0
            actions[iid]=max(valid,key=lambda i:score[i])
        return actions
