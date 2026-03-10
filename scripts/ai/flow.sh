#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  cat <<'USAGE'
usage:
  flow.sh <task_id> <action> [notes]

actions:
  impl         -> write impl_done and set next to review
  review_pass  -> write review_pass and set next to break_test
  review_fail  -> write review_fail and set next to impl_fix
  break_pass   -> write break_pass and set next to approved
  break_fail   -> write break_fail and set next to impl_fix
  status       -> print NEXT state from gate.sh
USAGE
  exit 1
fi

task_id="$1"
action="$2"
notes="${3:-}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
handoff="${script_dir}/handoff.sh"
gate="${script_dir}/gate.sh"

case "$action" in
  impl)
    "$handoff" "$task_id" impl impl_done review "$notes"
    ;;
  review_pass)
    "$handoff" "$task_id" review review_pass break_test "$notes"
    ;;
  review_fail)
    "$handoff" "$task_id" review review_fail impl_fix "$notes"
    ;;
  break_pass)
    "$handoff" "$task_id" break_test break_pass approved "$notes"
    ;;
  break_fail)
    "$handoff" "$task_id" break_test break_fail impl_fix "$notes"
    ;;
  status)
    "$gate" "$task_id"
    exit 0
    ;;
  *)
    echo "unknown action: $action" >&2
    exit 1
    ;;
esac

"$gate" "$task_id"
