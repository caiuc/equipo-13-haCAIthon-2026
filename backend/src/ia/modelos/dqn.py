"""DQN derivado del agente funcional entregado en Empresa.zip."""
from __future__ import annotations

import random
from collections import deque, namedtuple
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

Transition = namedtuple("Transition", ["state", "action", "reward", "next_state", "done", "next_mask"])


class QNetwork(nn.Module):
    def __init__(self, state_size: int, action_size: int, hidden_units=(128, 128)):
        super().__init__()
        h1, h2 = list(hidden_units)[:2]
        self.net = nn.Sequential(
            nn.Linear(state_size, h1), nn.ReLU(),
            nn.Linear(h1, h2), nn.ReLU(),
            nn.Linear(h2, action_size),
        )

    def forward(self, value):
        return self.net(value)


class ReplayBuffer:
    def __init__(self, capacity: int):
        self.buffer = deque(maxlen=int(capacity))

    def push(self, *args):
        self.buffer.append(Transition(*args))

    def sample(self, batch_size: int):
        items = random.sample(self.buffer, batch_size)
        return Transition(*zip(*items))

    def __len__(self):
        return len(self.buffer)


class DQNAgent:
    def __init__(self, state_size: int, action_size: int, cfg: dict, seed: int = 42, device: str | None = None):
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.state_size = int(state_size)
        self.action_size = int(action_size)
        self.gamma = float(cfg.get("gamma", 0.97))
        self.batch_size = int(cfg.get("batch_size", 64))
        self.target_update_every = int(cfg.get("target_update_steps", 500))
        hidden = tuple(cfg.get("hidden_units", [128, 128]))
        self.online = QNetwork(self.state_size, self.action_size, hidden).to(self.device)
        self.target = QNetwork(self.state_size, self.action_size, hidden).to(self.device)
        self.target.load_state_dict(self.online.state_dict())
        self.target.eval()
        self.optimizer = optim.Adam(self.online.parameters(), lr=float(cfg.get("learning_rate", 1e-3)))
        self.buffer = ReplayBuffer(int(cfg.get("replay_capacity", 50000)))
        self.loss_fn = nn.SmoothL1Loss()
        self.epsilon_start = float(cfg.get("epsilon_start", 1.0))
        self.epsilon_end = float(cfg.get("epsilon_end", 0.05))
        self.epsilon_decay_steps = int(cfg.get("epsilon_decay_steps", 20000))
        self.gradient_clip = float(cfg.get("gradient_clip", 10.0))
        self.steps_done = 0

    def current_epsilon(self) -> float:
        fraction = min(self.steps_done / max(self.epsilon_decay_steps, 1), 1.0)
        return self.epsilon_start + fraction * (self.epsilon_end - self.epsilon_start)

    def select_action(self, state, legal_mask, training: bool = True) -> int:
        legal = [index for index, allowed in enumerate(legal_mask) if allowed]
        if not legal:
            raise RuntimeError("Action mask sin acciones legales")
        if training:
            self.steps_done += 1
            if random.random() < self.current_epsilon():
                return random.choice(legal)
        with torch.no_grad():
            tensor = torch.tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0)
            values = self.online(tensor).squeeze(0).clone()
            for index in range(self.action_size):
                if index not in legal:
                    values[index] = -float("inf")
            return int(torch.argmax(values).item())

    def remember(self, state, action, reward, next_state, done, next_mask) -> None:
        self.buffer.push(
            np.asarray(state, dtype=np.float32), int(action), float(reward),
            np.asarray(next_state, dtype=np.float32), bool(done), np.asarray(next_mask, dtype=bool),
        )

    def train_step(self) -> float:
        if len(self.buffer) < self.batch_size:
            return 0.0
        batch = self.buffer.sample(self.batch_size)
        states = torch.tensor(np.asarray(batch.state), dtype=torch.float32, device=self.device)
        actions = torch.tensor(batch.action, dtype=torch.long, device=self.device).unsqueeze(1)
        rewards = torch.tensor(batch.reward, dtype=torch.float32, device=self.device).unsqueeze(1)
        next_states = torch.tensor(np.asarray(batch.next_state), dtype=torch.float32, device=self.device)
        dones = torch.tensor(batch.done, dtype=torch.float32, device=self.device).unsqueeze(1)
        masks = torch.tensor(np.asarray(batch.next_mask), dtype=torch.bool, device=self.device)

        q_values = self.online(states).gather(1, actions)
        with torch.no_grad():
            next_q = self.target(next_states).masked_fill(~masks, -float("inf"))
            max_next = next_q.max(dim=1, keepdim=True).values
            max_next = torch.nan_to_num(max_next, neginf=0.0)
            target = rewards + self.gamma * max_next * (1.0 - dones)

        loss = self.loss_fn(q_values, target)
        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.online.parameters(), self.gradient_clip)
        self.optimizer.step()
        if self.steps_done % max(self.target_update_every, 1) == 0:
            self.target.load_state_dict(self.online.state_dict())
        return float(loss.item())

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "state_size": self.state_size,
            "action_size": self.action_size,
            "online": self.online.state_dict(),
            "target": self.target.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "steps_done": self.steps_done,
        }, path)

    def load(self, path: str | Path) -> None:
        payload = torch.load(path, map_location=self.device, weights_only=False)
        if int(payload["state_size"]) != self.state_size or int(payload["action_size"]) != self.action_size:
            raise ValueError("Checkpoint incompatible con el escenario actual")
        self.online.load_state_dict(payload["online"])
        self.target.load_state_dict(payload.get("target", payload["online"]))
        if "optimizer" in payload:
            self.optimizer.load_state_dict(payload["optimizer"])
        self.steps_done = int(payload.get("steps_done", 0))
