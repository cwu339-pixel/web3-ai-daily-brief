# web3-ai-daily-brief

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Pipeline](https://img.shields.io/badge/pipeline-daily%20briefing-10b981)](#)

一个本地优先的 Web3/AI 每日情报系统。  
目标不是“搬运新闻”，而是每天产出可读、可复用的结论：**判断 / 影响 / 风险**。

## 1. 这个项目做什么

每日自动执行一条流水线：

1. 多源抓取（新闻、链上、开发者生态）
2. 事件去重（同一事件合并）
3. AI 结构化分析（每条信号输出判断/影响/风险）
4. 生成日报、社媒队列、质量成本看板

## 2. 5 分钟跑起来

### 安装

```bash
git clone https://github.com/cwu339-pixel/web3-ai-daily-brief.git
cd web3-ai-daily-brief
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 配置

```bash
cp .env.example .env
# 必填：OPENAI_API_KEY
```

### 运行

```bash
python -m src.cli generate --max 12 --per-source 2
```

## 3. 你会得到什么输出

默认都在 `outputs/`：

- `YYYY-MM-DD-briefing.md`：日报正文
- `YYYY-MM-DD-social-queue.json`：可发布内容队列
- `YYYY-MM-DD-digest.md` / `YYYY-MM-DD-digest.json`：编辑摘要
- `YYYY-MM-DD-distribution-drafts.json`：分发草稿（X/LinkedIn/Newsletter）
- `YYYY-MM-DD-quality-cost.json`：质量/成本数据
- `quality_cost_dashboard.json`：滚动质量看板
- `event_history.json`：事件历史（3/7天趋势）

快速看当天内容：

```bash
cat outputs/$(date +%Y-%m-%d)-digest.md
cat outputs/$(date +%Y-%m-%d)-social-queue.json
```

## 4. 常用命令

只跑部分来源：

```bash
python -m src.cli generate --sources github coindesk theblock
```

限制样本规模：

```bash
python -m src.cli generate --max 8 --per-source 1
```

只看 AI / 只看 Web3：

```bash
python -m src.cli generate --ai-only
python -m src.cli generate --web3-only
```

## 5. 目前支持的数据源

- GitHub
- X（Nitter RSS）
- CoinDesk
- CoinTelegraph
- The Block
- Blockworks
- OpenAI Blog
- DeepMind Blog
- Reddit
- Hacker News
- DefiLlama
- 可选：Telegram / Bilibili

说明：某些源在网络波动时会偶发失败，系统会跳过并继续产出。

## 6. 前端预览

```bash
python3 -m http.server 8000
# 浏览器打开 http://localhost:8000/web/
```

相关文件：

- `web/index.html`
- `web/styles.css`
- `web/app.js`

## 7. 定时运行（macOS）

```bash
./scripts/install_launchd.sh
# 卸载
./scripts/uninstall_launchd.sh
```

手动跑一次：

```bash
./scripts/run_daily_brief.sh
```

## 8. 项目定位（面试可用）

一句话：

> 我在做一个 Web3/AI 的 daily brief 引擎，把多源新闻和信号稳定转成“判断-影响-风险”，并自动输出日报与分发草稿。

## 9. 进阶文档

- `USAGE.md`：完整 CLI 用法
- `docs/daily_ops_sop.md`：每日执行 SOP
- `docs/ai_handoff_workflow.md`：Codex + OpenClaw 协作流
- `docs/agency_agents_integration.md`：Agent 协同说明

