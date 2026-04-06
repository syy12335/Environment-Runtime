# 数据格式

## 1. 输入 case

`data/cases/*.json`

```json
{
  "case_id": "case_01",
  "user_input": "请帮我做一次 anthropic_ver_1 的功能测试"
}
```

## 2. 中间结构

### ControllerAction

```json
{
  "action_kind": "observe|generate_task",
  "reason": "简短原因",
  "tool": "read|ls|null",
  "args": {},
  "task_type": "normal|functest|accutest|perftest|null",
  "task_content": "任务内容或null",
  "observation": "观察结果或null"
}
```

说明：

- `observe` 动作通常带 `tool/args/observation`
- `generate_task` 动作通常带 `task_type/task_content`

### Task

```json
{
  "type": "functest",
  "content": "针对 anthropic_ver_1 执行功能测试，重点检查 headers、body 与 assert",
  "status": "done",
  "result": "functest completed (mocked)"
}
```

### RoundRecord

```json
{
  "round": 1,
  "user_input": "...",
  "controller_trace": [
    {
      "action_kind": "observe",
      "reason": "需要读取最近测试结果",
      "tool": "read",
      "args": {"path": "var/runs/latest/output.json"},
      "observation": "..."
    },
    {
      "action_kind": "generate_task",
      "reason": "信息已足够",
      "task_type": "normal",
      "task_content": "根据最近一次 functest 结果整理失败原因摘要"
    }
  ],
  "task": {
    "type": "normal",
    "content": "根据最近一次 functest 结果整理失败原因摘要",
    "status": "done",
    "result": "已基于历史结果完成解释"
  },
  "reply": "最近一次失败主要是 code 字段断言不匹配。"
}
```

## 3. 最终输出

`var/runs/run_YYYYMMDD_HHMMSS/output.json`

```json
{
  "case_id": "case_01",
  "task_type": "normal",
  "task_status": "done",
  "task_result": "已基于历史结果完成解释",
  "reply": "最近一次失败主要是 code 字段断言不匹配。",
  "run_dir": "var/runs/run_YYYYMMDD_HHMMSS"
}
```

## 4. 每次运行产物

在 `var/runs/run_YYYYMMDD_HHMMSS/` 下生成：

- `input.json`
- `rounds.json`
- `tasks.json`
- `output.json`
