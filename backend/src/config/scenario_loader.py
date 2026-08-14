from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with path.open('r', encoding='utf-8') as fh:
        cfg = yaml.safe_load(fh)
    validate_config(cfg)
    return cfg


def validate_config(cfg: dict[str, Any]) -> None:
    required = ['simulation', 'signals', 'transit', 'rl', 'reward', 'nodes', 'links', 'intersections']
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ValueError(f'Configuración incompleta. Faltan: {missing}')

    for iid, inter in cfg['intersections'].items():
        if iid not in cfg['nodes']:
            raise ValueError(f'Intersección {iid!r} no existe en nodes')
        branches = inter.get('branches', {})
        if len(branches) < 2:
            raise ValueError(f'Intersección {iid!r} debe tener al menos dos ramas')
        for lane_id, lane in inter.get('incoming_lanes', {}).items():
            if lane.get('branch') not in branches:
                raise ValueError(f'Carril {lane_id!r} referencia rama inexistente en {iid}')
            turns = lane.get('allowed_turns', [])
            invalid = set(turns) - {'left', 'straight', 'right'}
            if invalid:
                raise ValueError(f'Carril {lane_id!r}: giros no soportados {invalid}')

    for lid, link in cfg['links'].items():
        if link['from'] not in cfg['nodes'] or link['to'] not in cfg['nodes']:
            raise ValueError(f'Link {lid!r} contiene nodos inexistentes')
        if float(link['length_m']) <= 0:
            raise ValueError(f'Link {lid!r} debe tener length_m > 0')
