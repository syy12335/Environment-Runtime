from __future__ import annotations

import io
import re
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_SCRIPTS_ROOT = PROJECT_ROOT / "scripts" / "run"
if str(RUN_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(RUN_SCRIPTS_ROOT))


import run_common


class _FakeStdout(io.StringIO):
    def __init__(self, *, is_tty: bool) -> None:
        super().__init__()
        self._is_tty = is_tty

    def isatty(self) -> bool:
        return self._is_tty


def test_with_heartbeat_renders_wait_indicator_and_wraps(monkeypatch) -> None:
    fake_stdout = _FakeStdout(is_tty=True)
    monkeypatch.setattr(run_common, "WAIT_INDICATOR_INTERVAL_SEC", 0.005)
    monkeypatch.setattr(run_common, "_WAIT_INDICATOR_ACTIVE", False)
    monkeypatch.setattr(run_common, "_WAIT_INDICATOR_WIDTH", 0)
    monkeypatch.setattr(sys, "stdout", fake_stdout)

    result, elapsed = run_common.with_heartbeat("demo task", lambda: time.sleep(0.05) or "done")

    assert result == "done"
    assert elapsed > 0
    output = fake_stdout.getvalue()
    frames = re.findall(r"\r等待中\.{0,6}", output)
    assert "\r等待中" in frames
    assert "\r等待中." in frames
    assert "\r等待中.." in frames
    assert "\r等待中..." in frames
    assert "\r等待中...." in frames
    assert "\r等待中....." in frames
    assert "\r等待中......" in frames

    wrap_start = frames.index("\r等待中......")
    assert "\r等待中" in frames[wrap_start + 1 :]
    assert "demo task finished in" in output


def test_with_heartbeat_logs_failure_and_stops_indicator(monkeypatch) -> None:
    fake_stdout = _FakeStdout(is_tty=True)
    monkeypatch.setattr(run_common, "WAIT_INDICATOR_INTERVAL_SEC", 0.005)
    monkeypatch.setattr(run_common, "_WAIT_INDICATOR_ACTIVE", False)
    monkeypatch.setattr(run_common, "_WAIT_INDICATOR_WIDTH", 0)
    monkeypatch.setattr(sys, "stdout", fake_stdout)

    def _boom() -> None:
        time.sleep(0.02)
        raise RuntimeError("boom")

    try:
        run_common.with_heartbeat("broken task", _boom)
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:
        raise AssertionError("expected RuntimeError")

    output = fake_stdout.getvalue()
    assert "\r等待中" in output
    assert "broken task failed after" in output
    assert "finished in" not in output


def test_with_heartbeat_degrades_without_tty(monkeypatch) -> None:
    fake_stdout = _FakeStdout(is_tty=False)
    monkeypatch.setattr(run_common, "WAIT_INDICATOR_INTERVAL_SEC", 0.005)
    monkeypatch.setattr(run_common, "_WAIT_INDICATOR_ACTIVE", False)
    monkeypatch.setattr(run_common, "_WAIT_INDICATOR_WIDTH", 0)
    monkeypatch.setattr(sys, "stdout", fake_stdout)

    result, _ = run_common.with_heartbeat("plain task", lambda: time.sleep(0.02) or 7)

    assert result == 7
    output = fake_stdout.getvalue()
    assert "\r等待中" not in output
    assert "plain task finished in" in output

