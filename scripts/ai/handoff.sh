#!/usr/bin/env bash
set -euo pipefail

task_id="${1:?usage: handoff.sh <task_id> <role> <status> [next] [notes]}"
role="${2:?role required: impl | review | break_test}"
status="${3:?status required}"
next="${4:-}"
notes="${5:-}"

case "$role" in
  impl|review|break_test) ;;
  *)
    echo "invalid role: $role (expected: impl|review|break_test)" >&2
    exit 1
    ;;
esac

base_dir=".ai/handoffs/${task_id}"
mkdir -p "$base_dir"

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  branch="$(git rev-parse --abbrev-ref HEAD)"
  commit="$(git rev-parse --short HEAD)"
else
  branch=""
  commit=""
fi

timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
output_file="${base_dir}/${role}.json"

jq -n \
  --arg task_id "$task_id" \
  --arg from "$role" \
  --arg status "$status" \
  --arg next "$next" \
  --arg notes "$notes" \
  --arg branch "$branch" \
  --arg commit "$commit" \
  --arg timestamp "$timestamp" \
  '{
    task_id: $task_id,
    from: $from,
    status: $status,
    next: $next,
    notes: $notes,
    branch: $branch,
    commit: $commit,
    timestamp: $timestamp
  }' > "$output_file"

echo "handoff written: $output_file"
