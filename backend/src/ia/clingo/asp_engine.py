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


def atom(value: str) -> str:
    safe = ''.join(ch if ch.isalnum() or ch == '_' else '_' for ch in str(value)).lower()
    if not safe or safe[0].isdigit():
        safe = 'x_' + safe
    return safe


class ClingoTopologyEngine:
    def __init__(self, rules_path: str | Path | None = None):
        self.rules_path = Path(rules_path) if rules_path else Path(__file__).with_name('rules.lp')

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
        for c in candidates:
            key = (c.from_branch, c.turn, c.to_branch)
            if key not in seen_targets:
                seen_targets.add(key)
                lines.append(f'turn_target({I},{atom(c.from_branch)},{atom(c.turn)},{atom(c.to_branch)}).')
                names[atom(c.to_branch)] = c.to_branch
        for (lane_id,to_branch), zones in occupancy_facts(candidates).items():
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
            ctl = clingo.Control(['0'])
            ctl.configuration.solve.opt_mode = 'optN'
            ctl.add('base', [], rules + '\n' + facts)
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

            # Primero movimientos para poder mapear in_phase.
            for s in best_symbols:
                if s.name == 'movement' and len(s.arguments) == 5:
                    _, L, F, T, Turn = s.arguments
                    lane, frm, to, turn = map(str, (L,F,T,Turn))
                    m = Movement(iid, names.get(lane,lane), names.get(frm,frm), names.get(to,to), names.get(turn,turn))
                    movements[(lane,to)] = m

            for s in best_symbols:
                if s.name == 'conflict' and len(s.arguments) == 5:
                    _, L1,T1,L2,T2 = s.arguments
                    k1 = movements.get((str(L1), str(T1)))
                    k2 = movements.get((str(L2), str(T2)))
                    if k1 and k2:
                        conflicts.add(frozenset((k1.key, k2.key)))
                elif s.name == 'in_phase' and len(s.arguments) == 4:
                    _, L,T,P = s.arguments
                    m = movements.get((str(L), str(T)))
                    if m:
                        phase_members[int(str(P))].append(m)

            phases = [Phase(index=p-1, movements=phase_members[p]) for p in sorted(phase_members)]
            logic = IntersectionLogic(iid, list(movements.values()), conflicts, phases)
            self.assert_safe(logic)
            all_logic[iid] = logic
        return all_logic

    @staticmethod
    def assert_safe(logic: IntersectionLogic) -> None:
        for phase in logic.phases:
            keys = [m.key for m in phase.movements]
            for i, a in enumerate(keys):
                for b in keys[i+1:]:
                    if frozenset((a,b)) in logic.conflicts:
                        raise AssertionError(f'Fase insegura en {logic.intersection_id}: {a} vs {b}')
