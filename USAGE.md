# 使用指南

## 📖 快速开始

### 第一次使用

```bash
# 1. 进入项目目录
cd ~/Projects/web3-ai-daily-brief

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 确保 .env 配置正确
cat .env
# 应该看到：OPENAI_API_KEY=sk-...

# 4. 生成第一份简报
python -m src.cli generate --max 3

# 5. 查看简报
cat outputs/$(date +%Y-%m-%d)-briefing.md
```

## 📝 常用命令

### 基础使用

```bash
# 生成今日简报（默认每类最多 10 个项目）
python -m src.cli generate

# 限制项目数量（节省 API 调用）
python -m src.cli generate --max 5

# 只生成 AI 简报
python -m src.cli generate --ai-only

# 只生成 Web3 简报
python -m src.cli generate --web3-only
```

### 查看简报

```bash
# 查看今天的简报
cat outputs/$(date +%Y-%m-%d)-briefing.md

# 用 Markdown 阅读器打开（macOS）
open outputs/$(date +%Y-%m-%d)-briefing.md

# 列出所有简报
ls -lh outputs/
```

## ⏰ 设置每日自动运行

### 方式 1：使用 cron（推荐）

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天早上 8:00 运行）
0 8 * * * cd ~/Projects/web3-ai-daily-brief && source venv/bin/activate && python -m src.cli generate --max 10
```

### 方式 2：使用 GitHub Actions

在项目中创建 `.github/workflows/daily-brief.yml`：

```yaml
name: Generate Daily Brief

on:
  schedule:
    - cron: '0 0 * * *'  # 每天 UTC 0:00
  workflow_dispatch:  # 手动触发

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.8'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Generate brief
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: python -m src.cli generate

      - name: Commit report
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add outputs/
          git commit -m "Add daily brief $(date +%Y-%m-%d)" || exit 0
          git push
```

## 🔧 进阶配置

### API 调用优化

```bash
# 如果 API 配额有限，减少处理数量
python -m src.cli generate --max 3

# 只关注 AI 领域
python -m src.cli generate --ai-only --max 5
```

### 自定义关键词（编辑源码）

编辑 `src/scrapers/github_scraper.py`：

```python
# 修改 AI 关键词
ai_keywords = [
    "AI", "LLM", "GPT",  # 保留这些
    "your-custom-keyword"  # 添加你的关键词
]

# 修改 Web3 关键词
web3_keywords = [
    "blockchain", "web3",  # 保留这些
    "your-web3-keyword"    # 添加你的关键词
]
```

## 📊 查看历史简报

```bash
# 查看某一天的简报
cat outputs/2026-02-05-briefing.md

# 搜索包含特定关键词的简报
grep -r "OpenAI" outputs/

# 统计简报数量
ls -1 outputs/*.md | wc -l
```

## 🐛 故障排查

### 问题 1：API key 无效

```bash
# 检查 .env 文件
cat .env

# 测试 API key
python << EOF
from openai import OpenAI
client = OpenAI(api_key="你的key")
models = client.models.list()
print(f"API key 有效！可见模型数: {len(models.data)}")
EOF
```

### 问题 2：没有爬取到项目

```bash
# 可能是网络问题，尝试重新运行
python -m src.cli generate

# 或者检查 GitHub 是否可访问
curl -I https://github.com/trending
```

### 问题 3：OpenAI API 配额用完

```bash
# 减少每次处理的项目数
python -m src.cli generate --max 3

# 或者升级 API plan
# 访问 https://platform.openai.com/usage
```

## 💡 最佳实践

### 1. 定期查看简报

```bash
# 添加到你的晨间脚本
echo "alias daily='cat ~/Projects/web3-ai-daily-brief/outputs/\$(date +%Y-%m-%d)-briefing.md'" >> ~/.zshrc
source ~/.zshrc

# 然后每天只需运行
daily
```

### 2. 导出为 PDF

```bash
# 安装 pandoc
brew install pandoc  # macOS
sudo apt install pandoc  # Ubuntu

# 转换为 PDF
pandoc outputs/2026-02-05-briefing.md -o briefing.pdf
```

### 3. 分享到团队

```bash
# 生成简报后自动发送到 Slack（需要配置 webhook）
python -m src.cli generate && \
curl -X POST -H 'Content-type: application/json' \
  --data "{\"text\":\"今日简报已生成：$(cat outputs/$(date +%Y-%m-%d)-briefing.md)\"}" \
  YOUR_SLACK_WEBHOOK_URL
```

## 📈 使用统计

```bash
# 查看生成的简报数量
ls -1 outputs/*.md | wc -l

# 查看最近 7 天的简报
ls -lt outputs/*.md | head -7

# 统计总共分析了多少项目
grep -h "GitHub Trending" outputs/*.md | \
  grep -o "[0-9]* 个相关项目" | \
  awk '{sum+=$1} END {print sum " 个项目"}'
```

## 🎓 学习资源

- [OpenAI API 文档](https://platform.openai.com/docs/overview)
- [BeautifulSoup 教程](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [GitHub Trending 算法](https://github.com/trending)

---

**遇到问题？**
- 提交 Issue：https://github.com/yourusername/web3-ai-daily-brief/issues
- 查看示例：`examples/` 目录下的测试脚本
