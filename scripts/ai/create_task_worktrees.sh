#!/usr/bin/env bash
set -euo pipefail

task_id="${1:?usage: create_task_worktrees.sh <task_id> [base_branch]}"
base_branch="${2:-main}"

repo_root="$(git rev-parse --show-toplevel)"
repo_name="$(basename "$repo_root")"
parent_dir="$(dirname "$repo_root")"

impl_branch="codex/${task_id}-impl"
impl_dir="${parent_dir}/${repo_name}-${task_id}-impl"
review_dir="${parent_dir}/${repo_name}-${task_id}-review"
break_dir="${parent_dir}/${repo_name}-${task_id}-break"

echo "creating impl worktree: ${impl_dir} (${impl_branch} from ${base_branch})"
git worktree add "$impl_dir" -b "$impl_branch" "$base_branch"

echo
echo "next:"
echo "1) implement in: ${impl_dir}"
echo "2) after impl commit:"
echo "   commit=\$(git -C \"${impl_dir}\" rev-parse HEAD)"
echo "   git worktree add \"${review_dir}\" --detach \"\$commit\""
echo "   git worktree add \"${break_dir}\" --detach \"\$commit\""
