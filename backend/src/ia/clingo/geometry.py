from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CandidateMovement:
    lane_id: str
    from_branch: str
    to_branch: str
    turn: str
    entry: tuple[float, float]
    exit: tuple[float, float]


def _norm(angle: float) -> float:
    return angle % 360.0


def _angular_distance(a: float, b: float) -> float:
    d = abs((_norm(a) - _norm(b) + 180.0) % 360.0 - 180.0)
    return d


def target_branch(branches: dict, from_branch: str, turn: str) -> str | None:
    """Selecciona la rama de salida más compatible con el giro solicitado.

    La orientación de una rama apunta desde el centro hacia el exterior. Un vehículo
    que entra desde esa rama llega al centro con rumbo orientación+180. Tras girar,
    la salida ideal está a +90 (izq), 0 (recto) o -90 (der) respecto a ese rumbo.
    """
    ori = float(branches[from_branch]['orientation_deg'])
    inbound_heading = _norm(ori + 180.0)
    offset = {'left': 90.0, 'straight': 0.0, 'right': -90.0}[turn]
    desired_out = _norm(inbound_heading + offset)
    candidates = [(bid, _angular_distance(float(b['orientation_deg']), desired_out))
                  for bid, b in branches.items() if bid != from_branch]
    if not candidates:
        return None
    bid, distance = min(candidates, key=lambda x: x[1])
    # Con topologías irregulares aceptamos hasta 75 grados de desviación.
    return bid if distance <= 75.0 else None


def point_on_branch(angle_deg: float, radius: float = 1.0) -> tuple[float, float]:
    a = math.radians(angle_deg)
    return (radius * math.cos(a), radius * math.sin(a))


def build_candidates(intersection: dict) -> list[CandidateMovement]:
    branches = intersection['branches']
    result: list[CandidateMovement] = []
    for lane_id, lane in intersection.get('incoming_lanes', {}).items():
        frm = lane['branch']
        entry = point_on_branch(float(branches[frm]['orientation_deg']))
        for turn in lane.get('allowed_turns', []):
            to = target_branch(branches, frm, turn)
            if to is None:
                continue
            exit_pt = point_on_branch(float(branches[to]['orientation_deg']))
            result.append(CandidateMovement(lane_id, frm, to, turn, entry, exit_pt))
    return result


def _orient(a, b, c) -> float:
    return (b[0]-a[0]) * (c[1]-a[1]) - (b[1]-a[1]) * (c[0]-a[0])


def _segments_intersect(a, b, c, d, eps: float = 1e-9) -> bool:
    o1, o2, o3, o4 = _orient(a,b,c), _orient(a,b,d), _orient(c,d,a), _orient(c,d,b)
    return (o1 * o2 < -eps) and (o3 * o4 < -eps)


def geometric_conflicts(candidates: Iterable[CandidateMovement]) -> set[tuple[str, str, str, str]]:
    """Genera relaciones geométricas neutrales para el solver ASP.

    No decide fases ni contiene pares específicos de una intersección. Se limita a
    detectar intersección de trayectorias derivadas de coordenadas normalizadas.
    También trata convergencia a una misma salida desde accesos distintos como zona
    compartida potencialmente conflictiva.
    """
    items = list(candidates)
    conflicts: set[tuple[str, str, str, str]] = set()
    for i, m1 in enumerate(items):
        for m2 in items[i+1:]:
            if m1.lane_id == m2.lane_id:
                continue
            crossing = _segments_intersect(m1.entry, m1.exit, m2.entry, m2.exit)
            merge = m1.to_branch == m2.to_branch and m1.from_branch != m2.from_branch
            # Movimientos exactamente opuestos rectos comparten centro.
            center_overlap = (m1.turn == 'straight' and m2.turn == 'straight'
                              and m1.to_branch == m2.from_branch
                              and m2.to_branch == m1.from_branch)
            if crossing or merge or center_overlap:
                conflicts.add((m1.lane_id, m1.to_branch, m2.lane_id, m2.to_branch))
    return conflicts


def _bezier_point(p0, p1, p2, t: float) -> tuple[float,float]:
    u=1.0-t
    return (u*u*p0[0]+2*u*t*p1[0]+t*t*p2[0],
            u*u*p0[1]+2*u*t*p1[1]+t*t*p2[1])


def movement_zones(m: CandidateMovement, grid: int = 7) -> set[str]:
    """Discretiza una trayectoria en zonas neutrales de ocupación.

    El objetivo es aportar hechos espaciales a ASP, no decidir incompatibilidades.
    Los giros derechos se curvan hacia el borde; rectos/izquierdos atraviesan una
    zona más interior. Se agrega una zona de convergencia por rama de salida.
    """
    if m.turn == 'right':
        control=((m.entry[0]+m.exit[0])*0.78,(m.entry[1]+m.exit[1])*0.78)
    elif m.turn == 'left':
        control=(0.0,0.0)
    else:
        control=(0.0,0.0)
    zones={f'exit_{m.to_branch}'}
    # Excluye extremos para no convertir una aproximación compartida en conflicto
    # entre carriles paralelos; la convergencia de salida sí se modela aparte.
    for k in range(2,9):
        t=k/10.0
        x,y=_bezier_point(m.entry,control,m.exit,t)
        gx=max(0,min(grid-1,int((x+1.0)*0.5*grid)))
        gy=max(0,min(grid-1,int((y+1.0)*0.5*grid)))
        zones.add(f'z{gx}_{gy}')
    return zones


def occupancy_facts(candidates: Iterable[CandidateMovement]) -> dict[tuple[str,str],set[str]]:
    return {(m.lane_id,m.to_branch):movement_zones(m) for m in candidates}
