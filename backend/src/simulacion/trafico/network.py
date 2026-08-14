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
    """Red microscópica con respeto estricto de carril, línea de detención y caja.

    Convención espacial: ``position_m`` representa el parachoques delantero del
    vehículo sobre el link. Esto permite que la línea de detención sea una barrera
    exacta: con rojo/amarillo el frente nunca puede sobrepasarla.
    """

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
        self._car_next_spawn: dict[str, float] = {}
        self._last_release: dict[tuple[str, str, str], float] = {}
        self._od = cfg.get('car_od', [])
        self._od_by_origin = defaultdict(list)
        for od in self._od:
            self._od_by_origin[od['origin']].append(od)
        self._stop_lookup = defaultdict(list)
        for sid, stop in cfg.get('stops', {}).items():
            self._stop_lookup[stop['link']].append((float(stop['position_m']), sid, stop))
        for stops in self._stop_lookup.values():
            stops.sort()

    @property
    def minimum_gap_m(self) -> float:
        return float(self.cfg.get('simulation', {}).get('minimum_vehicle_gap_m', 2.5))

    @property
    def stop_line_clearance_m(self) -> float:
        return float(self.cfg.get('simulation', {}).get('stop_line_clearance_m', 4.0))

    @property
    def intersection_exit_clearance_m(self) -> float:
        return float(self.cfg.get('simulation', {}).get('intersection_exit_clearance_m', 1.0))

    def _intersection_half_extent_m(self, intersection_id: str) -> float:
        # La demo usa una escala 1 unidad SVG ~= 1 m longitudinal. Mantener este
        # valor en configuración hace que la física y el cuadrado dibujado coincidan.
        display = self.cfg.get('display', {})
        return max(4.0, float(display.get('intersection_size', 74.0)) / 2.0)

    def _validate_bus_routes(self):
        for rid, route in self.cfg.get('bus_routes', {}).items():
            links = list(route.get('links', []))
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
        self.vehicles.clear()
        self.completed.clear()
        self.spawned = 0
        self._bus_schedule = self._build_bus_schedule()
        self._last_release.clear()
        self._car_next_spawn.clear()
        spawn_immediately = bool(self.cfg.get('simulation', {}).get('spawn_immediately', False))
        for origin in self._od_by_origin:
            if spawn_immediately:
                self._car_next_spawn[origin] = 0.0
            else:
                self._schedule_next_car(origin)

    def _movement_for_index(self, v: Vehicle, link_index: int) -> tuple[str, str, str] | None:
        if link_index < 0 or link_index >= len(v.route_links) - 1:
            return None
        cur_id = v.route_links[link_index]
        nxt_id = v.route_links[link_index + 1]
        cur = self.cfg['links'][cur_id]
        nxt = self.cfg['links'][nxt_id]
        intersection = cur['to']
        if self.cfg['nodes'].get(intersection, {}).get('kind') != 'intersection':
            return None
        from_branch = cur.get('to_branch')
        to_branch = nxt.get('from_branch')
        if not from_branch or not to_branch:
            return None
        lane_id = self._lane_for(intersection, from_branch, to_branch)
        return intersection, lane_id, to_branch

    def _next_movement(self, v: Vehicle) -> tuple[str, str, str] | None:
        return self._movement_for_index(v, v.link_index)

    def _lane_for(self, iid: str, from_branch: str, to_branch: str) -> str:
        inter = self.cfg['intersections'][iid]
        from ia.clingo.geometry import target_branch
        for lane_id, lane in inter['incoming_lanes'].items():
            if lane['branch'] != from_branch:
                continue
            for turn in lane.get('allowed_turns', []):
                if target_branch(inter['branches'], from_branch, turn) == to_branch:
                    return lane_id
        raise RuntimeError(f'No existe carril para {iid}: {from_branch}->{to_branch}')

    def _movement_turn(self, iid: str, lane_id: str, to_branch: str) -> str:
        if iid in self.logic:
            for movement in self.logic[iid].movements:
                if movement.lane_id == lane_id and movement.to_branch == to_branch:
                    return movement.turn
        inter = self.cfg['intersections'][iid]
        from ia.clingo.geometry import target_branch
        frm = inter['incoming_lanes'][lane_id]['branch']
        for turn in inter['incoming_lanes'][lane_id].get('allowed_turns', []):
            if target_branch(inter['branches'], frm, turn) == to_branch:
                return turn
        return 'straight'

    @staticmethod
    def _lane_slot_from_lane_id(lane_id: str) -> int:
        # 0 = carril interior/izquierdo; 1 = carril exterior recto/derecha.
        return 0 if 'left' in lane_id.lower() else 1

    def lane_slot(self, v: Vehicle, link_index: int | None = None) -> int:
        idx = v.link_index if link_index is None else int(link_index)
        movement = self._movement_for_index(v, idx)
        if movement is not None:
            return self._lane_slot_from_lane_id(movement[1])
        # Si el link sale de una intersección y no llega a otra, conserva de forma
        # determinista el carril asociado al movimiento que lo originó.
        previous = self._movement_for_index(v, idx - 1)
        if previous is not None:
            return self._lane_slot_from_lane_id(previous[1])
        return int(v.metadata.get('lane_slot', 1))

    def lane_id(self, v: Vehicle) -> str | None:
        movement = self._next_movement(v)
        if movement is not None:
            return movement[1]
        previous = self._movement_for_index(v, v.link_index - 1)
        return previous[1] if previous is not None else None

    def _lane_key(self, v: Vehicle, link_index: int | None = None) -> tuple[str, int]:
        idx = v.link_index if link_index is None else int(link_index)
        return v.route_links[idx], self.lane_slot(v, idx)

    def _spawn_space_available(self, candidate: Vehicle) -> bool:
        link_id, slot = self._lane_key(candidate, 0)
        for other in self.vehicles.values():
            if other.finished or self._lane_key(other) != (link_id, slot):
                continue
            # candidate.position_m = 0 representa su frente. El vehículo puede
            # aparecer solo si la parte trasera del líder deja el gap mínimo.
            gap = other.position_m - other.length_m - candidate.position_m
            if gap < self.minimum_gap_m:
                return False
        return True

    def _new_car(self, origin: str) -> bool:
        choices = self._od_by_origin.get(origin, [])
        if not choices:
            return False
        od = self.rng.choices(choices, weights=[float(x.get('weight', 1)) for x in choices], k=1)[0]
        route = self.route_planner.route(od['origin'], od['destination'])
        if not route:
            return False
        next_id = self.spawned + 1
        v = Vehicle(
            id=f'car-{next_id}', kind=VehicleKind.CAR, route_id=None, route_links=route,
            position_m=0.0, speed_mps=self.rng.uniform(5.0, 10.0),
            desired_speed_mps=self.rng.uniform(11.0, 15.0),
            max_accel=self.rng.uniform(1.5, 2.5), comfortable_decel=self.rng.uniform(2.5, 4.0),
            reaction_time_s=self.rng.uniform(0.8, 1.3), created_at_s=self.time_s,
        )
        v.metadata['lane_slot'] = self.lane_slot(v, 0)
        if not self._spawn_space_available(v):
            return False
        self.spawned = next_id
        self.vehicles[v.id] = v
        return True

    def _spawn_buses(self):
        due = []
        while self._bus_schedule and self._bus_schedule[0][0] <= self.time_s:
            due.append(self._bus_schedule.pop(0))
        for _, rid, idx in due:
            route = self.cfg['bus_routes'][rid]
            next_id = self.spawned + 1
            b = Bus(
                id=f'bus-{rid}-{idx + 1}', kind=VehicleKind.BUS, route_id=rid,
                route_links=list(route['links']), position_m=0.0, speed_mps=7.0,
                desired_speed_mps=12.0, length_m=12.0, max_accel=1.2,
                comfortable_decel=2.2, reaction_time_s=1.0, created_at_s=self.time_s,
                metadata={'stop_ids': list(route.get('stops', [])), 'visited_stops': []},
            )
            b.metadata['lane_slot'] = self.lane_slot(b, 0)
            if self._spawn_space_available(b):
                self.spawned = next_id
                self.vehicles[b.id] = b
            else:
                # El bus espera en el origen; nunca se materializa encima de otro.
                self._bus_schedule.append((self.time_s + self.dt, rid, idx))
        self._bus_schedule.sort()

    def _stop_line_position(self, v: Vehicle, movement: tuple[str, str, str] | None = None) -> float | None:
        movement = movement or self._next_movement(v)
        if movement is None:
            return None
        iid = movement[0]
        link_length = float(self.cfg['links'][v.current_link]['length_m'])
        offset = self._intersection_half_extent_m(iid) + self.stop_line_clearance_m
        return max(0.0, link_length - offset)

    def _movement_key(self, movement: tuple[str, str, str]) -> str:
        return f'{movement[1]}->{movement[2]}'

    def _active_intersection_entry(self, v: Vehicle) -> dict | None:
        value = v.metadata.get('intersection_entry')
        return value if isinstance(value, dict) else None

    def _movement_conflicts_with_occupancy(self, movement: tuple[str, str, str], vehicle_id: str) -> bool:
        iid, lane, to_branch = movement
        key = f'{lane}->{to_branch}'
        conflicts = self.logic.get(iid).conflicts if iid in self.logic else set()
        for other in self.vehicles.values():
            if other.id == vehicle_id or other.finished:
                continue
            entry = self._active_intersection_entry(other)
            if not entry or entry.get('intersection_id') != iid:
                continue
            occupied_key = str(entry.get('movement_key'))
            # Un solo vehículo por trayectoria dentro de la caja es deliberadamente
            # conservador y garantiza que la discretización 2D nunca solape cuerpos.
            if occupied_key == key or frozenset((key, occupied_key)) in conflicts:
                return True
            # Sin lógica Clingo disponible, usamos el principio fail-safe: no se
            # abre una segunda trayectoria mientras la caja esté ocupada.
            if iid not in self.logic:
                return True
        return False

    def _downstream_has_receiving_space(self, v: Vehicle, movement: tuple[str, str, str]) -> bool:
        if v.link_index >= len(v.route_links) - 1:
            return True
        iid = movement[0]
        next_index = v.link_index + 1
        next_link = v.route_links[next_index]
        next_slot = self.lane_slot(v, next_index)
        candidates = [
            other for other in self.vehicles.values()
            if not other.finished
            and other.id != v.id
            and self._lane_key(other) == (next_link, next_slot)
        ]
        if not candidates:
            return True
        nearest = min(candidates, key=lambda item: item.position_m)
        nearest_rear = nearest.position_m - nearest.length_m
        # Para entrar, el vehículo debe poder salir completamente del cuadrado sin
        # quedar atravesado bloqueando el cruce (regla "no bloquear la intersección").
        required_rear_space = (
            self._intersection_half_extent_m(iid)
            + v.length_m
            + self.minimum_gap_m
            + self.intersection_exit_clearance_m
        )
        return nearest_rear >= required_rear_space

    def _entry_constraints_allow(
        self,
        v: Vehicle,
        movement: tuple[str, str, str],
        signal_green: Callable[[str, str, str], bool],
    ) -> bool:
        entry = self._active_intersection_entry(v)
        if entry and entry.get('intersection_id') == movement[0]:
            # Un vehículo que alcanzó legalmente la caja debe despejarla aunque la
            # luz cambie mientras se encuentra dentro.
            return True
        iid, lane, to_branch = movement
        if not signal_green(iid, lane, to_branch):
            return False
        turn = self._movement_turn(iid, lane, to_branch)
        cap = float(self.cfg['simulation']['turn_capacity_vph'].get(turn, 1800))
        min_release_s = 3600.0 / max(cap, 1.0)
        last = self._last_release.get(movement, -1e18)
        if self.time_s - last < min_release_s:
            return False
        if self._movement_conflicts_with_occupancy(movement, v.id):
            return False
        if not self._downstream_has_receiving_space(v, movement):
            return False
        return True

    def _authorize_intersection_entry(
        self,
        v: Vehicle,
        movement: tuple[str, str, str],
        signal_green: Callable[[str, str, str], bool],
    ) -> bool:
        if not self._entry_constraints_allow(v, movement, signal_green):
            return False
        if self._active_intersection_entry(v):
            return True
        iid, lane, to_branch = movement
        self._last_release[movement] = self.time_s
        v.metadata['intersection_entry'] = {
            'intersection_id': iid,
            'movement_key': f'{lane}->{to_branch}',
            'lane_id': lane,
            'to_branch': to_branch,
            'entry_link_index': v.link_index,
            'entered_at_s': self.time_s,
        }
        return True

    def _clear_intersection_if_needed(self, v: Vehicle) -> None:
        entry = self._active_intersection_entry(v)
        if not entry:
            return
        entry_index = int(entry.get('entry_link_index', v.link_index))
        if v.link_index <= entry_index:
            return
        iid = str(entry['intersection_id'])
        current_link = self.cfg['links'][v.current_link]
        if current_link.get('from') != iid:
            v.metadata.pop('intersection_entry', None)
            return
        # Se libera la ocupación solo cuando el parachoques trasero salió del
        # cuadrado y dejó además una pequeña holgura.
        rear_position = v.position_m - v.length_m
        threshold = self._intersection_half_extent_m(iid) + self.intersection_exit_clearance_m
        if rear_position >= threshold:
            v.metadata.pop('intersection_entry', None)

    def _leader_gap(
        self,
        v: Vehicle,
        same_lane: list[Vehicle],
        link_length: float,
        signal_green: Callable[[str, str, str], bool],
    ):
        ahead = [x for x in same_lane if x.id != v.id and x.position_m > v.position_m and not x.finished]
        if ahead:
            leader = min(ahead, key=lambda x: x.position_m)
            gap = leader.position_m - leader.length_m - v.position_m
            return max(0.0, gap), leader.speed_mps

        movement = self._next_movement(v)
        if movement is not None and not self._active_intersection_entry(v):
            if not self._entry_constraints_allow(v, movement, signal_green):
                stop_line = self._stop_line_position(v, movement)
                if stop_line is not None:
                    return max(0.0, stop_line - v.position_m), 0.0
        return None, 0.0

    def _handle_stop(self, b: Bus) -> bool:
        return self.stop_manager.handle(b, self.time_s)

    def _enforce_minimum_separation(self) -> None:
        """Cinturón de seguridad numérico posterior al modelo de Gipps.

        Gipps ya frena por líder, pero la integración discreta y los cambios de link
        pueden acumular redondeos. Este pase garantiza de forma absoluta que dos
        cuerpos nunca terminen solapados en el mismo carril.
        """
        groups = defaultdict(list)
        for vehicle in self.vehicles.values():
            if not vehicle.finished:
                groups[self._lane_key(vehicle)].append(vehicle)
        for vehicles in groups.values():
            vehicles.sort(key=lambda item: item.position_m, reverse=True)
            for leader, follower in zip(vehicles, vehicles[1:]):
                max_front = leader.position_m - leader.length_m - self.minimum_gap_m
                if follower.position_m > max_front:
                    follower.position_m = max(0.0, max_front)
                    follower.speed_mps = min(follower.speed_mps, leader.speed_mps)

    def step(self, signal_green: Callable[[str, str, str], bool]) -> list[Vehicle]:
        # Buses tienen prioridad de despacho en el origen; los autos esperan si el
        # carril aún no tiene espacio físico. Así tampoco nacen superpuestos.
        self._spawn_buses()
        for origin in list(self._od_by_origin):
            if origin not in self._car_next_spawn:
                self._schedule_next_car(origin)
            while self.time_s >= self._car_next_spawn[origin]:
                if self._new_car(origin):
                    self._schedule_next_car(origin)
                else:
                    self._car_next_spawn[origin] = self.time_s + self.dt
                    break

        for vehicle in self.vehicles.values():
            self._clear_intersection_if_needed(vehicle)

        by_lane = defaultdict(list)
        for vehicle in self.vehicles.values():
            if not vehicle.finished:
                by_lane[self._lane_key(vehicle)].append(vehicle)

        completed_now = []
        # Procesar primero los vehículos delanteros reduce aún más la posibilidad de
        # artefactos de integración en una cola.
        processing_order = sorted(
            [v for v in self.vehicles.values() if not v.finished],
            key=lambda item: (item.current_link, self.lane_slot(item), -item.position_m),
        )

        for v in processing_order:
            if v.finished:
                continue
            if isinstance(v, Bus) and self._handle_stop(v):
                continue

            link = self.cfg['links'][v.current_link]
            link_length = float(link['length_m'])
            lane_key = self._lane_key(v)
            gap, leader_speed = self._leader_gap(v, by_lane[lane_key], link_length, signal_green)
            desired = min(v.desired_speed_mps, float(link.get('speed_limit_mps', v.desired_speed_mps)))
            next_speed = gipps_next_speed(
                v.speed_mps,
                desired,
                v.max_accel,
                v.comfortable_decel,
                v.reaction_time_s,
                gap,
                leader_speed,
            )
            if next_speed < 0.2:
                v.waiting_time_s += self.dt

            distance = 0.5 * (v.speed_mps + next_speed) * self.dt
            proposed_position = v.position_m + distance
            movement = self._next_movement(v)
            stop_line = self._stop_line_position(v, movement) if movement is not None else None

            if (
                movement is not None
                and stop_line is not None
                and not self._active_intersection_entry(v)
                and proposed_position >= stop_line
            ):
                if not self._authorize_intersection_entry(v, movement, signal_green):
                    v.position_m = min(stop_line, max(v.position_m, 0.0))
                    v.speed_mps = 0.0
                    continue

            v.speed_mps = next_speed
            v.position_m = proposed_position

            while v.position_m >= link_length:
                movement = self._next_movement(v)
                # Toda intersección debe haberse autorizado en la línea de detención.
                if movement is not None and not self._active_intersection_entry(v):
                    if not self._authorize_intersection_entry(v, movement, signal_green):
                        fallback_line = self._stop_line_position(v, movement)
                        v.position_m = fallback_line if fallback_line is not None else link_length - 0.5
                        v.speed_mps = 0.0
                        break

                overflow = v.position_m - link_length
                if v.link_index >= len(v.route_links) - 1:
                    v.finished_at_s = self.time_s
                    completed_now.append(v)
                    self.completed.append(v)
                    break
                v.link_index += 1
                v.position_m = overflow
                v.metadata['lane_slot'] = self.lane_slot(v)
                link = self.cfg['links'][v.current_link]
                link_length = float(link['length_m'])
                self._clear_intersection_if_needed(v)

        for v in completed_now:
            self.vehicles.pop(v.id, None)

        self._enforce_minimum_separation()
        for vehicle in self.vehicles.values():
            self._clear_intersection_if_needed(vehicle)
        self.time_s += self.dt
        return completed_now

    def active_buses(self) -> list[Bus]:
        return [v for v in self.vehicles.values() if isinstance(v, Bus)]

    def active_cars(self) -> list[Vehicle]:
        return [v for v in self.vehicles.values() if v.kind == VehicleKind.CAR]
