from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from common.domain_models import IntersectionLogic, Movement, Phase
from ia.clingo.geometry import build_candidates, occupancy_facts

try:
    import clingo
except ImportError:  # pragma: no cover
    clingo = None


_FORBIDDEN_CUSTOM_DIRECTIVES = ("#script", "#include")


def atom(value: str) -> str:
    safe = ''.join(ch if ch.isalnum() or ch == '_' else '_' for ch in str(value)).lower()
    if not safe or safe[0].isdigit():
        safe = 'x_' + safe
    return safe


def validate_custom_program(program: str | None) -> str:
    """Valida reglas ASP recibidas desde UI antes de entregarlas a Clingo.

    El archivo se agrega al núcleo ``rules.lp``. Se prohíben directivas que puedan
    ejecutar código embebido o leer archivos del servidor. El programa sigue
    pudiendo declarar hechos, restricciones, reglas y optimizaciones ASP normales.
    """
    if not program:
        return ""
    if not isinstance(program, str):
        raise ValueError("clingoProgram debe ser texto")
    if len(program.encode("utf-8")) > 200_000:
        raise ValueError("El archivo Clingo no puede superar 200 KB")
    lowered = program.lower()
    forbidden = [directive for directive in _FORBIDDEN_CUSTOM_DIRECTIVES if directive in lowered]
    if forbidden:
        raise ValueError(f"Directiva Clingo no permitida: {', '.join(forbidden)}")
    return program.strip()


class ClingoTopologyEngine:
    def __init__(self, rules_path: str | Path | None = None, extra_program: str | None = None):
        self.rules_path = Path(rules_path) if rules_path else Path(__file__).with_name('rules.lp')
        self.extra_program = validate_custom_program(extra_program)

    def _facts_for_intersection(self, iid: str, inter: dict[str, Any]) -> tuple[str, dict[str, str]]:
        names: dict[str, str] = {}
        I = atom(iid); names[I] = iid
        lines = [f'intersection({I}).']
        for bid, b in inter['branches'].items():
            B = atom(bid); names[B] = bid
            lines.append(f'branch({I},{B},{int(round(float(b["orientation_deg"])))}).')
        candidates = build_candidates(inter)
        for lane_id, lane in inter.get('incoming_lanes', {}).items():
            L, B = atom(lane_id), atom(lane['branch'])
            names[L], names[B] = lane_id, lane['branch']
            lines.append(f'lane({I},{L},{B}).')
            for t in lane.get('allowed_turns', []):
                lines.append(f'lane_allows({I},{L},{atom(t)}).')
        seen_targets = set()
        for candidate in candidates:
            key = (candidate.from_branch, candidate.turn, candidate.to_branch)
            if key not in seen_targets:
                seen_targets.add(key)
                lines.append(
                    f'turn_target({I},{atom(candidate.from_branch)},{atom(candidate.turn)},{atom(candidate.to_branch)}).'
                )
                names[atom(candidate.to_branch)] = candidate.to_branch
        for (lane_id, to_branch), zones in occupancy_facts(candidates).items():
            for zone in sorted(zones):
                lines.append(f'occupies({I},{atom(lane_id)},{atom(to_branch)},{atom(zone)}).')
        return '\n'.join(lines), names

    def solve(self, cfg: dict[str, Any]) -> dict[str, IntersectionLogic]:
        if clingo is None:
            raise RuntimeError('Clingo no está instalado. Ejecute: pip install clingo>=5.7,<6')

        all_logic: dict[str, IntersectionLogic] = {}
        rules = self.rules_path.read_text(encoding='utf-8')
        for iid, inter in cfg['intersections'].items():
            facts, names = self._facts_for_intersection(iid, inter)
            program = f"{rules}\n{facts}"
            if self.extra_program:
                program = f"{program}\n% --- Reglas cargadas por el usuario ---\n{self.extra_program}\n"

            ctl = clingo.Control(['0'])
            ctl.configuration.solve.opt_mode = 'optN'
            ctl.add('base', [], program)
            ctl.ground([('base', [])])

            best_symbols = None
            best_cost = None
            with ctl.solve(yield_=True) as handle:
                for model in handle:
                    cost = tuple(model.cost)
                    if best_cost is None or cost <= best_cost:
                        best_cost = cost
                        best_symbols = model.symbols(shown=True)
            if best_symbols is None:
                raise RuntimeError(f'Clingo no encontró una solución legal para {iid}')

            movements: dict[tuple[str, str], Movement] = {}
            conflicts: set[frozenset[str]] = set()
            phase_members: dict[int, list[Movement]] = defaultdict(list)

            for symbol in best_symbols:
                if symbol.name == 'movement' and len(symbol.arguments) == 5:
                    _, lane_atom, from_atom, to_atom, turn_atom = symbol.arguments
                    lane, frm, to, turn = map(str, (lane_atom, from_atom, to_atom, turn_atom))
                    movement = Movement(
                        iid,
                        names.get(lane, lane),
                        names.get(frm, frm),
                        names.get(to, to),
                        names.get(turn, turn),
                    )
                    movements[(lane, to)] = movement

            for symbol in best_symbols:
                if symbol.name == 'conflict' and len(symbol.arguments) == 5:
                    _, lane1, to1, lane2, to2 = symbol.arguments
                    first = movements.get((str(lane1), str(to1)))
                    second = movements.get((str(lane2), str(to2)))
                    if first and second:
                        conflicts.add(frozenset((first.key, second.key)))
                elif symbol.name == 'in_phase' and len(symbol.arguments) == 4:
                    _, lane_atom, to_atom, phase_atom = symbol.arguments
                    movement = movements.get((str(lane_atom), str(to_atom)))
                    if movement:
                        phase_members[int(str(phase_atom))].append(movement)

            phases = [Phase(index=phase_id - 1, movements=phase_members[phase_id]) for phase_id in sorted(phase_members)]
            logic = IntersectionLogic(iid, list(movements.values()), conflicts, phases)
            self.assert_safe(logic)
            all_logic[iid] = logic
        return all_logic

    @staticmethod
    def assert_safe(logic: IntersectionLogic) -> None:
        for phase in logic.phases:
            keys = [movement.key for movement in phase.movements]
            for index, first in enumerate(keys):
                for second in keys[index + 1:]:
                    if frozenset((first, second)) in logic.conflicts:
                        raise AssertionError(f'Fase insegura en {logic.intersection_id}: {first} vs {second}')
