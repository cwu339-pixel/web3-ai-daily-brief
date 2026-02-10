#!/bin/bash

# Web3 AI Daily Brief - GitHub 上传脚本
# 自动化完成所有 GitHub 上传步骤

set -e  # 遇到错误立即停止

echo "🚀 Web3 AI Daily Brief - GitHub 上传助手"
echo "=========================================="
echo ""

# 检查是否在正确的目录
if [ ! -f "README.md" ]; then
    echo "❌ 错误：请在 web3-ai-daily-brief 项目目录下运行此脚本"
    exit 1
fi

# 获取 GitHub 用户名
echo "📝 第1步：获取你的 GitHub 用户名"
echo ""
read -p "请输入你的 GitHub 用户名: " GITHUB_USERNAME

if [ -z "$GITHUB_USERNAME" ]; then
    echo "❌ 用户名不能为空"
    exit 1
fi

echo ""
echo "✅ GitHub 用户名: $GITHUB_USERNAME"
echo ""

# 提交所有更改
echo "📦 第2步：提交所有代码更改"
echo ""
git add .
git commit -m "feat: AI-powered daily brief for Web3 and AI technologies

- Automated GitHub Trending scraper for AI and Web3 projects
- Google Gemini AI integration for intelligent summarization
- Daily briefing generator with importance ratings
- Designed for investment banking tech tracking" || echo "⚠️  没有新的更改需要提交（或已经提交过）"

echo ""
echo "✅ 代码已提交"
echo ""

# 检查是否已经有远程仓库
if git remote | grep -q "origin"; then
    echo "⚠️  检测到已存在的 origin 远程仓库，正在移除..."
    git remote remove origin
fi

# 添加 GitHub 远程仓库
echo "🔗 第3步：连接到 GitHub 仓库"
echo ""
REPO_URL="https://github.com/$GITHUB_USERNAME/web3-ai-daily-brief.git"
git remote add origin $REPO_URL

echo "✅ 已添加远程仓库: $REPO_URL"
echo ""

# 推送到 GitHub
echo "⬆️  第4步：推送代码到 GitHub"
echo ""
echo "⏳ 正在推送代码..."
echo ""

if git push -u origin main; then
    echo ""
    echo "=========================================="
    echo "🎉 成功！代码已上传到 GitHub！"
    echo "=========================================="
    echo ""
    echo "📍 你的 GitHub 仓库地址："
    echo "   https://github.com/$GITHUB_USERNAME/web3-ai-daily-brief"
    echo ""
    echo "🔍 下一步："
    echo "   1. 访问上面的链接查看你的项目"
    echo "   2. 确认 README 显示正常"
    echo "   3. 复制链接，准备发送给 Joey"
    echo ""
    echo "📧 邮件模板已准备好，位于："
    echo "   ~/Projects/outputs/email_to_joey.md"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "⚠️  推送失败"
    echo "=========================================="
    echo ""
    echo "可能的原因："
    echo "  1. 仓库还未在 GitHub 上创建"
    echo "     👉 访问: https://github.com/new"
    echo "     👉 仓库名: web3-ai-daily-brief"
    echo "     👉 设为 Public"
    echo "     👉 不要勾选 'Initialize with README'"
    echo ""
    echo "  2. GitHub 认证问题"
    echo "     👉 第一次推送需要输入 GitHub 用户名和密码"
    echo "     👉 密码应使用 Personal Access Token"
    echo "     👉 创建 Token: https://github.com/settings/tokens"
    echo ""
    echo "  3. 权限问题"
    echo "     👉 确保你有该仓库的写权限"
    echo ""
    echo "修复后，再次运行此脚本即可"
fi
