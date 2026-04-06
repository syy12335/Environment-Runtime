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

### Action

```json
{
  "kind": "observe",
  "detail": "read environment memory",
  "args": {
    "round_count": 0,
    "user_input": "..."
  }
}
```

### Task

```json
{
  "type": "functest",
  "content": "Execute functest for: ...",
  "status": "done",
  "result": "functest completed (mocked)"
}
```

### RoundRecord

```json
{
  "round": 1,
  "user_input": "...",
  "action": { "...": "..." },
  "task": { "...": "..." },
  "reply": "..."
}
```

## 3. 最终输出

`var/runs/run_YYYYMMDD_HHMMSS/output.json`

```json
{
  "case_id": "case_01",
  "task_type": "functest",
  "task_status": "done",
  "task_result": "functest completed (mocked)",
  "reply": "[functest] completed with mocked assertions",
  "run_dir": "var/runs/run_YYYYMMDD_HHMMSS"
}
```

## 4. 每次运行产物

在 `var/runs/run_YYYYMMDD_HHMMSS/` 下生成：

- `input.json`
- `rounds.json`
- `tasks.json`
- `output.json`
