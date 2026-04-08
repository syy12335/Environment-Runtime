from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from task_router_graph import TaskRouterGraph


def _is_valid_case_file(path: Path) -> bool:
    if path.name == "manifest.json":
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return isinstance(payload, dict) and "case_id" in payload and "user_input" in payload


def main() -> None:
    graph = TaskRouterGraph(config_path="configs/graph.yaml")
    cases_dir = PROJECT_ROOT / "data" / "cases"
    output_dir = PROJECT_ROOT / "data" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    all_json_files = sorted(cases_dir.glob("*.json"))
    case_files = [path for path in all_json_files if _is_valid_case_file(path)]

    if not case_files:
        raise RuntimeError(f"No valid case files found in: {cases_dir}")

    skipped = [path.name for path in all_json_files if path not in case_files]
    for file_name in skipped:
        print(f"Skipped non-case file: {file_name}")

    # 批量执行所有合法 case，并保存每个 case 的 output 摘要。
    for case_file in case_files:
        result = graph.run_case(case_file)
        output_path = output_dir / f"{case_file.stem}_output.json"
        output_path.write_text(json.dumps(result["output"], ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Processed {case_file.name} -> {output_path.name}")


if __name__ == "__main__":
    main()
