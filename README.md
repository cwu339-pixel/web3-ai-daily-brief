# Web3 + AI 每日简报生成器

每天早上自动生成 Web3 + AI 领域的精选简报，5 分钟看完当天重要信息。

## 功能特性

- 🤖 自动爬取 GitHub Trending（AI + Web3 项目）
- 📰 聚合 Web3 主流新闻源
- 🧠 使用 Claude API 智能总结和分类
- 📝 生成结构化 Markdown 简报
- ⏰ 支持定时自动运行

## 快速开始

### 安装

```bash
git clone https://github.com/yourusername/web3-ai-daily-brief.git
cd web3-ai-daily-brief
pip install -r requirements.txt
```

### 配置

```bash
# 复制配置文件
cp .env.example .env

# 编辑 .env，添加你的 API keys
# ANTHROPIC_API_KEY=your_key_here
```

### 使用

```bash
# 生成今日简报
python -m src.cli generate

# 查看简报
cat outputs/$(date +%Y-%m-%d)-briefing.md
```

## 项目结构

```
web3-ai-daily-brief/
├── src/
│   ├── scrapers/       # 数据爬取模块
│   ├── analyzer/       # AI 分析模块
│   └── generator/      # 报告生成模块
├── tests/              # 测试文件
├── outputs/            # 生成的简报
└── docs/               # 文档
```

## 开发计划

- [x] 项目结构搭建
- [ ] GitHub Trending 爬虫
- [ ] Claude API 集成
- [ ] Web3 新闻爬虫
- [ ] 报告生成器
- [ ] 自动化部署

## 技术栈

- Python 3.8+
- Anthropic Claude API
- requests + BeautifulSoup
- pytest

## 许可证

MIT License
