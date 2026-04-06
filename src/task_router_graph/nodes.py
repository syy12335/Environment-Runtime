from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .agents import route_task, run_normal_task
from .agents.common import build_rounds_context
from .schema import ControllerAction, Environment, RoundRecord, Task


def _latest_run_dir(run_root: Path) -> Path | None:
    if not run_root.exists():
        return None
    candidates = [p for p in run_root.iterdir() if p.is_dir() and p.name.startswith("run_")]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _resolve_observe_path(*, workspace_root: Path, run_root: Path, raw_path: str) -> Path:
    normalized = raw_path.strip()
    if normalized.startswith("var/runs/latest"):
        latest = _latest_run_dir(run_root)
        if latest is None:
            raise FileNotFoundError("latest run directory not found")
        suffix = normalized[len("var/runs/latest") :].lstrip("/\\")
        return latest / suffix

    path_obj = Path(normalized)
    if path_obj.is_absolute():
        return path_obj
    return (workspace_root / normalized).resolve()


def _tool_read(*, workspace_root: Path, run_root: Path, path: str = "") -> str:
    if not path:
        return "[read] missing path"
    try:
        target = _resolve_observe_path(workspace_root=workspace_root, run_root=run_root, raw_path=path)
    except Exception as exc:
        return f"[read] invalid path: {exc}"

    if not target.exists():
        return f"[read] path not found: {target}"

    if target.is_dir():
        entries = sorted(item.name for item in target.iterdir())
        return "\n".join(entries[:200])

    text = target.read_text(encoding="utf-8", errors="replace")
    return text[:8000]


def _tool_ls(*, workspace_root: Path, run_root: Path, path: str = "") -> str:
    raw = path or "."
    try:
        target = _resolve_observe_path(workspace_root=workspace_root, run_root=run_root, raw_path=raw)
    except Exception as exc:
        return f"[ls] invalid path: {exc}"

    if not target.exists():
        return f"[ls] path not found: {target}"
    if not target.is_dir():
        return f"[ls] not a directory: {target}"

    entries = sorted(item.name for item in target.iterdir())
    return "\n".join(entries[:200])


def _build_observe_tools(*, workspace_root: Path, run_root: Path) -> dict[str, Callable[..., Any]]:
    return {
        "read": lambda **kwargs: _tool_read(workspace_root=workspace_root, run_root=run_root, **kwargs),
        "ls": lambda **kwargs: _tool_ls(workspace_root=workspace_root, run_root=run_root, **kwargs),
    }


def _build_controller_trace(route_result: dict[str, Any]) -> list[ControllerAction]:
    trace: list[ControllerAction] = []

    for item in route_result.get("controller_trace", []):
        trace.append(
            ControllerAction(
                action_kind="observe",
                reason=str(item.get("reason", "observe")),
                tool=str(item.get("tool", "")).strip() or None,
                args=item.get("args", {}) if isinstance(item.get("args"), dict) else {},
                observation=str(item.get("observation", "")).strip() or None,
            )
        )

    trace.append(
        ControllerAction(
            action_kind="generate_task",
            reason=str(route_result.get("reason", "generate task")),
            task_type=str(route_result.get("task_type", "")).strip() or None,
            task_content=str(route_result.get("task_content", "")).strip() or None,
        )
    )

    return trace


def route_node(
    *,
    llm: Any,
    controller_system: str,
    controller_skills_index: str,
    environment: Environment,
    user_input: str,
    workspace_root: Path,
    run_root: Path,
    max_steps: int,
) -> tuple[Task, list[ControllerAction]]:
    rounds_context = build_rounds_context(environment.rounds)
    observe_tools = _build_observe_tools(workspace_root=workspace_root, run_root=run_root)

    route_result = route_task(
        llm=llm,
        system_prompt=controller_system,
        user_input=user_input,
        rounds=rounds_context,
        skills_index=controller_skills_index,
        observe_tools=observe_tools,
        max_steps=max_steps,
    )

    task = Task(type=route_result["task_type"], content=route_result["task_content"])
    controller_trace = _build_controller_trace(route_result)
    return task, controller_trace


def execute_node(
    *,
    llm: Any,
    normal_system: str,
    normal_skills_index: str,
    environment: Environment,
    task: Task,
) -> tuple[Task, str]:
    if task.type == "normal":
        rounds_context = build_rounds_context(environment.rounds)
        result = run_normal_task(
            llm=llm,
            system_prompt=normal_system,
            task_content=task.content,
            rounds=rounds_context,
            normal_skills_index=normal_skills_index,
        )
        reply = result.get("reply", "").strip()
        status = result.get("task_status", "").strip()
        task_result = result.get("task_result", "").strip()

        if status not in {"done", "failed"}:
            status = "failed"
        if not task_result:
            task_result = "normal task returned empty task_result"
        if not reply:
            reply = "本轮 normal 任务执行完成，但回复内容为空。"

        task.status = status
        task.result = task_result
        return task, reply

    if task.type == "functest":
        task.status = "done"
        task.result = "functest completed (mocked)"
        return task, "[functest] completed with mocked assertions"

    if task.type == "accutest":
        task.status = "done"
        task.result = "accutest completed (placeholder metrics)"
        return task, "[accutest] placeholder score: 0.83"

    if task.type == "perftest":
        task.status = "done"
        task.result = "perftest completed (placeholder metrics)"
        return task, "[perftest] placeholder p95: 210ms, qps: 48"

    task.status = "failed"
    task.result = "unsupported task type"
    return task, "unsupported task type"


def update_node(
    environment: Environment,
    user_input: str,
    controller_trace: list[ControllerAction],
    task: Task,
    reply: str,
) -> Environment:
    environment.rounds.append(
        RoundRecord(
            round=len(environment.rounds) + 1,
            user_input=user_input,
            controller_trace=controller_trace,
            task=task,
            reply=reply,
        )
    )
    return environment
