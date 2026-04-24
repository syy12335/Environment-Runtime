from __future__ import annotations

import os
import socket
import threading
import time
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any, Callable, TypeVar
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import yaml

T = TypeVar("T")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
WAIT_INDICATOR_LABEL = "等待中"
WAIT_INDICATOR_INTERVAL_SEC = 1.0
WAIT_INDICATOR_MAX_DOTS = 6
_OUTPUT_LOCK = threading.RLock()
_WAIT_INDICATOR_ACTIVE = False
_WAIT_INDICATOR_WIDTH = 0


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
    with _OUTPUT_LOCK:
        clear_wait_line()
        print(f"[{ts}] {message}", flush=True)


def clear_wait_line() -> None:
    global _WAIT_INDICATOR_ACTIVE, _WAIT_INDICATOR_WIDTH
    if not _WAIT_INDICATOR_ACTIVE:
        return
    if not sys.stdout.isatty():
        _WAIT_INDICATOR_ACTIVE = False
        _WAIT_INDICATOR_WIDTH = 0
        return
    blank = " " * max(0, _WAIT_INDICATOR_WIDTH)
    sys.stdout.write(f"\r{blank}\r")
    sys.stdout.flush()
    _WAIT_INDICATOR_ACTIVE = False
    _WAIT_INDICATOR_WIDTH = 0


def print_cli_line(message: str = "") -> None:
    with _OUTPUT_LOCK:
        clear_wait_line()
        print(message, flush=True)


def _display_width(text: str) -> int:
    width = 0
    for char in text:
        width += 2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1
    return width


def display_path(path: Path | str, *, project_root: Path = PROJECT_ROOT) -> str:
    target = Path(str(path)).resolve()
    root = project_root.resolve()
    try:
        return target.relative_to(root).as_posix()
    except Exception:
        return os.path.relpath(str(target), str(root))


def resolve_run_dir(*, project_root: Path, run_id: str) -> Path:
    normalized = str(run_id).strip()
    if not normalized:
        raise ValueError("run_id is required to resolve run directory")
    return project_root / "var" / "runs" / f"run_{normalized}"


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")


