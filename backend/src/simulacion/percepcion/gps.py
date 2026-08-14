from __future__ import annotations


class GPSPerception:
    def __init__(self, cfg: dict, network):
        self.cfg = cfg
        self.network = network
        self.horizon_m = float(cfg['transit'].get('gps_horizon_m', 700.0))

    def distance_to_intersection(self, bus, intersection_id: str) -> float | None:
        distance = -bus.position_m
        for idx in range(bus.link_index, len(bus.route_links)):
            lid = bus.route_links[idx]
            link = self.cfg['links'][lid]
            distance += float(link['length_m'])
            if link['to'] == intersection_id:
                return max(0.0, distance)
        return None

    def observe(self, intersection_id: str) -> list[dict]:
        buses = []
        for b in self.network.active_buses():
            distance = self.distance_to_intersection(b, intersection_id)
            if distance is None or distance > self.horizon_m:
                continue
            eta = distance / max(b.speed_mps, 3.0)
            stop_ids=b.metadata.get('stop_ids',[])
            next_stop_id=stop_ids[b.next_stop_index] if b.next_stop_index < len(stop_ids) else None
            link=self.cfg['links'][b.current_link]
            buses.append({
                'id': b.id,
                'route_id': b.route_id,
                'current_link': b.current_link,
                'position_m': b.position_m,
                'direction': f"{link['from']}->{link['to']}",
                'distance_m': distance,
                'speed_mps': b.speed_mps,
                'eta_s': eta,
                'next_stop_index': b.next_stop_index,
                'next_stop_id': next_stop_id,
                'leader_id': b.metadata.get('leader_id'),
                'follower_id': b.metadata.get('follower_id'),
                'headway_s': b.headway_s,
                'following_headway_s': b.metadata.get('following_headway_s'),
                'headway_trend': b.headway_trend_s_per_s,
                'status': b.status.value,
            })
        return sorted(buses, key=lambda x: x['eta_s'])
