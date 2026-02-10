"""测试完整流程：爬取 + AI 总结

注意：这是一个可手动运行的 demo 脚本，不应被 pytest 在收集阶段导入执行。
"""
import os
import sys

def main() -> int:
    # 检查是否有 API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_key_here":
        print("❌ 请先在 .env 文件中设置 GEMINI_API_KEY")
        print("\n获取 API key:")
        print("1. 访问 https://aistudio.google.com/apikey")
        print("2. 创建账号并获取 API key")
        print("3. 编辑 .env 文件，替换 'your_key_here' 为你的 API key")
        return 1

    from src.scrapers.github_scraper import get_ai_trending
    from src.analyzer.summarizer import Summarizer

    print("🤖 正在爬取 GitHub Trending（AI 项目）...")
    projects = get_ai_trending()
    print(f"✅ 找到 {len(projects)} 个 AI 相关项目\n")

    if not projects:
        print("⚠️  今天没有找到 AI 相关项目")
        return 0

    print("🧠 正在使用 Gemini API 分析项目（只分析前 3 个）...\n")
    summarizer = Summarizer()

    for i, project in enumerate(projects[:3], 1):
        print(f"\n{'='*60}")
        print(f"项目 {i}: {project['repo_name']}")
        print(f"原始描述：{project['description'][:80]}...")

        result = summarizer.summarize_project(project)

        print(f"\n📝 AI 总结：{result['summary']}")
        print(f"🏷️  分类：{result['category']}")
        print(f"⭐ 重要性：{result['importance']}/10")
        print(f"🔗 链接：{result['url']}")

    print("\n\n✅ 测试完成！AI 总结功能正常工作。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
