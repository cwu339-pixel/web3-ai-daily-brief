"""Command-line interface"""
import argparse
import os
from datetime import datetime

from src.scrapers.github_scraper import get_ai_trending, get_web3_trending
from src.analyzer.summarizer import Summarizer
from src.generator.report_builder import ReportBuilder


def main():
    """主命令行入口"""
    parser = argparse.ArgumentParser(
        description="Web3 + AI 每日简报生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s generate              生成今日简报
  %(prog)s generate --ai-only    只生成 AI 简报
  %(prog)s generate --max 10     最多处理 10 个项目
        """
    )

    parser.add_argument(
        "command",
        choices=["generate"],
        help="命令：generate (生成简报)"
    )

    parser.add_argument(
        "--ai-only",
        action="store_true",
        help="只爬取 AI 项目"
    )

    parser.add_argument(
        "--web3-only",
        action="store_true",
        help="只爬取 Web3 项目"
    )

    parser.add_argument(
        "--max",
        type=int,
        default=10,
        help="每类最多处理的项目数（默认 10）"
    )

    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="输出目录（默认 outputs）"
    )

    args = parser.parse_args()

    if args.command == "generate":
        generate_briefing(args)


def generate_briefing(args):
    """生成简报"""
    print("=" * 60)
    print("🚀 Web3 + AI 每日简报生成器")
    print("=" * 60)
    print()

    # 检查 API key
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ 错误：未找到 GEMINI_API_KEY")
        print("请在 .env 文件中配置 API key")
        return

    # Step 1: 爬取 GitHub Trending
    ai_projects = []
    web3_projects = []

    if not args.web3_only:
        print("🤖 正在爬取 GitHub Trending (AI 项目)...")
        ai_projects = get_ai_trending()
        print(f"   ✅ 找到 {len(ai_projects)} 个 AI 相关项目")

    if not args.ai_only:
        print("⛓️  正在爬取 GitHub Trending (Web3 项目)...")
        web3_projects = get_web3_trending()
        print(f"   ✅ 找到 {len(web3_projects)} 个 Web3 相关项目")

    print()

    if not ai_projects and not web3_projects:
        print("⚠️  没有找到相关项目")
        return

    # Step 2: AI 分析
    print("🧠 正在使用 Gemini API 分析项目...")
    summarizer = Summarizer()

    ai_analyzed = []
    if ai_projects:
        print(f"   分析 AI 项目（最多 {args.max} 个）...")
        ai_analyzed = summarizer.batch_summarize(ai_projects, max_items=args.max)
        print(f"   ✅ 完成 {len(ai_analyzed)} 个 AI 项目分析")

    web3_analyzed = []
    if web3_projects:
        print(f"   分析 Web3 项目（最多 {args.max} 个）...")
        web3_analyzed = summarizer.batch_summarize(web3_projects, max_items=args.max)
        print(f"   ✅ 完成 {len(web3_analyzed)} 个 Web3 项目分析")

    print()

    # Step 3: 生成报告
    print("📝 正在生成 Markdown 简报...")
    builder = ReportBuilder(output_dir=args.output_dir)
    filepath = builder.generate_report(
        ai_projects=ai_analyzed,
        web3_projects=web3_analyzed
    )

    print(f"   ✅ 简报已生成：{filepath}")
    print()

    # 显示统计信息
    print("=" * 60)
    print("📊 生成统计")
    print("=" * 60)
    print(f"AI 项目：{len(ai_analyzed)} 个")
    print(f"Web3 项目：{len(web3_analyzed)} 个")
    print(f"输出文件：{filepath}")
    print(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("✨ 完成！可以查看简报了：")
    print(f"   cat {filepath}")
    print()


if __name__ == "__main__":
    main()
