from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Callable

import numpy as np
import torch

from common.domain_models import (
    Bus,
    BusStatus,
    IntersectionLogic,
    IntersectionTransit,
    NeighborMessage,
    SignalColor,
    Vehicle,
    VehicleKind,
)
from simulacion.percepcion.camera import SmartCamera
from simulacion.rutas.route_planner import RoutePlanner
from simulacion.trafico.lane import RoadLane
from simulacion.trafico.signal_controller import SignalController
from simulacion.vehiculos.gipps import update_vehicle


class MultiAgentTrafficEnv:
    """Entorno microscópico multiagente basado en el patrón de Empresa.zip.

    ``step(actions)`` representa UN intervalo de decisión DQN y ejecuta internamente
    N subpasos físicos de ``dt_s``. El callback ``on_substep`` se invoca después de
    cada subpaso y es la única fuente de frames para la visualización en vivo.
    """

    BRANCH_ORDER = ("north", "east", "south", "west")

    def __init__(
        self,
        cfg: dict,
        logic: dict[str, IntersectionLogic],
        episode_seconds: float = 600.0,
        seed: int | None = None,
    ):
        self.cfg = cfg
        self.logic = logic
        self.base_seed = int(cfg["simulation"].get("seed", 42) if seed is None else seed)
        self.episode_seconds = float(episode_seconds)
        self.dt_s = float(cfg["simulation"].get("dt_s", 0.2))
        self.decision_interval_s = float(cfg["rl"].get("decision_interval_s", 5.0))
        self.substeps_per_decision = max(1, int(round(self.decision_interval_s / self.dt_s)))
        self.intersection_half_size_m = float(cfg["simulation"].get("intersection_half_size_m", 12.0))
        self.minimum_gap_m = float(cfg["simulation"].get("minimum_vehicle_gap_m", 2.5))
        self.camera_roi_m = float(cfg["simulation"].get("camera_roi_m", 60.0))
        self.route_planner: RoutePlanner | None = None
        self.rng = random.Random(self.base_seed)
        self.sim_time_s = 0.0
        self.lanes: dict[str, RoadLane] = {}
        self.controllers: dict[str, SignalController] = {}
        self.transits: list[IntersectionTransit] = []
        self._car_sequence = 0
        self._bus_dispatch_index: dict[str, int] = {}
        self._immediate_spawn_done = False
        self.last_rewards: dict[str, float] = {}
        self.last_reward_breakdown: dict[str, dict] = {}
        self.last_actions: dict[str, int] = {}
        self.neighbor_messages: dict[str, NeighborMessage] = {}
        self._interval_stats: dict[str, dict] = {}
        self.stats: dict = {}
        self.headway_samples: list[float] = []
        self.reset(seed=self.base_seed)

    # ------------------------------------------------------------------ lifecycle
    def reset(self, seed: int | None = None) -> dict[str, list[float]]:
        if seed is not None:
            self.base_seed = int(seed)
        self.rng = random.Random(self.base_seed)
        random.seed(self.base_seed)
        np.random.seed(self.base_seed)
        torch.manual_seed(self.base_seed)
        self.route_planner = RoutePlanner(self.cfg, self.rng, self.logic)
        self.sim_time_s = 0.0
        self.transits = []
        self._car_sequence = 0
        self._bus_dispatch_index = {route_id: 0 for route_id in self.cfg.get("bus_routes", {})}
        self._immediate_spawn_done = False
        self.last_rewards = {iid: 0.0 for iid in self.logic}
        self.last_reward_breakdown = {iid: {} for iid in self.logic}
        self.last_actions = {iid: 0 for iid in self.logic}
        self.neighbor_messages = {}
        self.headway_samples = []
        self.stats = {
            "completedCars": 0,
            "completedBuses": 0,
            "carTravelTimes": [],
            "busTravelTimes": [],
            "intersectionCrossings": defaultdict(int),
            "phaseChanges": defaultdict(int),
            "bunchingEvents": 0,
            "spawnedCars": 0,
            "spawnedBuses": 0,
        }
        self._interval_stats = self._new_interval_stats()
        self._build_lanes()
        self._build_controllers()
        if bool(self.cfg["simulation"].get("spawn_immediately", True)):
            self._spawn_initial_traffic()
        self._update_bus_headways()
        self._broadcast_neighbor_messages()
        return self.observations()

    def _build_lanes(self) -> None:
        self.lanes = {}
        for link_id, link in self.cfg["links"].items():
            length = float(link["length_m"])
            to_node = self.cfg["nodes"][link["to"]]
            stop_line = None
            camera = None
            if to_node.get("kind") == "intersection":
                stop_line = max(1.0, length - self.intersection_half_size_m)
                camera = SmartCamera(self.camera_roi_m, stop_line)
            self.lanes[link_id] = RoadLane(
                link_id=link_id,
                length_m=length,
                speed_limit_mps=float(link.get("speed_limit_mps", 13.9)),
                stop_line_m=stop_line,
                camera=camera,
            )

    def _build_controllers(self) -> None:
        sig = self.cfg["signals"]
        self.controllers = {
            iid: SignalController(
                logic,
                min_green_s=float(sig["min_green_s"]),
                yellow_s=float(sig["yellow_s"]),
                max_red_s=float(sig["max_red_s"]),
            )
            for iid, logic in self.logic.items()
        }

    def _new_interval_stats(self) -> dict[str, dict]:
        return {
            iid: {"outflow": 0, "phaseChanged": False}
            for iid in self.logic
        }

    # ------------------------------------------------------------------ DQN contract
    def action_size(self, intersection_id: str) -> int:
        return self.controllers[intersection_id].phase_count

    def observation_size(self, intersection_id: str) -> int:
        return len(self._observation_for(intersection_id))

    def legal_action_mask(self, intersection_id: str) -> list[bool]:
        return self.controllers[intersection_id].legal_action_mask()

    def observations(self) -> dict[str, list[float]]:
        return {iid: self._observation_for(iid) for iid in self.logic}

    def step(
        self,
        actions: dict[str, int],
        on_substep: Callable[["MultiAgentTrafficEnv"], bool | None] | None = None,
    ) -> tuple[dict[str, list[float]], dict[str, float], bool, dict]:
        """Avanza exactamente un intervalo DQN y llama al renderer cada ``dt_s``."""
        self._interval_stats = self._new_interval_stats()
        self.last_actions = {iid: int(actions.get(iid, self.controllers[iid].current_phase)) for iid in self.logic}
        interrupted = False

        for substep in range(self.substeps_per_decision):
            requested = self.last_actions if substep == 0 else {}
            self._physics_substep(requested)
            if on_substep is not None and on_substep(self) is False:
                interrupted = True
                break

        rewards, breakdown = self._compute_rewards()
        self.last_rewards = rewards
        self.last_reward_breakdown = breakdown
        self._broadcast_neighbor_messages()
        done = interrupted or self.sim_time_s + 1e-9 >= self.episode_seconds
        return self.observations(), rewards, done, {
            "rewardBreakdown": breakdown,
            "actionMasks": {iid: self.legal_action_mask(iid) for iid in self.logic},
            "interrupted": interrupted,
        }

    # ------------------------------------------------------------------ physical substep
    def _physics_substep(self, requested_actions: dict[str, int]) -> None:
        for iid, controller in self.controllers.items():
            controller.step(requested_actions.get(iid), self.dt_s)
            if controller.phase_changed_this_step:
                self._interval_stats[iid]["phaseChanged"] = True
                self.stats["phaseChanges"][iid] += 1

        self._spawn_traffic()
        self._advance_transits()
        for lane in self.lanes.values():
            self._advance_lane(lane)

        self.sim_time_s += self.dt_s
        self._update_bus_headways()
        self._tick_cameras()

    def _advance_lane(self, lane: RoadLane) -> None:
        lane.sort_front_to_back()
        transfers: list[Vehicle] = []
        completed: list[Vehicle] = []

        for index, vehicle in enumerate(list(lane.vehicles)):
            leader = lane.vehicles[index - 1] if index > 0 else None
            previous_position = vehicle.position_m

            if isinstance(vehicle, Bus) and vehicle.dwell_remaining_s > 0.0:
                vehicle.dwell_remaining_s = max(0.0, vehicle.dwell_remaining_s - self.dt_s)
                vehicle.speed_mps = 0.0
                vehicle.waiting_time_s += self.dt_s
                if vehicle.dwell_remaining_s <= 0.0:
                    vehicle.next_stop_index += 1
                continue

            bus_stop = self._next_bus_stop_position(vehicle, lane.link_id)
            if bus_stop is not None and vehicle.position_m >= bus_stop - 0.15:
                self._start_bus_dwell(vehicle, bus_stop)
                continue

            stop_target = None
            if bus_stop is not None and bus_stop >= vehicle.position_m:
                stop_target = bus_stop

            can_enter = False
            if lane.stop_line_m is not None:
                can_enter = self._can_enter_intersection(vehicle, lane)
                if not can_enter:
                    stop_target = lane.stop_line_m if stop_target is None else min(stop_target, lane.stop_line_m)

            update_vehicle(vehicle, self.dt_s, leader, stop_target)
            if lane.camera:
                lane.camera.record_motion(previous_position, vehicle.position_m, self.sim_time_s)

            if bus_stop is not None and vehicle.position_m >= bus_stop - 0.05:
                vehicle.position_m = bus_stop
                vehicle.speed_mps = 0.0
                self._start_bus_dwell(vehicle, bus_stop)
                continue

            if lane.stop_line_m is not None and can_enter and vehicle.position_m >= lane.stop_line_m - 0.02:
                vehicle.position_m = lane.stop_line_m
                vehicle.speed_mps = max(vehicle.speed_mps, 1.0)
                if self._enter_intersection(vehicle, lane):
                    transfers.append(vehicle)
                    continue

            if lane.stop_line_m is None and vehicle.position_m >= lane.length_m:
                completed.append(vehicle)

        if transfers or completed:
            remove_ids = {v.id for v in transfers + completed}
            lane.vehicles = [v for v in lane.vehicles if v.id not in remove_ids]
        for vehicle in completed:
            self._finish_vehicle(vehicle)

    def _advance_transits(self) -> None:
        finished: list[IntersectionTransit] = []
        for transit in self.transits:
            transit.elapsed_s += self.dt_s
            if transit.progress < 1.0:
                continue
            outgoing = self.lanes[transit.to_link]
            vehicle = transit.vehicle
            start_position = self.intersection_half_size_m
            required = vehicle.length_m + self.minimum_gap_m
            if not outgoing.has_entry_space(start_position, required):
                transit.elapsed_s = transit.duration_s
                continue
            vehicle.link_index += 1
            vehicle.position_m = start_position
            vehicle.speed_mps = max(1.0, min(vehicle.speed_mps, outgoing.speed_limit_mps))
            outgoing.vehicles.append(vehicle)
            finished.append(transit)
        if finished:
            ids = {id(item) for item in finished}
            self.transits = [item for item in self.transits if id(item) not in ids]

    # ------------------------------------------------------------------ intersection safety
    def _movement_for(self, vehicle: Vehicle, lane: RoadLane):
        if vehicle.link_index + 1 >= len(vehicle.route_links):
            return None
        current_cfg = self.cfg["links"][lane.link_id]
        iid = current_cfg["to"]
        if self.cfg["nodes"].get(iid, {}).get("kind") != "intersection":
            return None
        next_link_id = vehicle.route_links[vehicle.link_index + 1]
        next_cfg = self.cfg["links"][next_link_id]
        from_branch = current_cfg.get("to_branch")
        to_branch = next_cfg.get("from_branch")
        for movement in self.logic[iid].movements:
            if movement.from_branch == from_branch and movement.to_branch == to_branch:
                return movement
        return None

    def _can_enter_intersection(self, vehicle: Vehicle, lane: RoadLane) -> bool:
        movement = self._movement_for(vehicle, lane)
        if movement is None:
            return False
        controller = self.controllers[movement.intersection_id]
        if controller.movement_color(movement.key) != SignalColor.GREEN:
            return False

        for transit in self.transits:
            if transit.intersection_id != movement.intersection_id:
                continue
            pair = frozenset((transit.movement_key, movement.key))
            if transit.movement_key == movement.key or pair in self.logic[movement.intersection_id].conflicts:
                return False

        next_link_id = vehicle.route_links[vehicle.link_index + 1]
        outgoing = self.lanes[next_link_id]
        start_position = self.intersection_half_size_m
        return outgoing.has_entry_space(start_position, vehicle.length_m + self.minimum_gap_m)

    def _enter_intersection(self, vehicle: Vehicle, lane: RoadLane) -> bool:
        movement = self._movement_for(vehicle, lane)
        if movement is None or not self._can_enter_intersection(vehicle, lane):
            return False
        to_link = vehicle.route_links[vehicle.link_index + 1]
        self.transits.append(IntersectionTransit(
            vehicle=vehicle,
            intersection_id=movement.intersection_id,
            from_link=lane.link_id,
            to_link=to_link,
            movement_key=movement.key,
            duration_s=1.6,
        ))
        if lane.camera:
            lane.camera.record_exit(self.sim_time_s)
        self._interval_stats[movement.intersection_id]["outflow"] += 1
        self.stats["intersectionCrossings"][movement.intersection_id] += 1
        return True

    # ------------------------------------------------------------------ traffic generation
    def _spawn_initial_traffic(self) -> None:
        # Los buses se despachan primero para que la demo muestre transporte público
        # desde el primer frame; los autos ocupan el espacio restante sin solaparse.
        self._spawn_due_buses(force=True)
        origins = sorted({entry["origin"] for entry in self.cfg.get("car_od", [])})
        for origin in origins:
            self._try_spawn_car(origin, force=True)
        self._immediate_spawn_done = True

    def _spawn_traffic(self) -> None:
        rates = self.cfg["simulation"].get("poisson_rates_per_hour", {})
        level = self.cfg["simulation"].get("traffic_level", "medium")
        rate_per_hour = float(rates.get(level, 420.0))
        probability = rate_per_hour / 3600.0 * self.dt_s
        for origin in sorted({entry["origin"] for entry in self.cfg.get("car_od", [])}):
            if self.rng.random() < probability:
                self._try_spawn_car(origin)
        self._spawn_due_buses()

    def _try_spawn_car(self, origin: str, force: bool = False) -> bool:
        choices = [entry for entry in self.cfg.get("car_od", []) if entry["origin"] == origin]
        if not choices:
            return False
        weights = [float(item.get("weight", 1.0)) for item in choices]
        target = self.rng.choices(choices, weights=weights, k=1)[0]
        route = self.route_planner.route(origin, target["destination"]) if self.route_planner else []
        if not route:
            return False
        lane = self.lanes[route[0]]
        vehicle_length = 4.5
        required = vehicle_length + self.minimum_gap_m + 2.0
        if not lane.has_spawn_space(required):
            return False
        self._car_sequence += 1
        desired = min(lane.speed_limit_mps, self.rng.uniform(10.5, 15.5))
        car = Vehicle(
            id=f"C{self._car_sequence}",
            kind=VehicleKind.CAR,
            route_links=route,
            position_m=0.0,
            speed_mps=0.0,
            desired_speed_mps=desired,
            length_m=vehicle_length,
            width_m=1.8,
            max_accel=self.rng.uniform(1.0, 2.5),
            comfortable_decel=self.rng.uniform(2.0, 3.5),
            safe_gap_m=self.rng.uniform(4.5, 6.5),
            reaction_time_s=self.rng.uniform(0.9, 1.2),
            created_at_s=self.sim_time_s,
        )
        lane.vehicles.append(car)
        self.stats["spawnedCars"] += 1
        return True

    def _spawn_due_buses(self, force: bool = False) -> None:
        for route_id, route_cfg in self.cfg.get("bus_routes", {}).items():
            index = self._bus_dispatch_index.get(route_id, 0)
            max_buses = int(route_cfg.get("buses", 0))
            if index >= max_buses:
                continue
            departure = float(route_cfg.get("first_departure_s", 0.0)) + index * float(route_cfg.get("headway_s", 60.0))
            if not force and self.sim_time_s + 1e-9 < departure:
                continue
            route_links = list(route_cfg["links"])
            lane = self.lanes[route_links[0]]
            required = 11.5 + self.minimum_gap_m + 2.0
            if not lane.has_spawn_space(required):
                continue
            bus = Bus(
                id=f"{route_id}-{index + 1}",
                kind=VehicleKind.BUS,
                route_id=route_id,
                route_links=route_links,
                position_m=0.0,
                speed_mps=0.0,
                desired_speed_mps=min(lane.speed_limit_mps, 11.5),
                length_m=11.5,
                width_m=2.5,
                max_accel=1.3,
                comfortable_decel=2.5,
                safe_gap_m=6.0,
                reaction_time_s=1.1,
                created_at_s=self.sim_time_s,
                metadata={"scheduledDepartureS": departure, "wasCritical": False},
            )
            lane.vehicles.append(bus)
            self._bus_dispatch_index[route_id] = index + 1
            self.stats["spawnedBuses"] += 1

    # ------------------------------------------------------------------ buses/stops/headway
    def _next_bus_stop_position(self, vehicle: Vehicle, link_id: str) -> float | None:
        if not isinstance(vehicle, Bus) or not vehicle.route_id:
            return None
        route = self.cfg.get("bus_routes", {}).get(vehicle.route_id, {})
        stop_ids = route.get("stops", [])
        if vehicle.next_stop_index >= len(stop_ids):
            return None
        stop = self.cfg.get("stops", {}).get(stop_ids[vehicle.next_stop_index])
        if not stop or stop.get("link") != link_id:
            return None
        return float(stop["position_m"])

    def _start_bus_dwell(self, vehicle: Vehicle, position_m: float) -> None:
        if not isinstance(vehicle, Bus) or vehicle.dwell_remaining_s > 0.0:
            return
        vehicle.position_m = position_m
        vehicle.speed_mps = 0.0
        lo = float(self.cfg["transit"].get("dwell_min_s", 4.0))
        hi = float(self.cfg["transit"].get("dwell_max_s", 12.0))
        vehicle.dwell_remaining_s = self.rng.uniform(lo, hi)

    def _route_progress_m(self, bus: Bus) -> float:
        route = bus.route_links
        prefix = sum(float(self.cfg["links"][lid]["length_m"]) for lid in route[:bus.link_index])
        for transit in self.transits:
            if transit.vehicle.id == bus.id:
                current_len = float(self.cfg["links"][transit.from_link]["length_m"])
                return prefix + (current_len - self.intersection_half_size_m) + transit.progress * (2 * self.intersection_half_size_m)
        return prefix + bus.position_m

    def _all_active_buses(self) -> list[Bus]:
        buses: dict[str, Bus] = {}
        for lane in self.lanes.values():
            for vehicle in lane.vehicles:
                if isinstance(vehicle, Bus):
                    buses[vehicle.id] = vehicle
        for transit in self.transits:
            if isinstance(transit.vehicle, Bus):
                buses[transit.vehicle.id] = transit.vehicle
        return list(buses.values())

    def _update_bus_headways(self) -> None:
        nominal_speed = float(self.cfg["transit"].get("bus_nominal_speed_mps", 10.0))
        critical = float(self.cfg["transit"].get("critical_headway_s", 25.0))
        risk = float(self.cfg["transit"].get("risk_headway_s", 35.0))
        target_default = float(self.cfg["transit"].get("target_headway_s", 50.0))
        by_route: dict[str, list[Bus]] = defaultdict(list)
        for bus in self._all_active_buses():
            if bus.route_id:
                by_route[bus.route_id].append(bus)

        for route_id, buses in by_route.items():
            target = float(self.cfg.get("bus_routes", {}).get(route_id, {}).get("headway_s", target_default))
            ordered = sorted(buses, key=self._route_progress_m, reverse=True)
            for idx, bus in enumerate(ordered):
                previous = bus.headway_s
                if idx == 0:
                    bus.headway_s = None
                    bus.headway_trend_s_per_s = 0.0
                    bus.status = BusStatus.NORMAL
                    continue
                gap = max(0.0, self._route_progress_m(ordered[idx - 1]) - self._route_progress_m(bus))
                headway = gap / max(nominal_speed, 0.1)
                bus.headway_s = headway
                if previous is not None:
                    bus.headway_trend_s_per_s = (headway - previous) / max(self.dt_s, 1e-6)
                self.headway_samples.append(headway)
                if headway < critical:
                    bus.status = BusStatus.CRITICAL
                elif headway < risk:
                    bus.status = BusStatus.RISK
                elif headway < target * 0.8:
                    bus.status = BusStatus.EARLY
                elif headway > target * 1.2:
                    bus.status = BusStatus.LATE
                else:
                    bus.status = BusStatus.NORMAL

                was_critical = bool(bus.metadata.get("wasCritical", False))
                now_critical = bus.status == BusStatus.CRITICAL
                if now_critical and not was_critical:
                    self.stats["bunchingEvents"] += 1
                bus.metadata["wasCritical"] = now_critical

    # ------------------------------------------------------------------ perception / communication
    def _incoming_lane_for_branch(self, intersection_id: str, branch: str) -> RoadLane | None:
        for link_id, link in self.cfg["links"].items():
            if link["to"] == intersection_id and link.get("to_branch") == branch:
                return self.lanes[link_id]
        return None

    def _observation_for(self, intersection_id: str) -> list[float]:
        values: list[float] = []
        for branch in self.BRANCH_ORDER:
            lane = self._incoming_lane_for_branch(intersection_id, branch)
            if lane and lane.camera:
                values.extend(lane.camera.state_vector(lane.vehicles))
            else:
                values.extend([0.0] * 5)

        nearby = self._bus_gps_summary(intersection_id)
        values.extend(nearby)
        neighbor_ids = self.cfg["intersections"][intersection_id].get("neighbors", [])
        if neighbor_ids:
            message = self.neighbor_messages.get(neighbor_ids[0])
            if message:
                phase_count = max(1, self.controllers[neighbor_ids[0]].phase_count - 1)
                values.extend([
                    min(message.congestion, 1.5),
                    1.0 if message.critical_bus else 0.0,
                    min((message.nearest_bus_eta_s or 120.0) / 120.0, 2.0),
                    message.current_phase / phase_count,
                ])
            else:
                values.extend([0.0, 0.0, 1.0, 0.0])
        else:
            values.extend([0.0] * 4)
        return values

    def _bus_gps_summary(self, intersection_id: str) -> list[float]:
        horizon = float(self.cfg["transit"].get("gps_horizon_m", 420.0))
        candidates = []
        for bus in self._all_active_buses():
            distance = self._distance_to_intersection(bus, intersection_id)
            if distance is None or distance > horizon:
                continue
            eta = distance / max(bus.speed_mps, 3.0)
            candidates.append((distance, eta, bus))
        if not candidates:
            return [1.0, 0.0, 0.0, 0.0, 0.0]
        _, eta, nearest = min(candidates, key=lambda item: item[0])
        target = float(self.cfg["transit"].get("target_headway_s", 50.0))
        headway_ratio = (nearest.headway_s / target) if nearest.headway_s is not None else 1.0
        return [
            min(eta / 120.0, 2.0),
            1.0 if nearest.status == BusStatus.LATE else 0.0,
            1.0 if nearest.status in {BusStatus.RISK, BusStatus.CRITICAL} else 0.0,
            min(headway_ratio, 2.0),
            min(nearest.waiting_time_s / 60.0, 2.0),
        ]

    def _distance_to_intersection(self, bus: Bus, intersection_id: str) -> float | None:
        route = bus.route_links
        if bus.link_index >= len(route):
            return None
        distance = 0.0
        current = route[bus.link_index]
        current_cfg = self.cfg["links"][current]
        if current_cfg["to"] == intersection_id:
            lane = self.lanes[current]
            target = lane.stop_line_m if lane.stop_line_m is not None else lane.length_m
            return max(0.0, target - bus.position_m)
        distance += max(0.0, float(current_cfg["length_m"]) - bus.position_m)
        for lid in route[bus.link_index + 1:]:
            link = self.cfg["links"][lid]
            if link["to"] == intersection_id:
                lane = self.lanes[lid]
                distance += lane.stop_line_m if lane.stop_line_m is not None else lane.length_m
                return distance
            distance += float(link["length_m"])
        return None

    def _broadcast_neighbor_messages(self) -> None:
        messages = {}
        for iid, controller in self.controllers.items():
            densities = []
            for branch in self.BRANCH_ORDER:
                lane = self._incoming_lane_for_branch(iid, branch)
                if lane and lane.camera:
                    densities.append(lane.camera.state_vector(lane.vehicles)[0])
            buses = []
            for bus in self._all_active_buses():
                distance = self._distance_to_intersection(bus, iid)
                if distance is not None:
                    buses.append((distance, bus))
            nearest_eta = None
            if buses:
                distance, bus = min(buses, key=lambda item: item[0])
                nearest_eta = distance / max(bus.speed_mps, 3.0)
            messages[iid] = NeighborMessage(
                sender_id=iid,
                timestamp_s=self.sim_time_s,
                congestion=sum(densities) / max(len(densities), 1),
                current_phase=controller.current_phase,
                nearest_bus_eta_s=nearest_eta,
                critical_bus=any(bus.status in {BusStatus.RISK, BusStatus.CRITICAL} for _, bus in buses[:4]),
            )
        self.neighbor_messages = messages

    def _tick_cameras(self) -> None:
        for link_id, lane in self.lanes.items():
            if not lane.camera:
                continue
            link = self.cfg["links"][link_id]
            iid = link["to"]
            branch = link.get("to_branch")
            green = self.controllers[iid].branch_color(branch) == SignalColor.GREEN
            lane.camera.tick(self.sim_time_s, self.dt_s, green)

    # ------------------------------------------------------------------ reward
    def _compute_rewards(self) -> tuple[dict[str, float], dict[str, dict]]:
        weights = self.cfg["reward"]
        target = float(self.cfg["transit"].get("target_headway_s", 50.0))
        critical = float(self.cfg["transit"].get("critical_headway_s", 25.0))
        risk = float(self.cfg["transit"].get("risk_headway_s", 35.0))
        rewards = {}
        breakdown = {}
        for iid in self.logic:
            densities = []
            waits = []
            bus_wait = 0.0
            nearby_buses: list[Bus] = []
            for branch in self.BRANCH_ORDER:
                lane = self._incoming_lane_for_branch(iid, branch)
                if not lane or not lane.camera:
                    continue
                roi = lane.camera.vehicles_in_roi(lane.vehicles)
                densities.append(lane.camera.state_vector(lane.vehicles)[0])
                waits.extend(v.waiting_time_s for v in roi)
                for vehicle in roi:
                    if isinstance(vehicle, Bus):
                        bus_wait += vehicle.waiting_time_s
                        nearby_buses.append(vehicle)

            outflow = float(self._interval_stats[iid]["outflow"])
            density = sum(densities) / max(len(densities), 1)
            max_wait = max(waits, default=0.0)
            headway_dev = 0.0
            risk_count = 0
            critical_count = 0
            for bus in nearby_buses:
                if bus.headway_s is not None:
                    headway_dev += abs(bus.headway_s - target) / max(target, 1.0)
                    if bus.headway_s < risk:
                        risk_count += 1
                    if bus.headway_s < critical:
                        critical_count += 1

            changed = 1.0 if self._interval_stats[iid]["phaseChanged"] else 0.0
            parts = {
                "outflow": float(weights["vehicle_outflow"]) * outflow,
                "density": float(weights["density"]) * density,
                "waiting": float(weights["waiting"]) * min(max_wait / 60.0, 3.0),
                "busWaiting": float(weights["bus_waiting"]) * min(bus_wait / 60.0, 4.0),
                "headwayDeviation": float(weights["headway_deviation"]) * headway_dev,
                "bunchingRisk": float(weights["bunching_risk"]) * risk_count,
                "bunchingConfirmed": float(weights["bunching_confirmed"]) * critical_count,
                "phaseChange": float(weights["phase_change"]) * changed,
            }
            reward = sum(parts.values())
            parts["reward"] = reward
            rewards[iid] = reward
            breakdown[iid] = parts
        return rewards, breakdown

    # ------------------------------------------------------------------ completion / helpers
    def _finish_vehicle(self, vehicle: Vehicle) -> None:
        vehicle.finished_at_s = self.sim_time_s
        travel_time = max(0.0, self.sim_time_s - vehicle.created_at_s)
        if isinstance(vehicle, Bus):
            self.stats["completedBuses"] += 1
            self.stats["busTravelTimes"].append(travel_time)
        else:
            self.stats["completedCars"] += 1
            self.stats["carTravelTimes"].append(travel_time)

    def active_vehicles(self) -> list[Vehicle]:
        result: dict[str, Vehicle] = {}
        for lane in self.lanes.values():
            for vehicle in lane.vehicles:
                result[vehicle.id] = vehicle
        for transit in self.transits:
            result[transit.vehicle.id] = transit.vehicle
        return list(result.values())

    def transit_for_vehicle(self, vehicle_id: str) -> IntersectionTransit | None:
        return next((item for item in self.transits if item.vehicle.id == vehicle_id), None)

    def assert_no_overlap(self) -> None:
        """Invariante de regresión: ningún par del mismo carril se solapa."""
        for lane in self.lanes.values():
            ordered = sorted(lane.vehicles, key=lambda v: -v.position_m)
            for leader, follower in zip(ordered, ordered[1:]):
                gap = leader.position_m - leader.length_m - follower.position_m
                if gap + 1e-6 < self.minimum_gap_m:
                    raise AssertionError(
                        f"Solapamiento en {lane.link_id}: {leader.id}/{follower.id}, gap={gap:.3f}"
                    )

    def action_masks(self) -> dict[str, list[bool]]:
        return {iid: self.legal_action_mask(iid) for iid in self.logic}

    def heuristic_actions(self) -> dict[str, int]:
        """Baseline seguro: elige la fase legal con mayor presión de cola/bus."""
        actions = {}
        for iid, controller in self.controllers.items():
            mask = controller.legal_action_mask()
            best_phase = controller.current_phase
            best_score = -float("inf")
            for phase in self.logic[iid].phases:
                if phase.index >= len(mask) or not mask[phase.index]:
                    continue
                branches = {movement.from_branch for movement in phase.movements}
                score = 0.0
                for branch in branches:
                    lane = self._incoming_lane_for_branch(iid, branch)
                    if not lane or not lane.camera:
                        continue
                    roi = lane.camera.vehicles_in_roi(lane.vehicles)
                    score += len(roi)
                    score += 4.0 * sum(isinstance(vehicle, Bus) for vehicle in roi)
                    score += 0.03 * sum(vehicle.waiting_time_s for vehicle in roi)
                if score > best_score:
                    best_score = score
                    best_phase = phase.index
            actions[iid] = best_phase
        return actions
