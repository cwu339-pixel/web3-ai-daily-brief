#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  cat <<'USAGE'
usage:
  openclaw_review.sh <task_id>

env:
  OPENCLAW_AGENT     default: main
  OPENCLAW_THINKING  default: low
USAGE
  exit 1
fi

task_id="$1"
agent="${OPENCLAW_AGENT:-main}"
thinking="${OPENCLAW_THINKING:-low}"

if ! command -v clawdbot >/dev/null 2>&1; then
  echo "clawdbot not found in PATH" >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(git rev-parse --show-toplevel)"
prompt="$("$script_dir/prompt.sh" "$task_id" review)"
task_file="$repo_root/.ai/tasks/${task_id}.json"
mode="dual"
if [[ -f "$task_file" ]]; then
  mode="$(jq -r '.mode // "dual"' "$task_file" 2>/dev/null || echo dual)"
fi

message=$(cat <<EOF
你是严格代码审查员。只做审查，不要改代码。
仓库路径：${repo_root}
任务ID：${task_id}
模式：${mode}

要求：
- 先读取该仓库与任务相关改动并审查。
- 第一行只能输出 REVIEW_PASS 或 REVIEW_FAIL。
- 如果 FAIL，只列 P1/P2 问题：问题 -> 复现步骤 -> 影响 -> 修复建议。
- 如果 PASS，给一句通过理由。

参考提示：
${prompt}
EOF
)

out_dir="$repo_root/.ai/handoffs/${task_id}"
mkdir -p "$out_dir"
raw_file="$out_dir/openclaw_review_raw.json"
text_file="$out_dir/openclaw_review.txt"

result="$(clawdbot agent --local --agent "$agent" --thinking "$thinking" --message "$message" --json)"
printf "%s\n" "$result" > "$raw_file"

review_text="$(printf "%s\n" "$result" | jq -r '.payloads[0].text // ""')"
printf "%s\n" "$review_text" > "$text_file"

if printf "%s\n" "$review_text" | rg -q '^REVIEW_FAIL'; then
  "$script_dir/flow.sh" "$task_id" review_fail "openclaw review fail"
  echo "OpenClaw verdict: REVIEW_FAIL"
  exit 0
fi

if printf "%s\n" "$review_text" | rg -q '^REVIEW_PASS'; then
  "$script_dir/flow.sh" "$task_id" review_pass "openclaw review pass"
  echo "OpenClaw verdict: REVIEW_PASS"
  exit 0
fi

echo "OpenClaw output missing REVIEW_PASS/REVIEW_FAIL marker." >&2
echo "Please check: $text_file" >&2
exit 2
