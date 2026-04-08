# Data Directory

本项目默认把开发/联调数据统一放在 `data/`，不区分真实或 fake 目录层级。

## 子目录

- `cases/`: 输入样本（包含历史 case 和新增样本）
- `environments/`: Environment full state 快照（rounds + cur_round + updated_at）
- `rl/`: controller 动作样本（jsonl）
- `outputs/`: 脚本运行输出摘要

## 约定

- 当前仓库里的 `data` 默认视为可用于开发和调试的数据集。
- 不再使用 `data/fake/` 分层。
