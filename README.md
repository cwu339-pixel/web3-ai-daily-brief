# Web3 + AI 每日简报生成器

每天早上自动生成 Web3 + AI 领域的精选简报，5 分钟看完当天重要信息。

## ✨ 功能特性

- 🤖 自动爬取 GitHub Trending（AI + Web3 项目）
- 📰 抓取 CoinDesk / CoinTelegraph 最新 Web3 新闻
- 💬 聚合 Reddit r/MachineLearning 热门讨论
- 🔥 获取 Hacker News AI 相关高分故事
- 🧠 使用 Google Gemini AI 智能总结和分类
- 📝 生成精美的 Markdown 格式简报
- ⭐ 自动评估项目重要性（1-10 分）
- 🏷️ 智能分类（AI技术/Web3技术/开发工具/其他）
- ⏰ 支持定时自动运行（launchd）

## 📸 效果预览

```markdown
# Web3 + AI 每日简报 | 2026-02-05

## 🤖 AI 技术进展

### AI技术

**⭐⭐⭐⭐ [bytedance/UI-TARS-desktop](https://github.com/bytedance/UI-TARS-desktop)**

- 📝 **总结**：开源多模态AI智能体堆栈，连接尖端AI模型与基础设施。
- 🔧 **语言**：TypeScript
- 🌟 **今日 Stars**：862
```

## 🚀 快速开始

### 1. 安装

```bash
git clone https://github.com/cwu339-pixel/web3-ai-daily-brief.git
cd web3-ai-daily-brief

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
# 复制配置文件
cp .env.example .env

# 编辑 .env，添加你的 Gemini API key
# GEMINI_API_KEY=your_gemini_api_key_here
```

**获取 Gemini API Key：**
1. 访问 https://aistudio.google.com/apikey
2. 登录 Google 账号
3. 创建 API key
4. 复制到 `.env` 文件

### 3. 使用

```bash
# 生成今日简报
python -m src.cli generate

# 只生成 AI 简报
python -m src.cli generate --ai-only

# 限制项目数量
python -m src.cli generate --max 5

# 查看生成的简报
cat outputs/$(date +%Y-%m-%d)-briefing.md
```

## 📁 项目结构

```
web3-ai-daily-brief/
├── src/
│   ├── scrapers/                    # 数据爬取模块
│   │   ├── base_scraper.py          # 抽象基类
│   │   ├── github_scraper.py        # GitHub Trending 爬虫
│   │   ├── coindesk_scraper.py      # CoinDesk RSS 新闻
│   │   ├── cointelegraph_scraper.py # CoinTelegraph RSS 新闻
│   │   ├── reddit_scraper.py        # Reddit 子版块爬虫
│   │   ├── hackernews_scraper.py    # Hacker News AI 故事
│   │   ├── rss_scraper.py           # RSS 通用基类
│   │   └── market_scraper.py        # 市场数据
│   ├── analyzer/                    # AI 分析模块
│   │   ├── summarizer.py            # Gemini API 总结器
│   │   └── prompt_templates.py      # Prompt 模板
│   ├── generator/                   # 报告生成模块
│   │   └── report_builder.py        # Markdown 报告生成
│   ├── models/                      # 数据模型
│   │   └── content_item.py          # 统一内容模型
│   └── cli.py                       # 命令行工具
├── scripts/                         # 运行脚本
│   ├── run_daily_brief.sh           # 每日执行脚本
│   ├── install_launchd.sh           # macOS 定时任务安装
│   └── uninstall_launchd.sh         # 定时任务卸载
├── launchd/                         # macOS launchd 配置
├── tests/                           # 测试文件
├── outputs/                         # 生成的简报
│   └── YYYY-MM-DD-briefing.md
├── examples/                        # 示例脚本
└── .env                             # 配置文件（需自己创建）
```

## 🎯 使用场景

1. **每日晨读** - 早上 5 分钟了解最新技术动态
2. **技术跟踪** - 持续关注 AI 和 Web3 领域进展
3. **项目发现** - 发现有潜力的开源项目
4. **投资研究** - Web3 项目投资参考

## 🛠️ 开发

### 运行测试

```bash
# 运行所有测试
pytest tests/

# 查看覆盖率
pytest --cov=src tests/
```

### 代码风格

```bash
# 格式化代码
black src/ tests/

# 检查代码风格
flake8 src/ tests/
```

## 📅 开发计划

### ✅ MVP 已完成（v0.1.0）
- [x] 项目结构搭建
- [x] GitHub Trending 爬虫
- [x] Gemini API 集成
- [x] 报告生成器
- [x] CLI 工具
- [x] 端到端测试

### ✅ v0.2.0 已完成
- [x] CoinDesk RSS 新闻爬虫
- [x] CoinTelegraph RSS 新闻爬虫
- [x] Reddit r/MachineLearning 爬虫
- [x] Hacker News AI 故事爬虫
- [x] 统一内容模型（ContentItem）
- [x] macOS launchd 定时自动运行

### 🔜 下一步计划（v0.3.0）
- [ ] 邮件推送功能
- [ ] GitHub Actions 自动运行
- [ ] Web UI 界面

### 💡 未来功能
- [ ] Telegram Bot 订阅
- [ ] 关键词订阅（只看特定话题）
- [ ] 周报/月报汇总
- [ ] 历史数据分析
- [ ] 趋势预测

## 🧪 技术栈

- **语言**：Python 3.8+
- **AI**：Google Gemini 2.5 Flash
- **爬虫**：requests + BeautifulSoup + feedparser
- **测试**：pytest
- **格式化**：black + flake8

## 📊 数据来源

| 来源 | 类型 | 状态 |
|------|------|------|
| GitHub Trending | AI + Web3 开源项目 | ✅ 已支持 |
| CoinDesk | Web3 新闻（RSS） | ✅ 已支持 |
| CoinTelegraph | Web3 新闻（RSS） | ✅ 已支持 |
| Reddit r/MachineLearning | AI 社区讨论 | ✅ 已支持 |
| Hacker News | AI 高分故事 | ✅ 已支持 |

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

**贡献指南：**
1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交代码 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

## 📝 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [GitHub Trending](https://github.com/trending) - 项目数据来源
- [Google Gemini](https://ai.google.dev/) - AI 分析能力
- [CoinDesk](https://www.coindesk.com) / [CoinTelegraph](https://cointelegraph.com) - Web3 新闻
- [Reddit r/MachineLearning](https://www.reddit.com/r/MachineLearning/) - AI 社区讨论
- [Hacker News](https://news.ycombinator.com) - 技术社区故事
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) - HTML 解析
- [feedparser](https://feedparser.readthedocs.io/) - RSS 解析

## 📧 联系方式

有问题或建议？欢迎：
- 提交 [Issue](https://github.com/cwu339-pixel/web3-ai-daily-brief/issues)

---

⭐ 如果这个项目对你有帮助，欢迎 Star！
