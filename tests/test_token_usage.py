from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from task_router_graph.schema import Environment, Task
from task_router_graph.token_usage import (
    TokenUsageRecorder,
    extract_token_usage,
    invoke_with_usage,
    merge_token_usage_summary,
)


def test_extract_token_usage_prefers_usage_metadata() -> None:
    response = SimpleNamespace(
        usage_metadata={"input_tokens": 11, "output_tokens": 7, "total_tokens": 18},
        response_metadata={"token_usage": {"prompt_tokens": 99, "completion_tokens": 1, "total_tokens": 100}},
    )

    assert extract_token_usage(response) == {
        "input_tokens": 11,
        "output_tokens": 7,
        "total_tokens": 18,
    }


def test_extract_token_usage_falls_back_to_response_metadata_token_usage() -> None:
    response = SimpleNamespace(
        response_metadata={"token_usage": {"prompt_tokens": 13, "completion_tokens": 5, "total_tokens": 18}},
    )

    assert extract_token_usage(response) == {
        "input_tokens": 13,
        "output_tokens": 5,
        "total_tokens": 18,
    }


def test_extract_token_usage_returns_none_when_missing() -> None:
    response = SimpleNamespace(content="hello")
    assert extract_token_usage(response) is None


def test_graph_run_accumulates_token_usage_across_multiple_buckets() -> None:
    pytest.importorskip("langgraph")
    from task_router_graph.graph import TaskRouterGraph

    graph = TaskRouterGraph.__new__(TaskRouterGraph)

    class _FakeLLM:
        def __init__(self, usage_metadata: dict[str, int]) -> None:
            self._usage_metadata = usage_metadata

        def invoke(self, messages, config=None):  # type: ignore[no-untyped-def]
            del messages, config
            return SimpleNamespace(content='{"ok": true}', usage_metadata=dict(self._usage_metadata))

    def _fake_run_state_invoke(*, initial_state, case_id):  # type: ignore[no-untyped-def]
        del case_id
        recorder = initial_state["token_usage_recorder"]
        invoke_with_usage(
            llm=_FakeLLM({"input_tokens": 10, "output_tokens": 2, "total_tokens": 12}),
            messages=[],
            usage_recorder=recorder,
            bucket="controller",
        )
        invoke_with_usage(
            llm=_FakeLLM({"input_tokens": 6, "output_tokens": 1, "total_tokens": 7}),
            messages=[],
            usage_recorder=recorder,
            bucket="context_compression",
        )
        invoke_with_usage(
            llm=_FakeLLM({"input_tokens": 4, "output_tokens": 3, "total_tokens": 7}),
            messages=[],
            usage_recorder=recorder,
            bucket="reply",
        )

        return {
            "environment": Environment(),
            "task": Task(type="executor", content="demo", status="done", result="ok"),
            "reply": "done",
            "run_id": "run_demo",
            "archive_records": [],
            "token_usage_recorder": recorder,
        }

    graph._run_state_invoke = _fake_run_state_invoke  # type: ignore[attr-defined]
    graph._run_state_stream = _fake_run_state_invoke  # type: ignore[attr-defined]

    result = graph.run(case_id="case_demo", user_input="hello")

    assert result.run_id == "run_demo"
    assert result.token_usage["total_tokens"] == 26
    assert result.token_usage["input_tokens"] == 20
    assert result.token_usage["output_tokens"] == 6
    assert result.token_usage["call_count"] == 3
    assert result.token_usage["calls_with_usage"] == 3
    assert result.token_usage["calls_without_usage"] == 0
    assert result.token_usage["by_bucket"]["controller"]["total_tokens"] == 12
    assert result.token_usage["by_bucket"]["context_compression"]["total_tokens"] == 7
    assert result.token_usage["by_bucket"]["reply"]["total_tokens"] == 7
    assert result.token_usage["by_bucket"]["executor"]["total_tokens"] == 0


def test_token_usage_recorder_tracks_missing_usage_without_estimating() -> None:
    recorder = TokenUsageRecorder()
    recorder.record_response(bucket="controller", response=SimpleNamespace(content="ok"))

    summary = recorder.summary()
    assert summary["call_count"] == 1
    assert summary["calls_with_usage"] == 0
    assert summary["calls_without_usage"] == 1
    assert summary["total_tokens"] == 0
    assert summary["is_complete"] is False


def test_merge_token_usage_summary_accumulates_top_level_and_buckets() -> None:
    left = {
        "input_tokens": 10,
        "output_tokens": 3,
        "total_tokens": 13,
        "call_count": 2,
        "calls_with_usage": 2,
        "calls_without_usage": 0,
        "by_bucket": {
            "controller": {
                "input_tokens": 10,
                "output_tokens": 3,
                "total_tokens": 13,
                "call_count": 2,
                "calls_with_usage": 2,
                "calls_without_usage": 0,
            }
        },
    }
    right = {
        "input_tokens": 8,
        "output_tokens": 2,
        "total_tokens": 10,
        "call_count": 3,
        "calls_with_usage": 2,
        "calls_without_usage": 1,
        "by_bucket": {
            "reply": {
                "input_tokens": 8,
                "output_tokens": 2,
                "total_tokens": 10,
                "call_count": 3,
                "calls_with_usage": 2,
                "calls_without_usage": 1,
            }
        },
    }

    merged = merge_token_usage_summary(left, right)

    assert merged["input_tokens"] == 18
    assert merged["output_tokens"] == 5
    assert merged["total_tokens"] == 23
    assert merged["call_count"] == 5
    assert merged["calls_with_usage"] == 4
    assert merged["calls_without_usage"] == 1
    assert merged["is_complete"] is False
    assert merged["by_bucket"]["controller"]["total_tokens"] == 13
    assert merged["by_bucket"]["reply"]["total_tokens"] == 10
    assert merged["by_bucket"]["reply"]["is_complete"] is False


def test_merge_token_usage_summary_tolerates_missing_or_invalid_payload() -> None:
    merged = merge_token_usage_summary(
        {
            "total_tokens": 5,
            "calls_without_usage": 0,
            "by_bucket": {"controller": {"total_tokens": 5, "calls_without_usage": 0}},
        },
        {"by_bucket": {"controller": {"total_tokens": "bad", "calls_without_usage": 2}}},
    )

    assert merged["total_tokens"] == 5
    assert merged["calls_without_usage"] == 0
    assert merged["is_complete"] is True
    assert merged["by_bucket"]["controller"]["total_tokens"] == 5
    assert merged["by_bucket"]["controller"]["calls_without_usage"] == 2
    assert merged["by_bucket"]["controller"]["is_complete"] is False
