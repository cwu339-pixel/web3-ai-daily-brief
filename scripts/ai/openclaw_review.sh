#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  cat <<'USAGE'
usage:
  openclaw_review.sh <task_id>

env:
  OPENCLAW_AGENT     default: main
  OPENCLAW_THINKING  default: low
  OPENCLAW_TIMEOUT   default: 120
  OPENCLAW_MAX_DIFF_CHARS default: 12000
USAGE
  exit 1
fi

task_id="$1"
agent="${OPENCLAW_AGENT:-main}"
thinking="${OPENCLAW_THINKING:-low}"
timeout_seconds="${OPENCLAW_TIMEOUT:-120}"
max_diff_chars="${OPENCLAW_MAX_DIFF_CHARS:-12000}"

if ! command -v clawdbot >/dev/null 2>&1; then
  echo "clawdbot not found in PATH" >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(git rev-parse --show-toplevel)"
prompt="$("$script_dir/prompt.sh" "$task_id" review)"
task_file="$repo_root/.ai/tasks/${task_id}.json"
mode="dual"
base_branch="main"
if [[ -f "$task_file" ]]; then
  mode="$(jq -r '.mode // "dual"' "$task_file" 2>/dev/null || echo dual)"
  base_branch="$(jq -r '.base_branch // "main"' "$task_file" 2>/dev/null || echo main)"
fi

impl_file="$repo_root/.ai/handoffs/${task_id}/impl.json"
impl_commit=""
if [[ -f "$impl_file" ]]; then
  impl_commit="$(jq -r '.commit // ""' "$impl_file" 2>/dev/null || echo "")"
fi

diff_files=""
diff_text=""
if [[ -n "$impl_commit" ]] && git rev-parse --verify "$impl_commit^{commit}" >/dev/null 2>&1; then
  diff_range="${base_branch}...${impl_commit}"
  diff_files="$(git diff --name-only --no-color "$diff_range" | sed -n '1,120p' || true)"
  diff_text="$(git diff --no-color "$diff_range" | LC_ALL=C head -c "$max_diff_chars" || true)"
else
  diff_files="$(git status --short | sed -n '1,120p' || true)"
  diff_text="$(git diff --no-color | LC_ALL=C head -c "$max_diff_chars" || true)"
fi

if [[ -z "$diff_files" ]]; then
  diff_files="(no changed files detected)"
fi
if [[ -z "$diff_text" ]]; then
  diff_text="(no patch content available)"
fi

if [[ "$diff_text" == "(no patch content available)" ]]; then
  "$script_dir/flow.sh" "$task_id" review_fail "openclaw no diff context"
  echo "OpenClaw skipped: no diff context. Auto-marked review_fail."
  exit 0
fi

message=$(cat <<EOF
你是严格代码审查员。只做审查，不要改代码。
仓库路径：${repo_root}
任务ID：${task_id}
模式：${mode}
基线分支：${base_branch}
实现提交：${impl_commit:-unknown}

要求：
- 只审查下面给出的改动上下文，不要讨论其他项目或历史记忆。
- 第一行只能输出 REVIEW_PASS 或 REVIEW_FAIL。
- 如果 FAIL，只列 P1/P2 问题：问题 -> 复现步骤 -> 影响 -> 修复建议。
- 如果 PASS，给一句通过理由。

改动文件：
${diff_files}

改动补丁（截断）：
${diff_text}

参考提示：
${prompt}
EOF
)

out_dir="$repo_root/.ai/handoffs/${task_id}"
mkdir -p "$out_dir"
raw_file="$out_dir/openclaw_review_raw.json"
text_file="$out_dir/openclaw_review.txt"

result="$(clawdbot agent --local --agent "$agent" --thinking "$thinking" --timeout "$timeout_seconds" --message "$message" --json)"
printf "%s\n" "$result" > "$raw_file"

review_text="$(printf "%s\n" "$result" | jq -r '.payloads[0].text // ""')"
printf "%s\n" "$review_text" > "$text_file"

first_line="$(printf "%s\n" "$review_text" | head -n1 | tr -d '\r')"

if [[ "$first_line" == "REVIEW_FAIL" ]]; then
  "$script_dir/flow.sh" "$task_id" review_fail "openclaw review fail"
  echo "OpenClaw verdict: REVIEW_FAIL"
  exit 0
fi

if [[ "$first_line" == "REVIEW_PASS" ]]; then
  "$script_dir/flow.sh" "$task_id" review_pass "openclaw review pass"
  echo "OpenClaw verdict: REVIEW_PASS"
  exit 0
fi

"$script_dir/flow.sh" "$task_id" review_fail "openclaw invalid verdict"
echo "OpenClaw output missing REVIEW_PASS/REVIEW_FAIL marker." >&2
echo "Auto-marked review_fail. Please check: $text_file" >&2
exit 0
