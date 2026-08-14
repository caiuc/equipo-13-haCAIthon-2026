from __future__ import annotations

from dataclasses import dataclass

from common.domain_models import IntersectionLogic, SignalMode


@dataclass
class ControllerState:
    phase_index: int
    mode: SignalMode
    elapsed_s: float
    pending_phase: int | None


class SignalController:
    def __init__(self, logic: IntersectionLogic, min_green_s: float, yellow_s: float, max_red_s: float):
        if not logic.phases:
            raise ValueError(f'{logic.intersection_id} no posee fases legales')
        self.logic = logic
        self.min_green_s = float(min_green_s)
        self.yellow_s = float(yellow_s)
        self.max_red_s = float(max_red_s)
        self.phase_index = 0
        self.mode = SignalMode.GREEN
        self.elapsed_s = 0.0
        self.pending_phase: int | None = None
        self.red_elapsed = {m.key: 0.0 for m in logic.movements}
        self.phase_changes = 0
        self.restriction_counts = {'yellow_lock':0,'min_green':0,'max_red':0}

    def state(self) -> ControllerState:
        return ControllerState(self.phase_index, self.mode, self.elapsed_s, self.pending_phase)

    def phase_keys(self, index: int | None = None) -> set[str]:
        idx = self.phase_index if index is None else index
        return {m.key for m in self.logic.phases[idx].movements}

    def is_green(self, lane_id: str, to_branch: str) -> bool:
        if self.mode != SignalMode.GREEN:
            return False
        return f'{lane_id}->{to_branch}' in self.phase_keys()

    def assert_safe_phase(self, phase_index: int) -> None:
        keys = list(self.phase_keys(phase_index))
        for i,a in enumerate(keys):
            for b in keys[i+1:]:
                if frozenset((a,b)) in self.logic.conflicts:
                    raise AssertionError(f'Fase {phase_index} insegura: {a} y {b}')

    def action_mask(self) -> list[bool]:
        n = len(self.logic.phases)
        if self.mode == SignalMode.YELLOW:
            self.restriction_counts['yellow_lock'] += 1
            # No se acepta una nueva decisión durante la transición.
            return [i == (self.pending_phase if self.pending_phase is not None else self.phase_index) for i in range(n)]
        if self.elapsed_s < self.min_green_s:
            self.restriction_counts['min_green'] += 1
            return [i == self.phase_index for i in range(n)]

        overdue = {k for k,t in self.red_elapsed.items() if t >= self.max_red_s}
        if overdue:
            candidates = [bool(self.phase_keys(i) & overdue) for i in range(n)]
            if any(candidates):
                self.restriction_counts['max_red'] += 1
                return candidates
        return [True] * n

    def request_phase(self, phase_index: int) -> bool:
        if not 0 <= phase_index < len(self.logic.phases):
            return False
        mask = self.action_mask()
        if not mask[phase_index]:
            return False
        self.assert_safe_phase(phase_index)
        if phase_index == self.phase_index:
            return True
        self.mode = SignalMode.YELLOW
        self.elapsed_s = 0.0
        self.pending_phase = phase_index
        return True

    def tick(self, dt: float) -> None:
        dt = float(dt)
        self.elapsed_s += dt
        if self.mode == SignalMode.YELLOW and self.elapsed_s >= self.yellow_s:
            assert self.pending_phase is not None
            self.phase_index = self.pending_phase
            self.pending_phase = None
            self.mode = SignalMode.GREEN
            self.elapsed_s = 0.0
            self.phase_changes += 1

        active = self.phase_keys() if self.mode == SignalMode.GREEN else set()
        for key in self.red_elapsed:
            self.red_elapsed[key] = 0.0 if key in active else self.red_elapsed[key] + dt
