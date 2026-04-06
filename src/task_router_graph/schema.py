from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ControllerAction:
    action_kind: str
    reason: str
    tool: str | None = None
    args: dict[str, Any] = field(default_factory=dict)
    task_type: str | None = None
    task_content: str | None = None
    observation: str | None = None


@dataclass
class Task:
    type: str
    content: str
    status: str = "pending"
    result: str = ""


@dataclass
class RoundRecord:
    round: int
    user_input: str
    controller_trace: list[ControllerAction]
    task: Task
    reply: str


@dataclass
class Environment:
    rounds: list[RoundRecord] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Output:
    case_id: str
    task_type: str
    task_status: str
    task_result: str
    reply: str
    run_dir: str


def to_dict(data: Any) -> Any:
    return asdict(data)
