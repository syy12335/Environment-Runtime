# task_router_graph_train

`task_router_graph_train` 负责 controller-only 的训练、固定 holdout 评测和后训练回流。

当前主线固定为：

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

## Docs

正式文档在 `src/task_router_graph_train/docs/`：

- `overview.md`
  - 模块定位和主线总览
- `data_contract.md`
  - 当前主线对象和数据契约
- `controller_grpo_reward_spec.md`
  - controller-only `GRPO` reward 正式口径
- `post_training_v1.md`
  - `SFT / GRPO / badcase` 回流规则
- `manual_protocol_v1_draft.md`
  - 手写推敲稿

学习材料在 `.private/task_router_graph_train/`。

## Assets

主线真源和评测资产在：

- `src/task_router_graph_train/assets/manual_protocol_v1/`
- `src/task_router_graph_train/assets/eval_samples/manual_eval/`

其余 `sft_v1/`、`rl_v1/` 目录如果仍然存在，只视为历史或兼容资产，不作为当前文档主线入口。

## 当前非目标

- reply 训练闭环
- multi-step / full-trajectory GRPO
- reward model / critic / PPO 训练栈
- 把 `.private/` 学习材料当作正式实现文档
