from __future__ import annotations

from common.domain_models import IntersectionLogic, SignalColor


class SignalController:
    """Máquina de estados inspirada directamente en TrafficLight de Empresa.zip.

    El agente solicita una FASE, nunca luces individuales. El controlador aplica
    verde mínimo, amarillo obligatorio y máximo de rojo.
    """

    def __init__(self, logic: IntersectionLogic, min_green_s: float, yellow_s: float, max_red_s: float):
        if not logic.phases:
            raise ValueError(f"{logic.intersection_id} no posee fases legales")
        self.logic = logic
        self.min_green_s = float(min_green_s)
        self.yellow_s = float(yellow_s)
        self.max_red_s = float(max_red_s)
        self.current_phase = 0
        self.pending_phase: int | None = None
        self.color_state = SignalColor.GREEN
        self.time_in_color_s = 0.0
        self.time_in_phase_s = 0.0
        self.red_timers = {phase.index: 0.0 for phase in logic.phases}
        self.phase_changed_this_step = False
        self.last_requested_phase = 0

    @property
    def phase_count(self) -> int:
        return len(self.logic.phases)

    def legal_action_mask(self) -> list[bool]:
        mask = [True] * self.phase_count
        if self.color_state == SignalColor.YELLOW:
            return [idx == (self.pending_phase if self.pending_phase is not None else self.current_phase)
                    for idx in range(self.phase_count)]
        if self.time_in_phase_s < self.min_green_s:
            return [idx == self.current_phase for idx in range(self.phase_count)]

        overdue = [idx for idx, value in self.red_timers.items()
                   if idx != self.current_phase and value >= self.max_red_s]
        if overdue:
            return [idx in overdue for idx in range(self.phase_count)]
        return mask

    def request_is_legal(self, phase_index: int) -> bool:
        mask = self.legal_action_mask()
        return 0 <= phase_index < len(mask) and mask[phase_index]

    def step(self, requested_phase: int | None, dt_s: float) -> None:
        self.phase_changed_this_step = False
        if requested_phase is not None:
            self.last_requested_phase = int(requested_phase)

        if self.color_state == SignalColor.YELLOW:
            self.time_in_color_s += dt_s
            if self.time_in_color_s + 1e-9 >= self.yellow_s:
                self.current_phase = self.pending_phase if self.pending_phase is not None else self.current_phase
                self.pending_phase = None
                self.color_state = SignalColor.GREEN
                self.time_in_color_s = 0.0
                self.time_in_phase_s = 0.0
        else:
            selected = self.current_phase if requested_phase is None else int(requested_phase)
            if selected != self.current_phase and self.request_is_legal(selected):
                self.pending_phase = selected
                self.color_state = SignalColor.YELLOW
                self.time_in_color_s = 0.0
                self.phase_changed_this_step = True
            else:
                self.time_in_color_s += dt_s
                self.time_in_phase_s += dt_s

        for idx in self.red_timers:
            if idx == self.current_phase and self.color_state == SignalColor.GREEN:
                self.red_timers[idx] = 0.0
            else:
                self.red_timers[idx] += dt_s

    def movement_color(self, movement_key: str) -> SignalColor:
        active = {m.key for m in self.logic.phases[self.current_phase].movements}
        if movement_key not in active:
            return SignalColor.RED
        return self.color_state

    def branch_color(self, branch: str) -> SignalColor:
        phase = self.logic.phases[self.current_phase]
        active_from_branch = any(m.from_branch == branch for m in phase.movements)
        if not active_from_branch:
            return SignalColor.RED
        return self.color_state
