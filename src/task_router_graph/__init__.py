"""task_router_graph package."""

from __future__ import annotations

__all__ = ["TaskRouterGraph"]


def __getattr__(name: str):
    if name == "TaskRouterGraph":
        from .graph import TaskRouterGraph

        return TaskRouterGraph
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
