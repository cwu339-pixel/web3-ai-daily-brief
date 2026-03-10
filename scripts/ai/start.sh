#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  cat <<'USAGE'
usage:
  start.sh <task_id> [small|medium|large|single|dual|triple] [base_branch]

mapping:
  small  -> single (仅实现)
  medium -> dual   (实现 + review)
  large  -> triple (实现 + review + break_test)

examples:
  ./scripts/ai/start.sh T200 medium main
  ./scripts/ai/start.sh T201 large
USAGE
  exit 1
fi

task_id="$1"
size="${2:-medium}"
base_branch="${3:-main}"

case "$size" in
  small) mode="single" ;;
  medium) mode="dual" ;;
  large) mode="triple" ;;
  single|dual|triple) mode="$size" ;;
  *)
    echo "invalid size/mode: $size" >&2
    exit 1
    ;;
esac

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(git rev-parse --show-toplevel)"
repo_name="$(basename "$repo_root")"
parent_dir="$(dirname "$repo_root")"

mkdir -p "$repo_root/.ai/tasks" "$repo_root/.ai/handoffs/$task_id"

task_file="$repo_root/.ai/tasks/${task_id}.json"
created_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

jq -n \
  --arg task_id "$task_id" \
  --arg size "$size" \
  --arg mode "$mode" \
  --arg base_branch "$base_branch" \
  --arg created_at "$created_at" \
  '{
    task_id: $task_id,
    size: $size,
    mode: $mode,
    base_branch: $base_branch,
    created_at: $created_at
  }' > "$task_file"

create_worktree="${CREATE_WORKTREE:-true}"
impl_branch="codex/${task_id}-impl"
impl_dir="${parent_dir}/${repo_name}-${task_id}-impl"
if [[ "$create_worktree" == "true" ]]; then
  if git show-ref --verify --quiet "refs/heads/$impl_branch"; then
    echo "worktree skipped: branch already exists ($impl_branch)"
  elif [[ -d "$impl_dir" ]]; then
    echo "worktree skipped: dir already exists ($impl_dir)"
  else
    "$script_dir/create_task_worktrees.sh" "$task_id" "$base_branch"
  fi
else
  echo "worktree creation skipped (CREATE_WORKTREE=false)"
fi

echo
echo "task initialized: $task_id"
echo "mode: $mode (from: $size)"
echo "task file: .ai/tasks/${task_id}.json"
echo
echo "next steps:"
echo "1) AI 实现: ./scripts/ai/flow.sh ${task_id} impl \"impl done\""
if [[ "$mode" == "dual" || "$mode" == "triple" ]]; then
  echo "2) OpenClaw 审查: OPENCLAW_AGENT=main ./scripts/ai/openclaw_review.sh ${task_id}"
fi
if [[ "$mode" == "triple" ]]; then
  echo "3) AI 破坏测试: ./scripts/ai/flow.sh ${task_id} break_pass \"break pass\""
fi
echo "4) 查询状态: ./scripts/ai/flow.sh ${task_id} status"
echo "5) 自动下一步: ./scripts/ai/next.sh ${task_id} [--run]"
