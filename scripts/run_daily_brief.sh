#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

OUT_DIR="${OUT_DIR:-$ROOT_DIR/outputs}"
DATE_STAMP="$(date +"%Y-%m-%d")"
LOG_OUT="${LOG_OUT:-$OUT_DIR/launchd_stdout.log}"
LOG_ERR="${LOG_ERR:-$OUT_DIR/launchd_stderr.log}"

mkdir -p "$OUT_DIR"

PYTHON_BIN=""
if [[ -x "$ROOT_DIR/venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/venv/bin/python"
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  PYTHON_BIN="$(command -v python)"
fi

MAX_ITEMS="${MAX_ITEMS:-10}"
SOURCES="${SOURCES:-all}"
MODE="${MODE:-both}" # both | ai-only | web3-only

ARGS=(generate --max "$MAX_ITEMS" --sources "$SOURCES" --output-dir "$OUT_DIR")
if [[ "$MODE" == "ai-only" ]]; then
  ARGS+=(--ai-only)
elif [[ "$MODE" == "web3-only" ]]; then
  ARGS+=(--web3-only)
fi

{
  echo "== web3-ai-daily-brief =="
  echo "timestamp: $(date -Iseconds)"
  echo "date: ${DATE_STAMP}"
  echo "python: ${PYTHON_BIN}"
  echo "args: ${ARGS[*]}"
  echo
  "$PYTHON_BIN" -m src.cli "${ARGS[@]}"
  echo
  echo "done."
} >>"$LOG_OUT" 2>>"$LOG_ERR"

