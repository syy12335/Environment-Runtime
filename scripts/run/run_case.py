from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from run_common import flush_tracers, log, with_heartbeat


def main() -> None:
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--case", default="data/cases/case_01.json", help="Path to one case JSON")
        parser.add_argument("--config", default="configs/graph.yaml", help="Path to graph config")
        parser.add_argument("--heartbeat-sec", type=float, default=10.0, help="Heartbeat interval seconds (0 to disable)")
        args = parser.parse_args()

        case_path = Path(args.case)
        if not case_path.is_absolute():
            case_path = PROJECT_ROOT / case_path
        case_path = case_path.resolve()
        if not case_path.exists():
            raise FileNotFoundError(f"Case file not found: {case_path}")

        try:
            from task_router_graph import TaskRouterGraph
        except Exception as exc:
            raise RuntimeError(
                "Failed to import TaskRouterGraph. Please install dependencies (pip install -r requirements.txt)."
            ) from exc

        log(f"Loading graph with config: {args.config}")
        graph, _ = with_heartbeat(
            "Graph initialization",
            args.heartbeat_sec,
            lambda: TaskRouterGraph(config_path=args.config),
        )

        log(f"Running case: {case_path.name}")
        result, _ = with_heartbeat(
            f"Case {case_path.stem}",
            args.heartbeat_sec,
            lambda: graph.run_case(case_path),
        )

        print(json.dumps(result["output"], ensure_ascii=False, indent=2), flush=True)
    finally:
        flush_tracers()


if __name__ == "__main__":
    main()
