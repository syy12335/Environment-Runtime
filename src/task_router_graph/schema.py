from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Action:
    kind: str
    detail: str
    args: dict[str, Any] = field(default_factory=dict)


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
    action: Action
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
