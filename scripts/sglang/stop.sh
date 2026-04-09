#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PID_FILE="${SGLANG_PID_FILE:-$ROOT_DIR/var/sglang.pid}"
GRACE_SEC="${SGLANG_STOP_GRACE_SEC:-8}"

if [[ ! -f "$PID_FILE" ]]; then
  echo "pid file not found: $PID_FILE"
  exit 0
fi

PID="$(cat "$PID_FILE" 2>/dev/null || true)"
if [[ -z "$PID" ]]; then
  echo "pid file is empty: $PID_FILE"
  rm -f "$PID_FILE"
  exit 0
fi

if ! kill -0 "$PID" 2>/dev/null; then
  echo "process already stopped: pid=$PID"
  rm -f "$PID_FILE"
  exit 0
fi

echo "stopping sglang pid=$PID"
kill "$PID" 2>/dev/null || true

for _ in $(seq 1 "$GRACE_SEC"); do
  if ! kill -0 "$PID" 2>/dev/null; then
    rm -f "$PID_FILE"
    echo "sglang stopped"
    exit 0
  fi
  sleep 1
done

echo "force killing sglang pid=$PID"
kill -9 "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
echo "sglang stopped (forced)"
