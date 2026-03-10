#!/usr/bin/env bash
set -euo pipefail

handoff_root=".ai/handoffs"
last_file=""

notify() {
  local title="$1"
  local msg="$2"

  echo "[notify] ${title}: ${msg}"

  if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"${msg}\" with title \"${title}\"" >/dev/null
  fi
}

while true; do
  latest_file="$(ls -t "${handoff_root}"/*/impl.json 2>/dev/null | head -n1 || true)"
  if [[ -n "$latest_file" && "$latest_file" != "$last_file" ]]; then
    task_id="$(basename "$(dirname "$latest_file")")"
    status="$(jq -r '.status // "unknown"' "$latest_file" 2>/dev/null || echo unknown)"
    if [[ "$status" == "impl_done" ]]; then
      notify "AI Handoff" "${task_id} ready for review"
    fi
    last_file="$latest_file"
  fi
  sleep 2
done
