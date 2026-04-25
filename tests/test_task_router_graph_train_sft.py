from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from task_router_graph_train.dataset import prepare_round_assets
from task_router_graph_train.train import controller_sft


def test_train_controller_sft_signature_drops_legacy_manifest_inputs() -> None:
    params = inspect.signature(controller_sft.train_controller_sft).parameters
    assert "asset_manifest" not in params
    assert "run_dir" not in params


def test_sft_input_resolution_defaults_to_latest_round(tmp_path: Path) -> None:
    round_root = tmp_path / "rounds"
    report = prepare_round_assets(round_id="round_0001", round_assets_root=round_root)
    train_path, eval_path, manifest_path = controller_sft._resolve_sft_input_paths(
        train_examples=None,
        eval_examples=None,
        round_id=None,
        round_manifest=Path(report["manifest_path"]),
        allow_unsafe_path_input=False,
    )
    assert train_path.exists()
    assert eval_path.exists()
    assert manifest_path.endswith("round_manifest.json")


def test_sft_input_resolution_rejects_unsafe_without_flag(tmp_path: Path) -> None:
    train_path = tmp_path / "train.jsonl"
    eval_path = tmp_path / "eval.jsonl"
    train_path.write_text("", encoding="utf-8")
    eval_path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        controller_sft._resolve_sft_input_paths(
            train_examples=train_path,
            eval_examples=eval_path,
            round_id=None,
            round_manifest=None,
            allow_unsafe_path_input=False,
        )
