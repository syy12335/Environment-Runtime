"""task_router_graph 包入口。

通过懒加载方式导出 TaskRouterGraph，减少无关场景下的初始化开销。
"""

from __future__ import annotations

__all__ = ["TaskRouterGraph", "GraphRunResult"]


def __getattr__(name: str):
    if name in {"TaskRouterGraph", "GraphRunResult"}:
        from .graph import GraphRunResult, TaskRouterGraph

        if name == "TaskRouterGraph":
            return TaskRouterGraph
        return GraphRunResult
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
