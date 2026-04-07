from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Task:
    # 运行时任务载体：类型、内容和执行结果。
    type: str
    content: str
    status: str = "pending"
    result: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Task":
        # 从字典恢复任务对象，并做基础字段兜底。
        return cls(
            type=str(payload.get("type", "")).strip(),
            content=str(payload.get("content", "")).strip(),
            status=str(payload.get("status", "pending")).strip() or "pending",
            result=str(payload.get("result", "")).strip(),
        )

    def to_dict(self) -> dict[str, str]:
        # 任务对象的稳定序列化出口。
        return {
            "type": self.type,
            "content": self.content,
            "status": self.status,
            "result": self.result,
        }
