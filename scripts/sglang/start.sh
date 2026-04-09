#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${SGLANG_LOG_DIR:-$ROOT_DIR/var/logs}"
LOG_FILE="${SGLANG_LOG_FILE:-$LOG_DIR/sglang.log}"
PID_FILE="${SGLANG_PID_FILE:-$ROOT_DIR/var/sglang.pid}"

MODEL_PATH="${SGLANG_MODEL_PATH:-/model/default/Qwen3.5-4B}"
SERVED_MODEL_NAME="${SGLANG_SERVED_MODEL_NAME:-qwen35-4b}"
HOST="${SGLANG_HOST:-127.0.0.1}"
PORT="${SGLANG_PORT:-30000}"
API_KEY="${SGLANG_API_KEY:-EMPTY}"

CONDA_ACTIVATE="${SGLANG_CONDA_ACTIVATE:-/opt/conda/bin/activate}"
CONDA_ENV="${SGLANG_CONDA_ENV:-task-routing-clean}"
CPU_CORES="${SGLANG_CPU_CORES:-0-3}"
NICE_LEVEL="${SGLANG_NICE_LEVEL:-10}"

mkdir -p "$LOG_DIR" "$(dirname "$PID_FILE")"

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "sglang already running: pid=$OLD_PID"
    echo "log: $LOG_FILE"
    exit 0
  fi
fi

if ! command -v taskset >/dev/null 2>&1; then
  echo "taskset not found; cannot pin CPU cores." >&2
  exit 1
fi

if ! command -v nice >/dev/null 2>&1; then
  echo "nice not found; cannot lower process priority." >&2
  exit 1
fi

if [[ ! -f "$CONDA_ACTIVATE" ]]; then
  echo "conda activate script not found: $CONDA_ACTIVATE" >&2
  exit 1
fi

(
  source "$CONDA_ACTIVATE" "$CONDA_ENV"
  exec nice -n "$NICE_LEVEL" taskset -c "$CPU_CORES" \
    python -m sglang.launch_server \
      --model-path "$MODEL_PATH" \
      --served-model-name "$SERVED_MODEL_NAME" \
      --host "$HOST" \
      --port "$PORT" \
      --api-key "$API_KEY" \
      "$@"
) >>"$LOG_FILE" 2>&1 &

PID=$!
echo "$PID" > "$PID_FILE"

sleep 1
if kill -0 "$PID" 2>/dev/null; then
  echo "sglang started: pid=$PID"
  echo "base_url: http://$HOST:$PORT/v1"
  echo "model: $SERVED_MODEL_NAME"
  echo "log: $LOG_FILE"
  echo "pid file: $PID_FILE"
  exit 0
fi

echo "sglang failed to start; check log: $LOG_FILE" >&2
exit 1
