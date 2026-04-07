from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .controller_action import ControllerAction
from .round_record import RoundRecord
from .task import Task


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Environment:
    # 精简原则：Environment 只负责轮次写入、人类可读展示、以及给 AI 的观察视图。
    rounds: list[RoundRecord] = field(default_factory=list)
    updated_at: str = field(default_factory=_now_iso)

    def add_round(
        self,
        *,
        user_input: str,
        controller_trace: list[ControllerAction],
        task: Task,
        reply: str,
    ) -> RoundRecord:
        # 写入轮次时复制对象，避免外部后续修改污染历史。
        trace_copy = [ControllerAction.from_dict(item.to_dict()) for item in controller_trace]
        task_copy = Task.from_dict(task.to_dict())

        record = RoundRecord(
            round=len(self.rounds) + 1,
            user_input=user_input,
            controller_trace=trace_copy,
            task=task_copy,
            reply=reply,
        )
        self.rounds.append(record)
        self.updated_at = _now_iso()
        return record

    def show_environment(self, *, show_trace: bool = False) -> str:
        # 给人看的环境展示。
        lines: list[str] = [
            "=== Environment ===",
            f"updated_at: {self.updated_at}",
            f"round_count: {len(self.rounds)}",
            "------------------------------",
        ]

        for round_item in self.rounds:
            lines.append(f"round#{round_item.round}")
            lines.append(f"user_input: {round_item.user_input}")
            lines.append(
                "task: "
                f"type={round_item.task.type}, "
                f"status={round_item.task.status}, "
                f"result={round_item.task.result}"
            )
            lines.append(f"reply: {round_item.reply}")

            if show_trace:
                lines.append(f"controller_trace_count: {len(round_item.controller_trace)}")
                for action in round_item.controller_trace:
                    lines.append(
                        "- "
                        f"{action.action_kind} | "
                        f"tool={action.tool} | "
                        f"reason={action.reason}"
                    )

            lines.append("------------------------------")

        return "\n".join(lines)

    def build_observation_view(
        self,
        *,
        round_limit: int = 5,
        include_user_input: bool = True,
        include_task: bool = True,
        include_reply: bool = True,
        include_trace: bool = False,
    ) -> list[dict[str, object]]:
        # 给 AI 读的观察视图。
        payload: list[dict[str, object]] = []
        for round_item in self.rounds[-round_limit:]:
            item: dict[str, object] = {"round": round_item.round}
            if include_user_input:
                item["user_input"] = round_item.user_input
            if include_trace:
                item["controller_trace"] = [action.to_dict() for action in round_item.controller_trace]
            if include_task:
                item["task"] = round_item.task.to_dict()
            if include_reply:
                item["reply"] = round_item.reply
            payload.append(item)
        return payload
