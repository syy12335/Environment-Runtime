# Skills 机制说明

本文档说明当前项目中 controller / executor 两类 skill 的组织与注入方式。

## 1. 总览

- controller：`INDEX.md + reference` 模式（用于路由规则与 task_content 生成口径）。
- executor：`skill.md` 插件目录模式（用于执行策略与工具调用顺序约束）。

两者都通过 agent 注入到模型上下文；graph 层不承载 skill 业务细节。

## 2. Controller Skills（路由知识）

目录：`src/task_router_graph/skills/controller`

当前入口：`src/task_router_graph/skills/controller/INDEX.md`

行为要点：

1. controller agent 读取 `INDEX.md`，并按引用关系加载对应 task reference 文件。
2. controller 负责决定 `task_type + task_content`，不直接执行结果检索与回答。
3. controller 可使用 observe 工具补充“路由所需事实”。

## 3. Executor Skills（插件化扩展）

目录：`src/task_router_graph/skills/executor`

自动发现规则：

1. 递归扫描 `skills/executor/**/skill.md`。
2. 仅采集 frontmatter 的核心字段：
   - `name`
   - `description`
   - `when_to_use`（兼容 `when-to-use`）
3. `path` 由系统自动注入为仓库相对路径。
4. 这些元数据会注入 `EXECUTOR_SKILLS_INDEX`，供模型先做命中判断。
5. 命中后，executor 再通过 `read {"path":"..."}` 读取 skill 正文并执行。

### 3.1 注入位置（实现口径）

1. 注入发生在 executor agent，而不是 graph 编排层。
2. 参考实现：`src/task_router_graph/agents/executor_agent.py`
   - `_load_executor_skill_catalog()`：扫描并提取元数据
   - `_build_executor_skill_registry()`：构建 `EXECUTOR_SKILLS_INDEX`
   - `run_executor_task()`：在运行时注入 system prompt 占位
3. prompt 占位在 `src/task_router_graph/prompt/executor/system.md` 的 `[EXECUTOR_SKILLS_INDEX]` 块。

## 4. 新增一个 Executor Skill（标准流程）

### 4.1 创建目录与文件

```text
src/task_router_graph/skills/executor/
  my_skill/
    skill.md
```

### 4.2 写入最小 frontmatter

```yaml
---
name: my-skill
description: 这个 skill 解决什么问题
when_to_use: 在什么条件下应命中这个 skill
---
# Skill 正文规则
```

### 4.3 写正文规则

建议正文包含：

1. 目标
2. 必须顺序
3. 禁止项
4. 失败止损
5. 完成判定

## 5. 约束与建议

1. skill `name` 应稳定且唯一，避免归一化后冲突。
2. `when_to_use` 要可判定，避免“泛描述”导致误命中。
3. skill 正文应尽量给出工具调用顺序和失败止损条件。
4. 不需要改 `graph.py`，也不需要维护 executor 的 `INDEX.md`。

## 6. 现有示例

- `src/task_router_graph/skills/executor/greeting_guide/skill.md`
- `src/task_router_graph/skills/executor/time_range_info/skill.md`

以上分别覆盖：问候引导场景、时间段信息查询（先时间锚定再外部检索）场景。
