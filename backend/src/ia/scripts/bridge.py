#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import re
import sys
import time
import traceback

SRC_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = SRC_ROOT.parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from config.scenario_loader import load_config
from ia.clingo.asp_engine import ClingoTopologyEngine
from ia.entrenamiento.evaluate import evaluate
from ia.entrenamiento.train import train
from simulacion.metricas.metrics_collector import MetricsCollector
from simulacion.telemetria.snapshot import build_network_snapshot
from simulacion.telemetria.topology_serializer import serialize_topology
from simulacion.trafico.simulation_runner import run_baseline_simulation

SCENARIO_ROOT = SRC_ROOT / "config" / "scenarios"
OUTPUT_ROOT = BACKEND_ROOT / "outputs"
SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
ALLOWED_OPERATIONS = {"scenarios", "topology", "simulate", "train", "evaluate"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("python-bridge")


def _read_request() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {"parameters": {}}
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("La entrada JSON debe ser un objeto")
    parameters = payload.get("parameters", {})
    if not isinstance(parameters, dict):
        raise ValueError("parameters debe ser un objeto JSON")
    return payload


def _scenario_path(parameters: dict) -> Path:
    name = str(parameters.get("scenario", "example_network.yaml"))
    if not SAFE_NAME.fullmatch(name):
        raise ValueError("Nombre de escenario inválido")
    path = (SCENARIO_ROOT / name).resolve()
    if path.parent != SCENARIO_ROOT.resolve() or not path.is_file():
        raise FileNotFoundError(f"Escenario no encontrado: {name}")
    return path


def _positive_number(parameters: dict, key: str, default: float, minimum: float, maximum: float) -> float:
    value = float(parameters.get(key, default))
    if value < minimum or value > maximum:
        raise ValueError(f"{key} debe estar entre {minimum} y {maximum}")
    return value


def _positive_int(parameters: dict, key: str, default: int, minimum: int, maximum: int) -> int:
    value = int(parameters.get(key, default))
    if value < minimum or value > maximum:
        raise ValueError(f"{key} debe estar entre {minimum} y {maximum}")
    return value


def _safe_run_directory(parameters: dict) -> Path:
    run_id = str(parameters.get("runId") or f"run-{int(time.time())}")
    if not SAFE_NAME.fullmatch(run_id):
        raise ValueError("runId inválido")
    directory = (OUTPUT_ROOT / "model_runs" / run_id).resolve()
    model_root = (OUTPUT_ROOT / "model_runs").resolve()
    if directory.parent != model_root:
        raise ValueError("Ruta de salida inválida")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _safe_checkpoint_directory(parameters: dict) -> Path | None:
    run_id = parameters.get("checkpointRunId")
    if not run_id:
        return None
    run_id = str(run_id)
    if not SAFE_NAME.fullmatch(run_id):
        raise ValueError("checkpointRunId inválido")
    directory = (OUTPUT_ROOT / "model_runs" / run_id).resolve()
    model_root = (OUTPUT_ROOT / "model_runs").resolve()
    if directory.parent != model_root or not directory.is_dir():
        raise FileNotFoundError(f"Checkpoint no encontrado: {run_id}")
    return directory


def _load_runtime(parameters: dict):
    scenario = _scenario_path(parameters)
    cfg = load_config(scenario)
    logic = ClingoTopologyEngine().solve(cfg)
    return scenario, cfg, logic


def operation_scenarios(_: dict) -> dict:
    scenarios = sorted(path.name for path in SCENARIO_ROOT.glob("*.yaml") if path.is_file())
    return {"scenarios": scenarios}


def operation_topology(parameters: dict) -> dict:
    scenario, cfg, logic = _load_runtime(parameters)
    result = serialize_topology(logic)
    result["scenario"] = scenario.name
    result["network"] = {
        "nodes": cfg["nodes"],
        "links": cfg["links"],
        "stops": cfg.get("stops", {}),
        "busRoutes": cfg.get("bus_routes", {}),
    }
    return result


def operation_simulate(parameters: dict) -> dict:
    scenario, cfg, logic = _load_runtime(parameters)
    seconds = _positive_number(parameters, "seconds", 900.0, 5.0, 86400.0)
    env, metrics = run_baseline_simulation(cfg, logic, seconds)
    return {
        "scenario": scenario.name,
        "controller": "heuristic-safe-baseline",
        "metrics": metrics,
        "snapshot": build_network_snapshot(cfg, env),
    }


def operation_train(parameters: dict) -> dict:
    scenario, cfg, logic = _load_runtime(parameters)
    episodes = _positive_int(parameters, "episodes", 20, 1, 10000)
    seconds = _positive_number(parameters, "seconds", 900.0, 5.0, 86400.0)
    output_dir = _safe_run_directory(parameters)
    result = train(cfg, logic, episodes, seconds, output_dir)
    metrics = MetricsCollector(cfg).summarize(result["env"])
    return {
        "scenario": scenario.name,
        "runId": output_dir.name,
        "architecture": result["group"].architecture,
        "history": result["history"],
        "metrics": metrics,
        "snapshot": build_network_snapshot(cfg, result["env"]),
    }


def operation_evaluate(parameters: dict) -> dict:
    scenario, cfg, logic = _load_runtime(parameters)
    seconds = _positive_number(parameters, "seconds", 1800.0, 5.0, 86400.0)
    checkpoints = _safe_checkpoint_directory(parameters)
    env, metrics = evaluate(cfg, logic, seconds, checkpoints)
    return {
        "scenario": scenario.name,
        "checkpointRunId": checkpoints.name if checkpoints else None,
        "controller": "dqn" if checkpoints else "heuristic-safe-baseline",
        "metrics": metrics,
        "snapshot": build_network_snapshot(cfg, env),
    }


OPERATIONS = {
    "scenarios": operation_scenarios,
    "topology": operation_topology,
    "simulate": operation_simulate,
    "train": operation_train,
    "evaluate": operation_evaluate,
}


def execute(operation: str, payload: dict) -> dict:
    if operation not in ALLOWED_OPERATIONS:
        raise ValueError(f"Operación no permitida: {operation}")
    started = time.perf_counter()
    parameters = payload.get("parameters", {})
    data = OPERATIONS[operation](parameters)
    return {
        "success": True,
        "data": data,
        "metadata": {
            "operation": operation,
            "simulationId": payload.get("simulationId"),
            "durationMs": round((time.perf_counter() - started) * 1000, 2),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Adaptador JSON NestJS ↔ Python")
    parser.add_argument("operation", choices=sorted(ALLOWED_OPERATIONS))
    args = parser.parse_args()
    try:
        payload = _read_request()
        response = execute(args.operation, payload)
        sys.stdout.write(json.dumps(response, ensure_ascii=False))
        sys.stdout.flush()
        return 0
    except Exception as error:
        logger.error("operation=%s error=%s", args.operation, error)
        logger.debug("%s", traceback.format_exc())
        response = {
            "success": False,
            "error": {
                "code": type(error).__name__.upper(),
                "message": str(error),
            },
        }
        sys.stdout.write(json.dumps(response, ensure_ascii=False))
        sys.stdout.flush()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