def persist_run_result(
    result: Any,
    *,
    project_root: Path,
    token_usage_session: dict[str, Any] | None = None,
) -> tuple[Path, dict[str, Any]]:
    from task_router_graph.token_usage import empty_token_usage_summary
    from task_router_graph.utils import write_json

    run_id = str(getattr(result, "run_id", "")).strip()
    if not run_id:
        raise ValueError("GraphRunResult.run_id is required")

    run_dir = resolve_run_dir(project_root=project_root, run_id=run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    environment = getattr(result, "environment", None)
    output = getattr(result, "output", None)
    if environment is None or output is None:
        raise ValueError("GraphRunResult must include environment and output")

    environment_payload = environment.to_dict(include_trace=True)
    environment_payload["case_id"] = str(getattr(output, "case_id", "")).strip()
    write_json(run_dir / "environment.json", environment_payload)

    output_payload = output.to_dict()
    output_payload["run_dir"] = str(run_dir.relative_to(project_root))
    token_usage = getattr(result, "token_usage", {})
    if not isinstance(token_usage, dict):
        token_usage = empty_token_usage_summary()
    result_payload = {
        "run_id": run_id,
        "case_id": str(output_payload.get("case_id", "")).strip(),
        "output": output_payload,
        "token_usage": token_usage,
    }
    if isinstance(token_usage_session, dict):
        result_payload["token_usage_session"] = token_usage_session
    write_json(
        run_dir / "result.json",
        result_payload,
    )

    archive_records_raw = getattr(result, "archive_records", [])
    archive_records: list[dict[str, Any]] = []
    if isinstance(archive_records_raw, list):
        for item in archive_records_raw:
            if isinstance(item, dict):
                archive_records.append(item)
    append_jsonl(run_dir / "environment_archive.jsonl", archive_records)
    return run_dir, environment_payload


def serialize_run_result(
    result: Any,
    *,
    project_root: Path,
    token_usage_session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from task_router_graph.schema import to_dict
    from task_router_graph.token_usage import empty_token_usage_summary

    run_dir = resolve_run_dir(project_root=project_root, run_id=str(getattr(result, "run_id", "")))
    output_payload = to_dict(getattr(result, "output"))
    output_payload["run_dir"] = str(run_dir.relative_to(project_root))
    environment_payload = getattr(result, "environment").to_dict(include_trace=True)
    environment_payload["case_id"] = str(output_payload.get("case_id", "")).strip()
    token_usage = getattr(result, "token_usage", {})
    if not isinstance(token_usage, dict):
        token_usage = empty_token_usage_summary()
    payload = {
        "environment": environment_payload,
        "output": output_payload,
        "token_usage": token_usage,
    }
    if isinstance(token_usage_session, dict):
        payload["token_usage_session"] = token_usage_session
    return payload


def with_heartbeat(task_name: str, fn: Callable[[], T]) -> tuple[T, float]:
    start = time.perf_counter()
    stop_event = threading.Event()
    indicator_enabled = sys.stdout.isatty()

    def _heartbeat() -> None:
        global _WAIT_INDICATOR_ACTIVE, _WAIT_INDICATOR_WIDTH
        dots = 0
        while True:
            frame = WAIT_INDICATOR_LABEL + ("." * dots)
            frame_width = _display_width(frame)
            with _OUTPUT_LOCK:
                if not indicator_enabled:
                    continue
                padding = " " * max(0, _WAIT_INDICATOR_WIDTH - frame_width)
                _WAIT_INDICATOR_ACTIVE = True
                _WAIT_INDICATOR_WIDTH = frame_width
                sys.stdout.write(f"\r{frame}{padding}")
                sys.stdout.flush()
            if stop_event.wait(WAIT_INDICATOR_INTERVAL_SEC):
                break
            dots = 0 if dots >= WAIT_INDICATOR_MAX_DOTS else dots + 1

    heartbeat_thread = None
    if indicator_enabled:
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
        with _OUTPUT_LOCK:
            clear_wait_line()

    elapsed = time.perf_counter() - start
    log(f"{task_name} finished in {elapsed:.1f}s")
    return result, elapsed


def _resolve_config_path(config_path: str | Path) -> Path:
    path = Path(str(config_path).strip())
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def _load_model_cfg(config_path: str | Path) -> tuple[dict[str, Any], str]:
    path = _resolve_config_path(config_path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("config must be a yaml mapping")

    model_cfg = payload.get("model")
    if not isinstance(model_cfg, dict):
        raise ValueError("config.model must be a mapping")

    provider_env = str(model_cfg.get("provider_env", "MODEL_PROVIDER")).strip() or "MODEL_PROVIDER"
    return model_cfg, provider_env


def _resolve_provider_api_key(provider_cfg: dict[str, Any]) -> str:
    api_key_env = str(provider_cfg.get("api_key_env", "")).strip()
    if api_key_env:
        env_val = os.getenv(api_key_env, "").strip()
        if env_val:
            return env_val

    explicit = str(provider_cfg.get("api_key", "")).strip()
    if explicit:
        return explicit

    return "EMPTY"


def _probe_http(base_url: str, api_key: str, timeout_sec: float = 1.5) -> bool:
    probe_url = f"{base_url.rstrip('/')}/models"
    req = Request(probe_url, headers={"Authorization": f"Bearer {api_key or 'EMPTY'}"})
    try:
        with urlopen(req, timeout=timeout_sec):
            return True
    except HTTPError:
        # 401/404 等也表示服务已启动并可达。
        return True
    except URLError:
        return False
    except Exception:
        return False


def _is_sglang_available(providers: dict[str, Any]) -> bool:
    sglang_cfg = providers.get("sglang")
    if not isinstance(sglang_cfg, dict):
        return False

    base_url = str(sglang_cfg.get("base_url", "")).strip()
    if not base_url:
        return False

    parsed = urlparse(base_url)
    host = (parsed.hostname or "").strip()
    if not host:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        with socket.create_connection((host, port), timeout=1.0):
            pass
    except OSError:
        return False

    api_key = _resolve_provider_api_key(sglang_cfg)
    return _probe_http(base_url=base_url, api_key=api_key)


def ensure_preferred_provider_and_log(config_path: str | Path) -> tuple[str, str, str]:
    model_cfg, provider_env = _load_model_cfg(config_path)
    providers = model_cfg.get("providers")
    if not isinstance(providers, dict) or not providers:
        raise ValueError("model.providers must be a non-empty mapping")

    default_provider = str(model_cfg.get("provider", "")).strip()
    env_provider = os.getenv(provider_env, "").strip()

    preferred = "sglang" if "sglang" in providers else (default_provider or next(iter(providers.keys())))
    selected = env_provider or preferred

    reason = "env override" if env_provider else "default to sglang"

    if selected not in providers:
        selected = preferred
        reason = f"invalid env provider, fallback to {selected}"

    if selected == "sglang" and not _is_sglang_available(providers):
        if "aliyun" in providers:
            selected = "aliyun"
            reason = "sglang unavailable, fallback to aliyun"
        else:
            non_sglang = [name for name in providers.keys() if str(name) != "sglang"]
            if non_sglang:
                selected = str(non_sglang[0])
                reason = f"sglang unavailable, fallback to {selected}"
            else:
                reason = "sglang unavailable, no fallback provider"

    os.environ[provider_env] = selected

    provider_cfg = providers.get(selected)
    model_name = ""
    if isinstance(provider_cfg, dict):
        model_name = str(provider_cfg.get("name", "")).strip()

    log(
        "Provider selected before startup: "
        f"provider={selected}, model={model_name or '-'}, env={provider_env}, reason={reason}"
    )

    return selected, model_name, provider_env
