from __future__ import annotations

from pathlib import Path

import yaml

from .nodes import execute_node, observe_node, route_node, update_node
from .schema import Environment, Output, to_dict
from .utils import read_json, timestamp_tag, write_json


class TaskRouterGraph:
    def __init__(self, config_path: str | Path = "configs/graph.yaml") -> None:
        self.root = Path(__file__).resolve().parents[2]
        self.config_path = (self.root / config_path).resolve() if not Path(config_path).is_absolute() else Path(config_path)
        self.config = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))

    def run(self, *, case_id: str, user_input: str, environment: Environment | None = None) -> dict:
        env = environment or Environment()

        action = observe_node(env, user_input)
        task = route_node(user_input)
        task, reply = execute_node(task)
        env = update_node(env, user_input, action, task, reply)

        run_dir = self._prepare_run_dir()
        output = Output(
            case_id=case_id,
            task_type=task.type,
            task_status=task.status,
            task_result=task.result,
            reply=reply,
            run_dir=str(run_dir.relative_to(self.root)),
        )

        write_json(run_dir / "input.json", {"case_id": case_id, "user_input": user_input})
        write_json(run_dir / "rounds.json", [to_dict(round_item) for round_item in env.rounds])
        write_json(run_dir / "tasks.json", [to_dict(round_item.task) for round_item in env.rounds])
        write_json(run_dir / "output.json", to_dict(output))

        return {
            "environment": to_dict(env),
            "output": to_dict(output),
        }

    def run_case(self, case_path: str | Path) -> dict:
        case = read_json(Path(case_path))
        return self.run(case_id=case["case_id"], user_input=case["user_input"])

    def _prepare_run_dir(self) -> Path:
        run_root = (self.root / self.config["paths"]["run_root"]).resolve()
        run_dir = run_root / f"run_{timestamp_tag()}"
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir
