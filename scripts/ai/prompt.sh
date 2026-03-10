#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  cat <<'USAGE'
usage:
  prompt.sh <task_id> <impl|review|break_test>

example:
  ./scripts/ai/prompt.sh T200 impl
USAGE
  exit 1
fi

task_id="$1"
role="$2"
task_file=".ai/tasks/${task_id}.json"
mode="triple"

if [[ -f "$task_file" ]]; then
  mode="$(jq -r '.mode // "triple"' "$task_file" 2>/dev/null || echo triple)"
fi

case "$role" in
  impl)
    cat <<EOF
任务 ${task_id}（模式: ${mode}）：
先列将修改的文件，再实现需求并运行测试。
若失败请先自修复再继续。
输出：改动文件、测试结果、剩余风险。
EOF
    ;;
  review)
    cat <<EOF
任务 ${task_id}（模式: ${mode}）：
你只做代码审查，不允许改代码。
只报告 P1/P2 问题，格式：问题 -> 复现步骤 -> 影响 -> 修复建议。
EOF
    ;;
  break_test)
    cat <<EOF
任务 ${task_id}（模式: ${mode}）：
你只做破坏性测试，不允许改代码。
给出边界/异常/权限/性能用例，格式：用例 -> 预期 -> 实际风险。
EOF
    ;;
  *)
    echo "invalid role: $role" >&2
    exit 1
    ;;
esac
