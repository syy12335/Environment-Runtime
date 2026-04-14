from __future__ import annotations

import threading
import time
from typing import Callable, TypeVar

T = TypeVar("T")


def flush_tracers() -> None:
    try:
        from langchain_core.tracers.langchain import wait_for_all_tracers
    except Exception:
        return

    try:
        wait_for_all_tracers()
    except Exception:
        return


def log(message: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {message}", flush=True)


def with_heartbeat(task_name: str, interval_sec: float, fn: Callable[[], T]) -> tuple[T, float]:
    interval_sec = max(0.0, float(interval_sec))
    start = time.perf_counter()
    stop_event = threading.Event()

    def _heartbeat() -> None:
        while not stop_event.wait(interval_sec):
            elapsed = time.perf_counter() - start
            log(f"{task_name} still running... {elapsed:.0f}s elapsed")

    heartbeat_thread = None
    if interval_sec > 0:
        heartbeat_thread = threading.Thread(target=_heartbeat, daemon=True)
        heartbeat_thread.start()

    try:
        result = fn()
    except Exception:
        elapsed = time.perf_counter() - start
        log(f"{task_name} failed after {elapsed:.1f}s")
        raise
    finally:
        stop_event.set()
        if heartbeat_thread is not None:
            heartbeat_thread.join(timeout=0.2)

    elapsed = time.perf_counter() - start
    log(f"{task_name} finished in {elapsed:.1f}s")
    return result, elapsed
