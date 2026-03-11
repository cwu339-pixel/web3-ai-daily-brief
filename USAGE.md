# Usage Guide

这个文件只放“怎么用命令跑”，不重复介绍项目背景。

## 1. 环境准备

```bash
cd ~/Projects/web3-ai-daily-brief
source venv/bin/activate
cp .env.example .env  # 首次需要
```

确保 `.env` 至少有：

```bash
OPENAI_API_KEY=...
```

## 2. 基础日报命令

```bash
# 全量来源（默认）
python -m src.cli generate

# 控制规模
python -m src.cli generate --max 5 --per-source 1

# 只看 AI
python -m src.cli generate --ai-only

# 只看 Web3
python -m src.cli generate --web3-only

# 指定来源
python -m src.cli generate --sources github coindesk theblock
```

## 3. 查看输出

```bash
# 日报（含执行卡）
cat outputs/$(date +%Y-%m-%d)-briefing.md

# 社媒队列
cat outputs/$(date +%Y-%m-%d)-social-queue.json

# 质量成本看板
cat outputs/$(date +%Y-%m-%d)-quality-cost.json
```

滚动文件：

- `outputs/quality_cost_dashboard.json`
- `outputs/event_history.json`

## 4. 每日自动运行（macOS）

```bash
./scripts/install_launchd.sh
```

移除：

```bash
./scripts/uninstall_launchd.sh
```

日志：

- `outputs/launchd_stdout.log`
- `outputs/launchd_stderr.log`

## 5. 手动运行调度脚本

```bash
./scripts/run_daily_brief.sh
```

脚本可调参数（环境变量）：

- `MAX_ITEMS`（默认 5）
- `PER_SOURCE`（默认 1）
- `SOURCES`（默认 all）
- `MODE`：`both | ai-only | web3-only`
- `AUTO_PUSH_TO_SOCIAL_AGENT`（默认 false）
- `OPENAI_RPM`（默认 30）

示例：

```bash
MAX_ITEMS=8 PER_SOURCE=2 MODE=ai-only ./scripts/run_daily_brief.sh
```

## 6. 多 AI 协作流（Codex + OpenClaw）

```bash
# 初始化任务（dual 模式）
./scripts/ai/start.sh T200 medium main

# Codex 实现完成
./scripts/ai/flow.sh T200 impl "impl done"

# 自动进入 OpenClaw 审查（当 NEXT=review）
./scripts/ai/next.sh T200 --run

# 查看当前 gate
./scripts/ai/flow.sh T200 status
```

如果审查建议循环过多，会进入 `human_decision`：

```bash
./scripts/ai/flow.sh T200 human_pass "accept current scope"
# 或
./scripts/ai/flow.sh T200 human_fail "must fix before approve"
```

详细说明：
- `docs/ai_handoff_workflow.md`

## 7. 社媒与视频（可选）

```bash
# 推送队列到 social-media-agent
./scripts/push_to_social_agent.sh

# 视频生成脚本帮助
bash ./scripts/run_generate_youtube_video_v3.sh --help

# YouTube 发布脚本帮助
bash ./scripts/run_youtube_private.sh --help
```

## 8. 测试

```bash
./venv/bin/python -m pytest -q
```
