#!/usr/bin/env bash
set -euo pipefail

task_id="${1:?usage: gate.sh <task_id>}"
base_dir=".ai/handoffs/${task_id}"
task_file=".ai/tasks/${task_id}.json"

read_status() {
  local file="$1"
  if [[ -f "$file" ]]; then
    jq -r '.status // "missing"' "$file"
  else
    echo "missing"
  fi
}

read_mode() {
  if [[ -f "$task_file" ]]; then
    local m
    m="$(jq -r '.mode // "triple"' "$task_file" 2>/dev/null || echo triple)"
    case "$m" in
      single|dual|triple) echo "$m" ;;
      *) echo "triple" ;;
    esac
  else
    echo "triple"
  fi
}

impl_status="$(read_status "${base_dir}/impl.json")"
review_status="$(read_status "${base_dir}/review.json")"
break_status="$(read_status "${base_dir}/break_test.json")"
mode="$(read_mode)"

if [[ "$impl_status" != "impl_done" ]]; then
  echo "NEXT=impl"
  exit 0
fi

if [[ "$mode" == "single" ]]; then
  echo "NEXT=approved"
  exit 0
fi

if [[ "$review_status" == "review_fail" || "$break_status" == "break_fail" ]]; then
  echo "NEXT=impl_fix"
  exit 0
fi

if [[ "$review_status" == "missing" ]]; then
  echo "NEXT=review"
  exit 0
fi

if [[ "$mode" == "dual" ]]; then
  if [[ "$review_status" == "review_pass" ]]; then
    echo "NEXT=approved"
    exit 0
  fi
  echo "NEXT=waiting"
  exit 0
fi

if [[ "$break_status" == "missing" ]]; then
  echo "NEXT=break_test"
  exit 0
fi

if [[ "$review_status" == "review_pass" && "$break_status" == "break_pass" ]]; then
  echo "NEXT=approved"
  exit 0
fi

echo "NEXT=waiting"
