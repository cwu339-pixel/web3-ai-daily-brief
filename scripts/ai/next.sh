#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  cat <<'USAGE'
usage:
  next.sh <task_id> [--run]

examples:
  ./scripts/ai/next.sh T200
  ./scripts/ai/next.sh T200 --run
USAGE
  exit 1
fi

task_id="$1"
run_mode="${2:-}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
gate="$("$script_dir/gate.sh" "$task_id")"
next="${gate#NEXT=}"

case "$next" in
  impl)
    echo "NEXT=impl"
    echo "Run: ./scripts/ai/flow.sh ${task_id} impl \"impl done\""
    ;;
  review)
    echo "NEXT=review"
    echo "Run: OPENCLAW_AGENT=main ./scripts/ai/openclaw_review.sh ${task_id}"
    if [[ "$run_mode" == "--run" ]]; then
      OPENCLAW_AGENT="${OPENCLAW_AGENT:-main}" "$script_dir/openclaw_review.sh" "$task_id"
    fi
    ;;
  impl_fix)
    echo "NEXT=impl_fix"
    echo "Fix in Codex, then run: ./scripts/ai/flow.sh ${task_id} impl \"fix applied\""
    ;;
  break_test)
    echo "NEXT=break_test"
    echo "Run: ./scripts/ai/flow.sh ${task_id} break_pass \"break test passed\""
    echo "or : ./scripts/ai/flow.sh ${task_id} break_fail \"break test failed\""
    ;;
  approved)
    echo "NEXT=approved"
    echo "Task ${task_id} is ready for next project step."
    ;;
  *)
    echo "NEXT=${next}"
    echo "Check task files under .ai/handoffs/${task_id}/"
    ;;
esac
