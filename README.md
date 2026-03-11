# web3-ai-daily-brief

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Local-First](https://img.shields.io/badge/deployment-local--first-0ea5e9)](#)
[![Pipeline](https://img.shields.io/badge/pipeline-daily%20briefing-10b981)](#)
[![AI%20Review](https://img.shields.io/badge/ai%20review-codex%20%2B%20openclaw-f59e0b)](#)

本地优先的 AI/Web3 每日情报流水线：
抓取多源信号 -> 事件去重 -> OpenAI 分析 -> 生成可执行日报与发布队列。

## 项目定位

这不是“新闻聚合器”，而是一个可以每天稳定产出 **执行卡** 的研究/内容系统。

核心输出：
- 每日简报（Markdown）
- 社媒发布队列（JSON）
- 质量与成本看板（JSON/Markdown）
- 事件历史与 3/7 天趋势跟踪

## 5 分钟体验路径

```bash
python -m src.cli generate --max 5 --per-source 1
cat outputs/$(date +%Y-%m-%d)-briefing.md
cat outputs/$(date +%Y-%m-%d)-quality-cost.json
```

你会立刻看到三类结果：`简报`、`执行卡`、`质量成本看板`。

## 现在有什么能力

- 多源抓取：GitHub、CoinDesk、CoinTelegraph、The Block、Blockworks、Reddit、Hacker News、OpenAI Blog、DeepMind Blog、DefiLlama（以及可选 Telegram/Bilibili）
- 事件级去重：同一事件多来源合并，减少重复噪音
- AI 结构化分析：每条信号输出 `summary/category/importance` + 执行字段
- 执行卡输出：`action_item/owner/deadline/execution_risk/expected_gain`
- 每日质量成本看板：成功率、耗时、token、失败原因、估算费用
- 本地多 AI 协作流（Codex + OpenClaw）：建议回合、上限门禁、人工仲裁、决议留痕

## 快速开始

### 1) 安装

```bash
git clone https://github.com/cwu339-pixel/web3-ai-daily-brief.git
cd web3-ai-daily-brief
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2) 配置

```bash
cp .env.example .env
# 至少配置：OPENAI_API_KEY
```

### 3) 生成今天日报

```bash
python -m src.cli generate
```

常用参数：

```bash
python -m src.cli generate --max 5 --per-source 1
python -m src.cli generate --ai-only
python -m src.cli generate --web3-only
python -m src.cli generate --sources github coindesk theblock
```

## 输出文件

每次运行默认在 `outputs/` 生成：

- `YYYY-MM-DD-briefing.md`：每日简报（含执行卡）
- `YYYY-MM-DD-social-queue.json`：社媒队列
- `YYYY-MM-DD-quality-cost.json`：当日质量/成本看板
- `YYYY-MM-DD-quality-cost.md`：看板 Markdown 版
- `quality_cost_dashboard.json`：滚动看板（近 60 次）
- `event_history.json`：事件历史（用于 3/7 天趋势）

快速查看：

```bash
cat outputs/$(date +%Y-%m-%d)-briefing.md
cat outputs/$(date +%Y-%m-%d)-quality-cost.json
```

## 每日定时运行（macOS）

```bash
./scripts/install_launchd.sh
# 卸载
./scripts/uninstall_launchd.sh
```

默认每天本地时间 09:00 执行，日志在：

- `outputs/launchd_stdout.log`
- `outputs/launchd_stderr.log`

你也可以直接跑脚本：

```bash
./scripts/run_daily_brief.sh
```

可用环境变量（脚本层）：

- `MAX_ITEMS`（默认 5）
- `PER_SOURCE`（默认 1）
- `SOURCES`（默认 all）
- `MODE`（`both`/`ai-only`/`web3-only`）
- `AUTO_PUSH_TO_SOCIAL_AGENT`（默认 false）

## 多 AI 协作（Codex + OpenClaw）

最小闭环（双工具）：

```bash
./scripts/ai/start.sh T300 medium main
./scripts/ai/flow.sh T300 impl "v1 implemented"
./scripts/ai/next.sh T300 --run
```

这套流支持：

- 审查建议回合：`review_suggest -> impl_reply`
- 回合上限：超限后进入 `human_decision`
- 人工仲裁：`human_pass` / `human_fail`
- 决议留痕：`.ai/handoffs/<task_id>/history.jsonl` 与 `decisions.jsonl`

完整说明见：
- [docs/ai_handoff_workflow.md](docs/ai_handoff_workflow.md)

## 可选扩展

- 推送到社媒代理：`./scripts/push_to_social_agent.sh`
- 短视频生成与发布：`scripts/run_generate_youtube_*.sh`、`scripts/run_youtube_*.sh`
- 多平台内容编排：`python scripts/social_pipeline.py --help`

## 最新能力更新

- 协商闭环新增回合上限，避免 `review_suggest -> impl_reply` 无限循环
- 超过回合上限自动进入 `human_decision`，支持人工仲裁
- 每条分析结果升级为执行卡字段（动作/负责人/截止/风险/收益）
- 每次运行自动写质量成本看板（成功率、耗时、token、失败原因）
- 事件级去重 + 3/7 天连续趋势跟踪

## 测试

```bash
./venv/bin/python -m pytest -q
```

## 目录结构

```text
web3-ai-daily-brief/
├── src/
│   ├── cli.py
│   ├── analyzer/         # Summarizer + Event Tracker
│   ├── scrapers/         # 多源抓取
│   ├── generator/        # 简报/队列生成
│   └── social/           # 多平台策略与调度
├── scripts/
│   ├── run_daily_brief.sh
│   ├── ai/               # 本地多 AI 协作脚本
│   └── ...
├── docs/
├── tests/
└── outputs/
```

## 备注

- 成本估算默认关闭；若要启用，请在 `.env` 里配置：
  - `OPENAI_INPUT_COST_PER_1M`
  - `OPENAI_OUTPUT_COST_PER_1M`
- 该仓库当前为本地工作流优先，适合个人或小团队日更研究/内容场景。
