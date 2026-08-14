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

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("live-simulation")

RUNNING = True


def _stop(_signum, _frame):
    global RUNNING
    RUNNING = False


signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)


def emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def read_request() -> dict:
    raw = sys.stdin.readline()
    if not raw.strip():
        raise ValueError("No se recibió configuración para la simulación")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("La configuración debe ser un objeto JSON")
    return payload


def scenario_path(name: str) -> Path:
    if not SAFE_NAME.fullmatch(name):
        raise ValueError("Nombre de escenario inválido")
    path = (SCENARIO_ROOT / name).resolve()
    if path.parent != SCENARIO_ROOT.resolve() or not path.is_file():
        raise FileNotFoundError(f"Escenario no encontrado: {name}")
    return path


def checkpoint_dir(run_id: str) -> Path:
    if not SAFE_NAME.fullmatch(run_id):
        raise ValueError("checkpointRunId inválido")
    path = (OUTPUT_ROOT / run_id).resolve()
    if path.parent != OUTPUT_ROOT.resolve() or not path.is_dir():
        raise FileNotFoundError(f"Checkpoint no encontrado: {run_id}")
    return path


def main() -> int:
    try:
        params = read_request()
        scenario_name = str(params.get("scenario", "example_network.yaml"))
        run_id = str(params.get("checkpointRunId", ""))
        if not run_id:
            raise ValueError("checkpointRunId es obligatorio")
        cycle_seconds = float(params.get("cycleSeconds", 600.0))
        real_time_factor = float(params.get("realTimeFactor", 1.0))
        if cycle_seconds < 30 or cycle_seconds > 86400:
            raise ValueError("cycleSeconds debe estar entre 30 y 86400")
        if real_time_factor < 0.25 or real_time_factor > 8:
            raise ValueError("realTimeFactor debe estar entre 0.25 y 8")

        cfg = load_config(scenario_path(scenario_name))
        logic = ClingoTopologyEngine(extra_program=params.get("clingoProgram")).solve(cfg)
        env = MultiAgentTrafficEnv(cfg, logic, episode_seconds=cycle_seconds)
        observations = env.reset()
        group = AgentGroup(env, logic, cfg, seed=int(cfg["simulation"].get("seed", 42)) + 1000)
        if not group.load(checkpoint_dir(run_id)):
            raise FileNotFoundError("No están todos los checkpoints DQN del run seleccionado")

        frame_sequence = 0
        decision_sequence = 0
        cycle = 1
        metric_collector = MetricsCollector(cfg)
        next_frame_deadline = time.perf_counter()

        emit({
            "type": "cycle",
            "cycle": cycle,
            "simulationDtS": env.dt_s,
            "decisionIntervalS": env.decision_interval_s,
            "realTimeFactor": real_time_factor,
            "snapshot": build_network_snapshot(cfg, env),
        })

        while RUNNING:
            masks = env.action_masks()
            actions = group.select_actions(observations, masks, training=False)
            decision_sequence += 1
            emit({
                "type": "decision",
                "sequence": decision_sequence,
                "cycle": cycle,
                "timeS": env.sim_time_s,
                "actions": actions,
                "masks": masks,
                "snapshot": build_network_snapshot(cfg, env),
            })

            def on_substep(current_env):
                nonlocal frame_sequence, next_frame_deadline
                if not RUNNING:
                    return False
                frame_sequence += 1
                snapshot = build_network_snapshot(cfg, current_env)
                emit({
                    "type": "frame",
                    "frameSequence": frame_sequence,
                    "decisionSequence": decision_sequence,
                    "cycle": cycle,
                    "simulationDtS": current_env.dt_s,
                    "decisionIntervalS": current_env.decision_interval_s,
                    "realTimeFactor": real_time_factor,
                    "snapshot": snapshot,
                })
                next_frame_deadline += current_env.dt_s / real_time_factor
                delay = next_frame_deadline - time.perf_counter()
                if delay > 0:
                    time.sleep(delay)
                else:
                    next_frame_deadline = time.perf_counter()
                return RUNNING

            observations, rewards, done, info = env.step(actions, on_substep=on_substep)
            if not RUNNING:
                break
            emit({
                "type": "decision_result",
                "sequence": decision_sequence,
                "cycle": cycle,
                "timeS": env.sim_time_s,
                "actions": actions,
                "rewards": rewards,
                "rewardBreakdown": info.get("rewardBreakdown", {}),
                "metrics": metric_collector.summarize(env),
                "snapshot": build_network_snapshot(cfg, env),
            })

            if done:
                emit({
                    "type": "cycle_complete",
                    "cycle": cycle,
                    "metrics": metric_collector.summarize(env),
                    "snapshot": build_network_snapshot(cfg, env),
                })
                cycle += 1
                observations = env.reset(seed=int(cfg["simulation"].get("seed", 42)) + cycle)
                next_frame_deadline = time.perf_counter()
                emit({
                    "type": "cycle",
                    "cycle": cycle,
                    "simulationDtS": env.dt_s,
                    "decisionIntervalS": env.decision_interval_s,
                    "realTimeFactor": real_time_factor,
                    "snapshot": build_network_snapshot(cfg, env),
                })

        emit({"type": "stopped", "cycle": cycle, "frameSequence": frame_sequence, "decisionSequence": decision_sequence})
        return 0
    except Exception as error:
        logger.error("live simulation failed: %s", error)
        logger.debug("%s", traceback.format_exc())
        emit({"type": "error", "error": {"code": type(error).__name__.upper(), "message": str(error)}})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
