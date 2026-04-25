# Task Router Train Overview

## 定位

`task_router_graph_train` 负责 controller-only 的训练、固定 holdout 评测和后训练回流。

它和运行时包的边界固定为：

- 运行时逻辑在 `src/task_router_graph/`
- 训练与评测逻辑在 `src/task_router_graph_train/`
- 训练包可以依赖运行时包
- 运行时包不能反向依赖训练包

## 当前主线

当前主线固定为四段：

1. `manual_protocol_v1`
2. `SFT`
3. `GRPO`
4. `badcase -> teacher -> next round SFT`

这里训练的是外层 `controller` 的 single-step next-action policy。

- `state`
  - `USER_INPUT`
  - `ENVIRONMENT_JSON`
  - `SKILLS_INDEX`
- `action_space`
  - `observe`
  - `generate_task`

## 文档入口

主线文档分成三份：

- `post_training_v1.md`
  - 主线方案
  - `SFT / GRPO / badcase` 回流规则
- `controller_grpo_reward_spec.md`
  - controller `GRPO` reward 正式口径
- `manual_protocol_v1_draft.md`
  - 手写推敲稿

`overview.md` 只保留总图，不重复展开 reward 细则和后训练细则。

## 模块结构

- `runtime_adapter.py`
  - 从运行时语义构造训练态输入
- `dataset/`
  - 负责样本清洗、state 构造和训练数据派生
- `train/`
  - 负责 controller `SFT` 与 controller `GRPO`
- `eval/`
  - 负责固定 holdout 评测
- `feedback.py`
  - 负责后训练回流辅助逻辑
- `artifacts.py`
  - 负责训练资产与 manifest 解析

## 当前关键约定

- `manual_protocol_v1` 是 frozen base
- `state_input` 固定为 `USER_INPUT / ENVIRONMENT_JSON / SKILLS_INDEX`
- `holdout` 固定保留，不进入训练
- `GRPO` 主路径不保留 `reference_action`
- badcase 经 teacher 标注后，只回流成下一轮 `SFT`

## 当前非目标

- reply 训练闭环
- multi-step / full-trajectory GRPO
- reward model / critic / PPO 训练栈
- 把 `.private/` 学习材料当作正式实现文档
