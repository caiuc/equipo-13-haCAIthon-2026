from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import statistics

from common.domain_models import Bus, VehicleKind


class MetricsCollector:
    def __init__(self, cfg: dict):
        self.cfg=cfg
        self.phase_samples=defaultdict(list)
        self.reward_samples=defaultdict(list)

    def sample(self, env, rewards: dict[str,float] | None = None):
        for iid,c in env.controllers.items():
            self.phase_samples[iid].append({'time_s':env.network.time_s,'phase':c.phase_index,'mode':c.mode.value})
        if rewards:
            for iid,r in rewards.items(): self.reward_samples[iid].append(float(r))

    @staticmethod
    def _event_durations(events: list[dict]) -> list[float]:
        starts={}; durations=[]
        for e in events:
            key=(e.get('route'),e.get('bus'))
            if e['type']=='bunching_start': starts[key]=float(e['time_s'])
            elif e['type']=='bunching_end' and key in starts:
                durations.append(float(e['time_s'])-starts.pop(key))
        return durations

    def _phase_stats(self, env) -> dict:
        result={}
        interval=float(self.cfg['rl'].get('decision_interval_s',5.0))
        for iid,c in env.controllers.items():
            samples=self.phase_samples.get(iid,[])
            counts=defaultdict(int)
            runs=[]
            last_phase=None; run_len=0
            for row in samples:
                counts[row['phase']]+=1
                if row['phase']!=last_phase:
                    if run_len: runs.append(run_len*interval)
                    last_phase=row['phase']; run_len=1
                else:
                    run_len+=1
            if run_len: runs.append(run_len*interval)
            total=max(1,len(samples))
            result[iid]={
                'phase_changes':c.phase_changes,
                'mean_phase_duration_s':statistics.fmean(runs) if runs else 0.0,
                'phase_utilization_pct':{str(k):100*v/total for k,v in sorted(counts.items())},
                'restriction_activations':dict(c.restriction_counts),
            }
        return result

    def _intersection_snapshot(self, env) -> dict:
        result={}
        for iid,c in env.controllers.items():
            raw=env.last_raw.get(iid,({},[],[]))
            cam,buses,msgs=raw
            result[iid]={
                'current_phase':c.phase_index,
                'mode':c.mode.value,
                'active_movements':[m.key for m in env.logic[iid].phases[c.phase_index].movements],
                'movement_perception':cam,
                'upcoming_buses':buses,
                'received_neighbor_messages':[
                    {
                        'sender_id':m.sender_id,'timestamp_s':m.timestamp_s,'congestion':m.congestion,
                        'congested_movements':m.congested_movements,'current_phase':m.current_phase,
                        'upcoming_buses':m.upcoming_buses,'critical_events':m.critical_events
                    } for m in msgs[-6:]
                ],
                'last_reward_components':env.last_reward_components.get(iid,{})
            }
        return result

    def summarize(self, env) -> dict:
        all_v=list(env.network.completed)+list(env.network.vehicles.values())
        completed=list(env.network.completed)
        buses=[v for v in all_v if isinstance(v,Bus)]
        completed_buses=[v for v in completed if isinstance(v,Bus)]
        completed_cars=[v for v in completed if v.kind==VehicleKind.CAR]
        travel=[v.finished_at_s-v.created_at_s for v in completed if v.finished_at_s is not None]
        bus_travel=[v.finished_at_s-v.created_at_s for v in completed_buses if v.finished_at_s is not None]
        waits=[v.waiting_time_s for v in completed]
        headways=[b.headway_s for b in buses if b.headway_s is not None]
        crit=float(self.cfg['transit']['critical_headway_s'])
        starts=[e for e in env.headways.events if e['type']=='bunching_start']
        ends=[e for e in env.headways.events if e['type']=='bunching_end']
        durations=self._event_durations(env.headways.events)
        avg_reward={iid:(statistics.fmean(xs) if xs else 0.0) for iid,xs in self.reward_samples.items()}
        active=list(env.network.vehicles.values())
        mean_speed=statistics.fmean([v.speed_mps for v in active]) if active else 0.0
        queue=sum(1 for v in active if v.speed_mps<0.5)
        total_link_length=sum(float(x['length_m']) for x in self.cfg['links'].values())
        sim_time=max(env.network.time_s,1e-6)
        bus_speeds=[b.speed_mps for b in buses]
        dwell=[s.get('dwell_s',0.0) for b in buses for s in b.metadata.get('visited_stops',[])]
        return {
            'simulation': {'time_s':env.network.time_s,'spawned':env.network.spawned,'completed':len(completed)},
            'public_transport': {
                'completed_buses':len(completed_buses),
                'mean_travel_time_s': statistics.fmean(bus_travel) if bus_travel else 0.0,
                'mean_waiting_time_s': statistics.fmean([b.waiting_time_s for b in buses]) if buses else 0.0,
                'mean_speed_mps': statistics.fmean(bus_speeds) if bus_speeds else 0.0,
                'mean_headway_s': statistics.fmean(headways) if headways else 0.0,
                'headway_std_s': statistics.pstdev(headways) if len(headways)>1 else 0.0,
                'headway_regularity_cv': ((statistics.pstdev(headways)/statistics.fmean(headways)) if len(headways)>1 and statistics.fmean(headways)>0 else 0.0),
                'headways_below_critical_pct': (100*sum(h<crit for h in headways)/len(headways)) if headways else 0.0,
                'bunching_events':len(starts),
                'bunching_recoveries':len(ends),
                'mean_bunching_duration_s':statistics.fmean(durations) if durations else 0.0,
                'mean_recovery_time_s':statistics.fmean(durations) if durations else 0.0,
                'mean_stop_dwell_s':statistics.fmean(dwell) if dwell else 0.0,
                'event_log':env.headways.events,
            },
            'general_traffic': {
                'completed_cars':len(completed_cars),
                'mean_travel_time_s':statistics.fmean(travel) if travel else 0.0,
                'mean_waiting_time_s':statistics.fmean(waits) if waits else 0.0,
                'active_mean_speed_mps':mean_speed,
                'active_queue_length':queue,
                'network_density_veh_per_km':len(active)/(total_link_length/1000.0) if total_link_length else 0.0,
                'network_flow_veh_per_hour':len(completed)*3600.0/sim_time,
            },
            'signal_control': {'intersections':self._phase_stats(env),'mean_reward':avg_reward},
            'intersection_telemetry': self._intersection_snapshot(env),
        }

    def write_json(self, env, path: str | Path):
        path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(self.summarize(env),indent=2,ensure_ascii=False),encoding='utf-8')
