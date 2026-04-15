# task-router

基于 LangGraph 的小场景任务路由框架。Controller 接收用户输入后自动识别任务类型并分发执行，支持失败诊断与重试，每次运行的完整轨迹统一落盘至 `environment.json`。

## 任务类型

| 类型 | 说明 |
|---|---|
| `executor` | 通用执行任务，由 executor agent 直接处理 |
| `functest` | 占位，功能测试，可替换为任意工作流 |
| `accutest` | 占位，精度测试，可替换为任意工作流 |
| `perftest` | 占位，性能测试，可替换为任意工作流 |

## 流程

~~~
init → route → (executor | functest | accutest | perftest) → update → (failure_diagnose → route | final_reply) → end
```

- `route`：controller 判断任务类型，生成 task
- `update`：将结果与轨迹写入 environment
- `failure_diagnose`：失败时分析原因，回到 route 重试（最多 `max_failed_retries` 次）
- `final_reply`：round 结束时统一生成最终回复

## 安装

```bash
pip install -r requirements.txt
```

## 配置

主配置文件：`configs/graph.yaml`

```yaml
model:
  provider: sglang          # 或 aliyun，可用 MODEL_PROVIDER 环境变量覆盖

runtime:
  max_task_turns: 4
  max_failed_retries: 3
```

设置模型后端：

```bash
# 阿里云百炼
export MODEL_PROVIDER=aliyun
export API_KEY_Qwen=<your_key>

# 本地 sglang
export MODEL_PROVIDER=sglang
export SGLANG_API_KEY=EMPTY
```

## 运行

```bash
# 单次输入
python scripts/run/run_cli.py --config configs/graph.yaml --input "帮我做一次功能测试"

# 交互模式
python scripts/run/run_cli.py --config configs/graph.yaml --interactive

# 运行 case 文件
python scripts/run/run_case.py --config configs/graph.yaml --case data/cases/case_01.json

# 批量运行
python scripts/run/run_cases.py --config configs/graph.yaml

# 可视化界面
streamlit run scripts/run/streamlit_app.py

# 打印完整轨迹
python scripts/run/run_cli_show.py --config configs/graph.yaml --input "..."
```

输出目录：`var/runs/run_YYYYMMDD_HHMMSS/environment.json`

## 本地 SGLang

```bash
./scripts/sglang/start.sh    # 启动
./scripts/sglang/status.sh   # 状态
./scripts/sglang/stop.sh     # 停止
```

## 目录结构

```
configs/                  # 运行配置
data/cases/               # 示例 case
docs/                     # 设计与数据格式文档
scripts/run/              # 运行入口
scripts/sglang/           # SGLang 启停脚本
src/task_router_graph/    # 核心实现
  agents/                 # controller / executor / test / diagnosis / reply
  schema/                 # Task、Environment、Output 数据结构
  prompt/                 # 各节点 prompt
  graph.py                # LangGraph 主流程
  nodes.py                # 节点逻辑
tests/
var/runs/                 # 运行输出
```

## 文档

- `docs/design.md`：流程与节点设计
- `docs/environment.md`：environment 数据结构
- `docs/data_format.md`：输入输出格式
````