from __future__ import annotations

import random
import networkx as nx


class RoutePlanner:
    def __init__(self, cfg: dict, rng: random.Random, logic: dict | None = None):
        self.cfg = cfg
        self.rng = rng
        self.logic = logic or {}
        self.graph = nx.DiGraph()
        for lid, link in cfg['links'].items():
            self.graph.add_edge(link['from'], link['to'], link_id=lid, weight=float(link['length_m']))

    def _links_from_nodes(self, nodes: list[str]) -> list[str]:
        return [self.graph[a][b]['link_id'] for a,b in zip(nodes, nodes[1:])]

    def is_legal_link_route(self, links: list[str]) -> bool:
        for a,b in zip(links, links[1:]):
            cur,nxt=self.cfg['links'][a],self.cfg['links'][b]
            iid=cur['to']
            if self.cfg['nodes'].get(iid,{}).get('kind') != 'intersection':
                continue
            frm,to=cur.get('to_branch'),nxt.get('from_branch')
            if not frm or not to:
                return False
            if iid in self.logic:
                if not any(m.from_branch==frm and m.to_branch==to for m in self.logic[iid].movements):
                    return False
            else:
                # Fallback topológico para utilidades que se usan sin solver.
                from ia.clingo.geometry import target_branch
                inter=self.cfg['intersections'][iid]
                possible=False
                for lane in inter.get('incoming_lanes',{}).values():
                    if lane['branch'] != frm: continue
                    for turn in lane.get('allowed_turns',[]):
                        if target_branch(inter['branches'],frm,turn)==to:
                            possible=True; break
                    if possible: break
                if not possible: return False
        return True

    def route(self, origin: str, destination: str) -> list[str]:
        try:
            paths=[]
            # Revisa hasta 12 candidatas para descartar trayectorias topológicamente imposibles.
            for i,path in enumerate(nx.shortest_simple_paths(self.graph,origin,destination,weight='weight')):
                links=self._links_from_nodes(path)
                if self.is_legal_link_route(links): paths.append(links)
                if i>=11 or len(paths)>=4: break
        except (nx.NetworkXNoPath,nx.NodeNotFound):
            return []
        if not paths: return []
        weights=[1.0/(1.0+i) for i in range(len(paths))]
        return self.rng.choices(paths,weights=weights,k=1)[0]
