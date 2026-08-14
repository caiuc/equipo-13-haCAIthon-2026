#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

BRIDGE = Path(__file__).with_name("bridge.py")


def main() -> int:
    parser = argparse.ArgumentParser(description="CLI de desarrollo para el núcleo Python")
    parser.add_argument("operation", choices=["scenarios", "topology", "simulate", "train", "evaluate"])
    parser.add_argument("--scenario", default="example_network.yaml")
    parser.add_argument("--seconds", type=float)
    parser.add_argument("--episodes", type=int)
    parser.add_argument("--run-id")
    parser.add_argument("--checkpoint-run-id")
    args = parser.parse_args()

    parameters = {"scenario": args.scenario}
    if args.seconds is not None:
        parameters["seconds"] = args.seconds
    if args.episodes is not None:
        parameters["episodes"] = args.episodes
    if args.run_id:
        parameters["runId"] = args.run_id
    if args.checkpoint_run_id:
        parameters["checkpointRunId"] = args.checkpoint_run_id

    completed = subprocess.run(
        [sys.executable, str(BRIDGE), args.operation],
        input=json.dumps({"parameters": parameters}),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.stderr:
        sys.stderr.write(completed.stderr)
    if completed.stdout:
        try:
            print(json.dumps(json.loads(completed.stdout), indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print(completed.stdout)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
