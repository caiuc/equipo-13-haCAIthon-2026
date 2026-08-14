from __future__ import annotations

from pathlib import Path
import random
import numpy as np
import torch
from torch import nn

from ia.modelos.replay_buffer import ReplayBuffer


class QNetwork(nn.Module):
    def __init__(self, state_dim: int, action_dim: int, hidden: list[int]):
        super().__init__()
        layers: list[nn.Module] = []
        prev = state_dim
        for units in hidden:
            layers += [nn.Linear(prev, units), nn.ReLU()]
            prev = units
        layers.append(nn.Linear(prev, action_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


class DQNAgent:
    def __init__(self, state_dim: int, action_dim: int, cfg: dict, seed: int = 42, device: str | None = None):
        self.state_dim = state_dim; self.action_dim = action_dim
        self.cfg = cfg
        self.device = torch.device(device or ('cuda' if torch.cuda.is_available() else 'cpu'))
        hidden = list(cfg.get('hidden_units',[128,128]))
        self.online = QNetwork(state_dim, action_dim, hidden).to(self.device)
        self.target = QNetwork(state_dim, action_dim, hidden).to(self.device)
        self.target.load_state_dict(self.online.state_dict()); self.target.eval()
        self.optimizer = torch.optim.Adam(self.online.parameters(), lr=float(cfg['learning_rate']))
        self.loss_fn = nn.SmoothL1Loss()
        self.buffer = ReplayBuffer(int(cfg['replay_capacity']), seed)
        self.rng = random.Random(seed)
        self.steps = 0

    @property
    def epsilon(self) -> float:
        start,end,decay = float(self.cfg['epsilon_start']),float(self.cfg['epsilon_end']),max(1,int(self.cfg['epsilon_decay_steps']))
        frac = min(1.0, self.steps/decay)
        return start + frac*(end-start)

    def select_action(self, state: np.ndarray, mask: list[bool] | np.ndarray, training: bool = True) -> int:
        valid = np.flatnonzero(np.asarray(mask,dtype=bool))
        if len(valid)==0:
            raise RuntimeError('Action mask sin acciones válidas')
        if training and self.rng.random() < self.epsilon:
            return int(self.rng.choice(valid.tolist()))
        with torch.no_grad():
            s = torch.as_tensor(state,dtype=torch.float32,device=self.device).unsqueeze(0)
            q = self.online(s).squeeze(0)
            invalid = torch.as_tensor(~np.asarray(mask,dtype=bool),device=self.device)
            q = q.masked_fill(invalid, -torch.inf)
            return int(torch.argmax(q).item())

    def remember(self, state, action, reward, next_state, done, next_mask):
        self.buffer.push(state.copy(), int(action), float(reward), next_state.copy(), bool(done), np.asarray(next_mask,dtype=bool).copy())
        self.steps += 1

    def learn(self) -> float | None:
        batch_size = int(self.cfg['batch_size'])
        if len(self.buffer) < batch_size:
            return None
        batch = self.buffer.sample(batch_size)
        states = torch.as_tensor(np.stack([x.state for x in batch]),dtype=torch.float32,device=self.device)
        actions = torch.as_tensor([x.action for x in batch],dtype=torch.long,device=self.device).unsqueeze(1)
        rewards = torch.as_tensor([x.reward for x in batch],dtype=torch.float32,device=self.device)
        next_states = torch.as_tensor(np.stack([x.next_state for x in batch]),dtype=torch.float32,device=self.device)
        dones = torch.as_tensor([x.done for x in batch],dtype=torch.float32,device=self.device)
        masks = torch.as_tensor(np.stack([x.next_mask for x in batch]),dtype=torch.bool,device=self.device)

        q = self.online(states).gather(1, actions).squeeze(1)
        with torch.no_grad():
            nq = self.target(next_states).masked_fill(~masks, -torch.inf)
            # Siempre debe existir una acción válida; fallback defensivo.
            max_nq = nq.max(dim=1).values
            max_nq = torch.where(torch.isfinite(max_nq), max_nq, torch.zeros_like(max_nq))
            target = rewards + float(self.cfg['gamma']) * (1.0-dones) * max_nq
        loss = self.loss_fn(q,target)
        self.optimizer.zero_grad(); loss.backward()
        nn.utils.clip_grad_norm_(self.online.parameters(), float(self.cfg.get('gradient_clip',10.0)))
        self.optimizer.step()
        if self.steps % int(self.cfg['target_update_steps']) == 0:
            self.target.load_state_dict(self.online.state_dict())
        return float(loss.item())

    def save(self, path: str | Path) -> None:
        path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
        torch.save({'state_dim':self.state_dim,'action_dim':self.action_dim,'model':self.online.state_dict(),'steps':self.steps},path)

    def load(self, path: str | Path) -> None:
        payload=torch.load(path,map_location=self.device,weights_only=False)
        if payload['state_dim']!=self.state_dim or payload['action_dim']!=self.action_dim:
            raise ValueError('Checkpoint incompatible con topología/estado actual')
        self.online.load_state_dict(payload['model']); self.target.load_state_dict(payload['model']); self.steps=int(payload.get('steps',0))
