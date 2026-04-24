from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
RUN_SCRIPTS_ROOT = PROJECT_ROOT / "scripts" / "run"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(RUN_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(RUN_SCRIPTS_ROOT))


import run_cli_show
from task_router_graph.token_usage import empty_token_usage_summary


def _build_payload() -> dict[str, object]:
    token_usage = empty_token_usage_summary()
    token_usage["input_tokens"] = 20
    token_usage["output_tokens"] = 5
    token_usage["total_tokens"] = 25
    token_usage["call_count"] = 4
    token_usage["calls_with_usage"] = 3
    token_usage["calls_without_usage"] = 1
    token_usage["is_complete"] = False
    token_usage["by_bucket"]["controller"]["total_tokens"] = 11
    token_usage["by_bucket"]["controller"]["call_count"] = 2
    token_usage["by_bucket"]["controller"]["calls_without_usage"] = 0
    token_usage["by_bucket"]["controller"]["is_complete"] = True

    return {
        "output": {
            "case_id": "case_demo",
            "task_type": "executor",
            "task_status": "done",
            "task_result": "ok",
            "reply": "done",
            "run_dir": "var/runs/run_demo",
        },
        "environment": {"case_id": "case_demo", "rounds": [], "cur_round": 0, "updated_at": "", "history_summaries": [], "history_meta_summary": ""},
        "token_usage": token_usage,
        "token_usage_session": {
            **empty_token_usage_summary(),
            "input_tokens": 40,
            "output_tokens": 10,
            "total_tokens": 50,
            "call_count": 8,
            "calls_with_usage": 6,
            "calls_without_usage": 2,
            "is_complete": False,
        },
    }


def test_print_token_usage_renders_summary_and_bucket_details(monkeypatch) -> None:
    payload = _build_payload()
    lines: list[str] = []
    monkeypatch.setattr(run_cli_show, "print_cli_line", lambda message="": lines.append(message))

    run_cli_show._print_token_usage(payload)

    rendered = "\n".join(lines)
    assert "=== Token Usage ===" in rendered
    assert "total_tokens: 25" in rendered
    assert "calls_without_usage: 1" in rendered
    assert "controller: total=11" in rendered
    assert "history_rollup: total=0" in rendered


def test_print_result_raw_keeps_top_level_token_usage(monkeypatch) -> None:
    payload = _build_payload()
    lines: list[str] = []
    monkeypatch.setattr(run_cli_show, "print_cli_line", lambda message="": lines.append(message))

    run_cli_show._print_result(payload, show_environment=False, show_raw=True)

    rendered = "\n".join(lines)
    assert '"token_usage"' in rendered
    assert '"total_tokens": 25' in rendered


def test_token_usage_brief_contains_turn_and_session_values() -> None:
    payload = _build_payload()
    turn_usage = payload["token_usage"]
    session_usage = payload["token_usage_session"]
    assert isinstance(turn_usage, dict)
    assert isinstance(session_usage, dict)

    text = run_cli_show._build_token_usage_brief_text(turn_usage=turn_usage, session_usage=session_usage)
    assert "TokenUsage(turn/session):" in text
    assert "total=25/50" in text
    assert "complete=false/false" in text


def test_print_token_usage_supports_session_key(monkeypatch) -> None:
    payload = _build_payload()
    lines: list[str] = []
    monkeypatch.setattr(run_cli_show, "print_cli_line", lambda message="": lines.append(message))

    run_cli_show._print_token_usage(
        payload,
        key="token_usage_session",
        title="=== Token Usage Final (Session) ===",
    )
    rendered = "\n".join(lines)
    assert "=== Token Usage Final (Session) ===" in rendered
    assert "total_tokens: 50" in rendered
