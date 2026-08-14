from __future__ import annotations

from collections import defaultdict
import math
import random
from typing import Callable

from common.domain_models import Bus, Vehicle, VehicleKind
from simulacion.vehiculos.gipps import gipps_next_speed
from simulacion.rutas.route_planner import RoutePlanner
from simulacion.paraderos.stop_manager import StopManager


class TrafficNetwork:
    def __init__(self, cfg: dict, logic: dict | None = None):
        self.cfg = cfg
        self.dt = float(cfg['simulation']['dt_s'])
        self.rng = random.Random(int(cfg['simulation'].get('seed', 42)))
        self.logic = logic or {}
        self.route_planner = RoutePlanner(cfg, self.rng, self.logic)
        self.stop_manager = StopManager(cfg, self.rng, self.dt)
        self.time_s = 0.0
        self.vehicles: dict[str, Vehicle] = {}
        self.completed: list[Vehicle] = []
        self.spawned = 0
        self._validate_bus_routes()
        self._bus_schedule = self._build_bus_schedule()
        self._car_next_spawn: dict[str,float] = {}
        self._last_release: dict[tuple[str,str,str], float] = {}
        self._od = cfg.get('car_od', [])
        self._od_by_origin = defaultdict(list)
        for od in self._od:
            self._od_by_origin[od['origin']].append(od)
        self._stop_lookup = defaultdict(list)
        for sid, stop in cfg.get('stops', {}).items():
            self._stop_lookup[stop['link']].append((float(stop['position_m']), sid, stop))
        for stops in self._stop_lookup.values():
            stops.sort()


    def _validate_bus_routes(self):
        for rid,route in self.cfg.get('bus_routes',{}).items():
            links=list(route.get('links',[]))
            if not links or not self.route_planner.is_legal_link_route(links):
                raise ValueError(f'Recorrido de bus {rid!r} contiene un movimiento físicamente imposible')

    def _build_bus_schedule(self):
        schedule = []
        transit = self.cfg['transit']
        jitter = float(transit.get('bus_spawn_jitter_s', 0))
        for rid, route in self.cfg.get('bus_routes', {}).items():
            first = float(route.get('first_departure_s', 0))
            headway = float(route.get('headway_s', transit['target_headway_s']))
            for i in range(int(route.get('buses', 1))):
                j = self.rng.uniform(-jitter, jitter) if i > 0 else 0.0
                schedule.append((max(0.0, first + i * headway + j), rid, i))
        return sorted(schedule)

    def _traffic_rate(self) -> float:
        sim = self.cfg['simulation']
        level = sim.get('traffic_level', 'medium')
        return float(sim['poisson_rates_per_hour'][level]) / 3600.0

    def _schedule_next_car(self, origin: str):
        rate = self._traffic_rate()
        self._car_next_spawn[origin] = self.time_s + (self.rng.expovariate(rate) if rate > 0 else math.inf)

    def reset(self):
        self.time_s = 0.0
        self.vehicles.clear(); self.completed.clear(); self.spawned = 0
        self._bus_schedule = self._build_bus_schedule()
        self._last_release.clear()
        self._car_next_spawn.clear()
        for origin in self._od_by_origin:
            self._schedule_next_car(origin)

    def _new_car(self, origin: str):
        choices = self._od_by_origin.get(origin, [])
        if not choices:
            return
        od = self.rng.choices(choices, weights=[float(x.get('weight',1)) for x in choices], k=1)[0]
        route = self.route_planner.route(od['origin'], od['destination'])
        if not route:
            return
        self.spawned += 1
        v = Vehicle(
            id=f'car-{self.spawned}', kind=VehicleKind.CAR, route_id=None, route_links=route,
            position_m=0.0, speed_mps=self.rng.uniform(5.0, 10.0),
            desired_speed_mps=self.rng.uniform(11.0, 15.0),
            max_accel=self.rng.uniform(1.5,2.5), comfortable_decel=self.rng.uniform(2.5,4.0),
            reaction_time_s=self.rng.uniform(0.8,1.3), created_at_s=self.time_s,
        )
        self.vehicles[v.id] = v

    def _spawn_buses(self):
        while self._bus_schedule and self._bus_schedule[0][0] <= self.time_s:
            _, rid, idx = self._bus_schedule.pop(0)
            route = self.cfg['bus_routes'][rid]
            self.spawned += 1
            b = Bus(
                id=f'bus-{rid}-{idx+1}', kind=VehicleKind.BUS, route_id=rid,
                route_links=list(route['links']), position_m=0.0, speed_mps=7.0,
                desired_speed_mps=12.0, length_m=12.0, max_accel=1.2,
                comfortable_decel=2.2, reaction_time_s=1.0, created_at_s=self.time_s,
                metadata={'stop_ids': list(route.get('stops',[])), 'visited_stops': []},
            )
            self.vehicles[b.id] = b

    def _next_movement(self, v: Vehicle) -> tuple[str,str,str] | None:
        if v.link_index >= len(v.route_links)-1:
            return None
        cur_id = v.route_links[v.link_index]
        nxt_id = v.route_links[v.link_index+1]
        cur = self.cfg['links'][cur_id]; nxt = self.cfg['links'][nxt_id]
        intersection = cur['to']
        if self.cfg['nodes'].get(intersection,{}).get('kind') != 'intersection':
            return None
        from_branch = cur.get('to_branch')
        to_branch = nxt.get('from_branch')
        if not from_branch or not to_branch:
            return None
        lane_id = self._lane_for(intersection, from_branch, to_branch)
        return intersection, lane_id, to_branch

    def _lane_for(self, iid: str, from_branch: str, to_branch: str) -> str:
        inter = self.cfg['intersections'][iid]
        # Selección geométrica consistente con topology.geometry.
        from ia.clingo.geometry import target_branch
        for lane_id, lane in inter['incoming_lanes'].items():
            if lane['branch'] != from_branch:
                continue
            for turn in lane.get('allowed_turns',[]):
                if target_branch(inter['branches'], from_branch, turn) == to_branch:
                    return lane_id
        raise RuntimeError(f'No existe carril para {iid}: {from_branch}->{to_branch}')

    def _movement_turn(self, iid: str, lane_id: str, to_branch: str) -> str:
        if iid in self.logic:
            for m in self.logic[iid].movements:
                if m.lane_id == lane_id and m.to_branch == to_branch:
                    return m.turn
        inter=self.cfg['intersections'][iid]
        from ia.clingo.geometry import target_branch
        frm=inter['incoming_lanes'][lane_id]['branch']
        for turn in inter['incoming_lanes'][lane_id].get('allowed_turns',[]):
            if target_branch(inter['branches'],frm,turn)==to_branch:
                return turn
        return 'straight'

    def _can_release(self, movement: tuple[str,str,str], signal_green: Callable[[str,str,str], bool]) -> bool:
        iid,lane,to=movement
        if not signal_green(iid,lane,to):
            return False
        turn=self._movement_turn(iid,lane,to)
        cap=float(self.cfg['simulation']['turn_capacity_vph'].get(turn,1800))
        min_gap=3600.0/max(cap,1.0)
        last=self._last_release.get(movement,-1e18)
        if self.time_s-last < min_gap:
            return False
        self._last_release[movement]=self.time_s
        return True

    def _leader_gap(self, v: Vehicle, same_link: list[Vehicle], link_length: float, signal_green: Callable[[str,str,str], bool]):
        ahead = [x for x in same_link if x.id != v.id and x.position_m > v.position_m and not x.finished]
        if ahead:
            leader = min(ahead, key=lambda x: x.position_m)
            gap = leader.position_m - v.position_m - leader.length_m
            return max(0.0,gap), leader.speed_mps
        movement = self._next_movement(v)
        if movement is not None:
            iid,lane,to = movement
            if not signal_green(iid,lane,to):
                gap = link_length - v.position_m - 1.5
                return max(0.0,gap), 0.0
        return None, 0.0

    def _handle_stop(self, b: Bus) -> bool:
        return self.stop_manager.handle(b, self.time_s)

    def step(self, signal_green: Callable[[str,str,str], bool]) -> list[Vehicle]:
        for origin in list(self._od_by_origin):
            if origin not in self._car_next_spawn:
                self._schedule_next_car(origin)
            while self.time_s >= self._car_next_spawn[origin]:
                self._new_car(origin); self._schedule_next_car(origin)
        self._spawn_buses()

        by_link = defaultdict(list)
        for v in self.vehicles.values():
            if not v.finished:
                by_link[v.current_link].append(v)

        completed_now = []
        for v in list(self.vehicles.values()):
            if v.finished:
                continue
            if isinstance(v, Bus) and self._handle_stop(v):
                continue
            link = self.cfg['links'][v.current_link]
            gap, leader_speed = self._leader_gap(v, by_link[v.current_link], float(link['length_m']), signal_green)
            desired = min(v.desired_speed_mps, float(link.get('speed_limit_mps', v.desired_speed_mps)))
            next_speed = gipps_next_speed(v.speed_mps, desired, v.max_accel, v.comfortable_decel,
                                          v.reaction_time_s, gap, leader_speed)
            if next_speed < 0.2:
                v.waiting_time_s += self.dt
            distance = 0.5 * (v.speed_mps + next_speed) * self.dt
            v.speed_mps = next_speed
            v.position_m += distance

            while v.position_m >= float(link['length_m']):
                movement = self._next_movement(v)
                if movement is not None and not self._can_release(movement, signal_green):
                    v.position_m = float(link['length_m']) - 0.5
                    v.speed_mps = 0.0
                    break
                overflow = v.position_m - float(link['length_m'])
                if v.link_index >= len(v.route_links)-1:
                    v.finished_at_s = self.time_s
                    completed_now.append(v); self.completed.append(v)
                    break
                v.link_index += 1
                v.position_m = overflow
                link = self.cfg['links'][v.current_link]

        for v in completed_now:
            self.vehicles.pop(v.id, None)
        self.time_s += self.dt
        return completed_now

    def active_buses(self) -> list[Bus]:
        return [v for v in self.vehicles.values() if isinstance(v, Bus)]

    def active_cars(self) -> list[Vehicle]:
        return [v for v in self.vehicles.values() if v.kind == VehicleKind.CAR]
