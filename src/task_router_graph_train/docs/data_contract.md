# Task Router Train 数据契约

## 目标

这份文档只定义当前主线里的正式对象：

- `manual_protocol_v1`
- `state_input`
- `holdout`
- `teacher_queue`
- `sft_admissions`

reward 细则见 `controller_grpo_reward_spec.md`。  
后训练回流规则见 `post_training_v1.md`。

## 1. manual_protocol_v1

当前基础真源位于：

- `src/task_router_graph_train/assets/manual_protocol_v1/manifest.json`
- `src/task_router_graph_train/assets/manual_protocol_v1/samples.jsonl`

`manifest.json` 最小字段：

- `dataset`
- `version`
- `bucket_registry`
- `counts_by_split`
- `counts_by_bucket_split`

`samples.jsonl` 每条最小字段：

- `sample_id`
- `bucket_key`
- `split`
- `template_id`
- `user_input`
- `environment`
- `target_action`
- `terminal`

约定：

- `environment` 只保留 formal visible state
- `target_action` 必须通过 runtime controller action schema
- `target_action` 必须符合当前 controller output protocol
- `holdout` 与 `SFT` 同源维护，但 `holdout` 不进入训练

## 2. state_input

`build_controller_state_input(...)` 的输出固定为：

```json
{
  "USER_INPUT": "...",
  "ENVIRONMENT_JSON": {},
  "SKILLS_INDEX": "..."
}
```

约定：

- `state_input` 是训练态真源
- prompt 文本由后续渲染步骤生成
- `ENVIRONMENT_JSON` 是 controller 可见视图，不是 runtime full state
- hidden state、verifier sidecar、only-track 细节都不能直接进入 `state_input`

## 3. SFT

当前轮次的 `SFT` 数据来源固定为：

```text
manual_protocol_v1.sft + previous_round.sft_admissions
```

`SFT` 样本约定：

- 输入是 `state_input`
- 输出是一条 controller gold action
- gold action 必须 schema-valid
- gold action 必须 protocol-valid
- gold action 必须 grounded in 当前可见 environment

文本化后的 `prompt / target_text` 只属于训练派生产物，不属于基础真源。

## 4. GRPO

`GRPO` 的 policy object 与 `SFT` 完全一致：

- 输入：`USER_INPUT + ENVIRONMENT_JSON + SKILLS_INDEX`
- 输出：controller next action

约定：

- `GRPO` 主路径不保留 `reference_action`
- reward 只看 teacher 对 rollout candidates 的判断
- hard gate 和 ranking 细则以 `controller_grpo_reward_spec.md` 为准
- `holdout` 只用于验证，不参与 `GRPO` 优化

## 5. holdout

`holdout` 是固定保留的 controller next-action gold set。

约定：

- 与 `SFT` 同样基于 `manual_protocol_v1`
- 不进入训练
- 用于固定 baseline 对比和回流判定

## 6. teacher_queue

`teacher_queue` 是运行后积累的待标注样本集合。

入队条件和 teacher 规则以 `post_training_v1.md` 为准。  
这里的最小要求只有：

- 能复现当前输入和可见 environment
- 能复现当前 policy 输出
- 能说明样本来源和触发原因

## 7. sft_admissions

`sft_admissions` 是 teacher 接纳后的增量 supervised 样本。

最小要求：

- `reference_action` 稳定
- `reference_action` schema-valid
- `reference_action` protocol-valid
- 与现有训练样本不高度重复

下一轮 `SFT` 只接纳这部分增量样本。

## 8. 历史对象

下面这些对象不再作为当前主线契约：

- `teacher_source`
- `badcase_pool`
- `feedback_manifest.json`
- `controller_regression_records_v1`
- `verl_rl_dataset_v1`

如果代码里还保留兼容逻辑，它们也只属于历史路径，不再作为当前文档主线入口。
