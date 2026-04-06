# 设计说明

## 1. 目标

用最小实现把 Prompt/Skills 与运行时代码对齐：

- controller 按 `observe | generate_task` 动作语义决策
- normal 按 `task_content + rounds + normal skills` 执行
- rounds 持久化 `controller_trace`，用于下一轮观察

## 2. Graph 结构

当前主流程为：

`route -> execute -> update`（由 LangGraph StateGraph 编排）

说明：

- `route` 节点内部调用 `ControllerAgent` 的 LangChain loop
- controller loop 在一个节点内完成多步 `observe`，最终产出一个 `generate_task`
- `execute` 根据 task.type 分发执行，normal 走 `NormalAgent`
- `update` 回写 `controller_trace + task + reply` 到 environment

## 3. Controller Loop

`ControllerAgent` 每次运行接收：

- `USER_INPUT`
- `ROUNDS_JSON`
- `SKILLS_INDEX`

并在内部循环：

1. 输出 `observe` 或 `generate_task`
2. 若是 `observe`，调用工具（`read` / `ls`）写入 observation
3. 继续下一步
4. 直到输出 `generate_task` 或达到 `max_controller_steps`

## 4. Prompt + Skills 注入

- controller system：`src/task_router_graph/prompt/controller/system.md`
- normal system：`src/task_router_graph/prompt/normal/system.md`
- controller skills：`src/task_router_graph/skills/controller/INDEX.md` + references
- normal skills：`src/task_router_graph/skills/normal/INDEX.md`

注入方式：

- system 使用占位符（`{{USER_INPUT}}/{{ROUNDS_JSON}}/{{SKILLS_INDEX}}` 等）
- agent 运行前完成 format 注入

## 5. 文件映射

- `src/task_router_graph/schema.py`：`ControllerAction / Task / RoundRecord / Environment`
- `src/task_router_graph/agents/controller_agent.py`：controller LangChain loop
- `src/task_router_graph/agents/normal_agent.py`：normal 执行 agent
- `src/task_router_graph/nodes.py`：route/execute/update 节点与 observe tools
- `src/task_router_graph/graph.py`：LangGraph 编排入口
