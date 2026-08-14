#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
from pathlib import Path
import re
import signal
import sys
import time
import traceback

SRC_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = SRC_ROOT.parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from config.scenario_loader import load_config
from ia.clingo.asp_engine import ClingoTopologyEngine
from ia.modelos.agent_group import AgentGroup
from simulacion.metricas.metrics_collector import MetricsCollector
from simulacion.telemetria.snapshot import build_network_snapshot
from simulacion.trafico.multi_agent_environment import MultiAgentTrafficEnv

SCENARIO_ROOT = SRC_ROOT / "config" / "scenarios"
OUTPUT_ROOT = BACKEND_ROOT / "outputs" / "model_runs"
SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
RUNNING = True

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
logger = logging.getLogger("live-simulation")


def _stop(*_):
    global RUNNING
    RUNNING = False


def _safe_path(root: Path, name: str, must_exist: bool = True) -> Path:
    if not SAFE_NAME.fullmatch(name):
        raise ValueError("Nombre inseguro")
    path = (root / name).resolve()
    if path.parent != root.resolve():
        raise ValueError("Ruta insegura")
    if must_exist and not path.exists():
        raise FileNotFoundError(name)
    return path


def emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _pace_realtime(wall_started: float, simulated_elapsed_s: float, realtime_factor: float) -> None:
    """Sincroniza el reloj microscópico con el reloj real.

    A 1x, 0,2 s simulados se muestran cada ~0,2 s reales. El tiempo usado en
    cálculo/serialización se descuenta del sleep para evitar deriva acumulada.
    """
    expected_wall_elapsed = simulated_elapsed_s / realtime_factor
    remaining = expected_wall_elapsed - (time.monotonic() - wall_started)
    if remaining > 0:
        time.sleep(remaining)


def main() -> int:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    try:
        raw = sys.stdin.readline()
        parameters = json.loads(raw or "{}")
        scenario_name = str(parameters.get("scenario", "example_network.yaml"))
        run_id = str(parameters.get("checkpointRunId", ""))
        if not run_id:
            raise ValueError("checkpointRunId es obligatorio")

        scenario_path = _safe_path(SCENARIO_ROOT, scenario_name)
        checkpoint_path = _safe_path(OUTPUT_ROOT, run_id)
        cfg = load_config(scenario_path)
        logic = ClingoTopologyEngine(extra_program=parameters.get("clingoProgram")).solve(cfg)

        cycle_seconds = float(parameters.get("cycleSeconds", 1800.0))
        realtime_factor = max(0.25, min(4.0, float(parameters.get("realTimeFactor", 1.0))))
        base_seed = int(cfg["simulation"].get("seed", 42))
        cycle = 0
        frame_sequence = 0
        decision_sequence = 0

        while RUNNING:
            cfg["simulation"]["seed"] = base_seed + cycle * 97
            env = MultiAgentTrafficEnv(cfg, logic, cycle_seconds)
            obs = env.reset()
            group = AgentGroup(env, logic, cfg, seed=100 + cycle)
            if not group.load(checkpoint_path):
                raise FileNotFoundError(f"Checkpoint incompleto: {run_id}")

            collector = MetricsCollector(cfg)
            cycle_started_wall = time.monotonic()
            decision_context = None
            decision_end_s = 0.0
            current_actions = {iid: 0 for iid in env.controllers}
            current_rewards = {iid: 0.0 for iid in env.controllers}
            next_metrics_at_s = 0.0

            emit({
                "type": "cycle",
                "cycle": cycle + 1,
                "runId": run_id,
                "realTimeFactor": realtime_factor,
                "simulationDtS": env.network.dt,
                "decisionIntervalS": env.decision_interval,
                "snapshot": build_network_snapshot(cfg, env),
            })

            while RUNNING and env.network.time_s < cycle_seconds:
                # El DQN decide solo al inicio de cada intervalo de decisión.
                # Entre decisiones el simulador avanza a dt=0,2 s y cada micro-paso
                # se transmite al navegador.
                if decision_context is None:
                    current_actions = group.select_actions(obs, env.action_masks(), training=False)
                    decision_context = env.begin_decision(current_actions)
                    decision_end_s = min(cycle_seconds, env.network.time_s + env.decision_interval)
                    decision_sequence += 1
                    emit({
                        "type": "decision",
                        "sequence": decision_sequence,
                        "cycle": cycle + 1,
                        "timeS": env.network.time_s,
                        "actions": current_actions,
                        "actionMasks": env.action_masks(),
                        "snapshot": build_network_snapshot(cfg, env),
                    })

                env.advance_micro_step()

                # Cierra recompensa/observación al completar los 5 s del DQN.
                if env.network.time_s + 1e-9 >= decision_end_s:
                    obs, current_rewards, _, _ = env.finish_decision(decision_context)
                    collector.sample(env, current_rewards)
                    decision_context = None

                # Pacing 1:1: el frame de t=0,2 aparece a los ~0,2 s reales.
                _pace_realtime(cycle_started_wall, env.network.time_s, realtime_factor)
                frame_sequence += 1
                frame = {
                    "type": "frame",
                    "frameSequence": frame_sequence,
                    "decisionSequence": decision_sequence,
                    "cycle": cycle + 1,
                    "controller": "dqn-realtime",
                    "realTimeFactor": realtime_factor,
                    "simulationDtS": env.network.dt,
                    "decisionIntervalS": env.decision_interval,
                    "actions": current_actions,
                    "rewards": current_rewards,
                    "snapshot": build_network_snapshot(cfg, env),
                }
                if env.network.time_s + 1e-9 >= next_metrics_at_s:
                    frame["metrics"] = collector.summarize(env)
                    next_metrics_at_s = env.network.time_s + 1.0
                emit(frame)

            if decision_context is not None:
                obs, current_rewards, _, _ = env.finish_decision(decision_context)
                collector.sample(env, current_rewards)

            cycle += 1

        emit({"type": "stopped", "frameSequence": frame_sequence, "decisionSequence": decision_sequence, "cycles": cycle})
        return 0
    except Exception as error:
        logger.error("%s", traceback.format_exc())
        emit({"type": "error", "error": {"code": type(error).__name__.upper(), "message": str(error)}})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
