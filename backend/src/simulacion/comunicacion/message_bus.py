from __future__ import annotations

from collections import defaultdict, deque
from common.domain_models import NeighborMessage


class MessageBus:
    def __init__(self, cfg: dict):
        self.neighbors = {iid: list(inter.get('neighbors', [])) for iid,inter in cfg['intersections'].items()}
        self.inboxes = defaultdict(lambda: deque(maxlen=32))

    def broadcast(self, message: NeighborMessage) -> None:
        for neighbor in self.neighbors.get(message.sender_id, []):
            self.inboxes[neighbor].append(message)

    def receive(self, intersection_id: str) -> list[NeighborMessage]:
        return list(self.inboxes[intersection_id])
