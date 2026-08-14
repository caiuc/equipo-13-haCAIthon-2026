from simulacion.trafico.multi_agent_environment import MultiAgentTrafficEnv


def test_red_stops_before_intersection_and_no_lane_overlap(cfg, logic):
    env = MultiAgentTrafficEnv(cfg, logic, episode_seconds=80, seed=7)
    # Fase 0 = N/S. E/O permanece rojo el tiempo suficiente para formar cola.
    for _ in range(8):
        env.step({"i1": 0, "i2": 0})
        env.assert_no_overlap()
    for link_id in ("w_i1", "e_i2"):
        lane = env.lanes[link_id]
        assert all(vehicle.position_m <= lane.stop_line_m + 1e-6 for vehicle in lane.vehicles)


def test_green_yellow_red_then_new_green_is_visible(cfg, logic):
    env = MultiAgentTrafficEnv(cfg, logic, episode_seconds=40, seed=2)
    env.step({"i1": 0, "i2": 0})  # 0..5, aún dentro de verde mínimo
    env.step({"i1": 0, "i2": 0})  # 5..10, ya se puede cambiar
    colors = []
    env.step(
        {"i1": 1, "i2": 1},
        on_substep=lambda current: colors.append((
            current.controllers["i1"].branch_color("north").value,
            current.controllers["i1"].branch_color("west").value,
        )) or True,
    )
    assert ("YELLOW", "RED") in colors
    assert ("RED", "GREEN") in colors


def test_conflicting_transits_never_share_intersection(cfg, logic):
    env = MultiAgentTrafficEnv(cfg, logic, episode_seconds=100, seed=11)
    for decision in range(16):
        actions = {"i1": decision % 2, "i2": (decision // 2) % 2}
        masks = env.action_masks()
        safe = {iid: action if masks[iid][action] else env.controllers[iid].current_phase for iid, action in actions.items()}
        def check(current):
            by_iid = {}
            for transit in current.transits:
                by_iid.setdefault(transit.intersection_id, []).append(transit.movement_key)
            for iid, movement_keys in by_iid.items():
                for i, first in enumerate(movement_keys):
                    for second in movement_keys[i+1:]:
                        assert first != second
                        assert frozenset((first, second)) not in current.logic[iid].conflicts
            current.assert_no_overlap()
            return True
        env.step(safe, on_substep=check)
