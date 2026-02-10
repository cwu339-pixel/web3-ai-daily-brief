"""Command-line interface"""
import argparse
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.analyzer.summarizer import Summarizer
from src.generator.report_builder import ReportBuilder
from src.models.content_item import ContentItem
from src.scrapers.coindesk_scraper import CoinDeskScraper
from src.scrapers.cointelegraph_scraper import CoinTelegraphScraper
from src.scrapers.hackernews_scraper import HackerNewsScraper
from src.scrapers.reddit_scraper import RedditScraper
from src.scrapers.github_scraper import (
    AI_KEYWORDS,
    WEB3_KEYWORDS,
    GitHubScraper,
)

logger = logging.getLogger(__name__)

AVAILABLE_SOURCES = ("github", "coindesk", "cointelegraph", "reddit", "hackernews")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Web3 + AI 每日简报生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s generate                          生成今日简报（全部数据源）
  %(prog)s generate --sources github         只用 GitHub Trending
  %(prog)s generate --sources coindesk       只用 CoinDesk 新闻
  %(prog)s generate --sources reddit hn      只用 Reddit + HN
  %(prog)s generate --ai-only               只生成 AI 简报
  %(prog)s generate --max 10                 每源最多处理 10 条
        """,
    )

    parser.add_argument(
        "command", choices=["generate"], help="命令：generate (生成简报)"
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=[*AVAILABLE_SOURCES, "all"],
        default=["all"],
        help="选择数据源（默认全部）",
    )
    parser.add_argument(
        "--ai-only", action="store_true", help="只爬取 AI 项目"
    )
    parser.add_argument(
        "--web3-only", action="store_true", help="只爬取 Web3 项目"
    )
    parser.add_argument(
        "--max", type=int, default=10, help="每类最多处理的项目数（默认 10）"
    )
    parser.add_argument(
        "--output-dir", default="outputs", help="输出目录（默认 outputs）"
    )

    args = parser.parse_args()

    if args.command == "generate":
        generate_briefing(args)


def generate_briefing(args):
    """Orchestrate: scrape -> analyze -> report."""
    print("=" * 60)
    print("Web3 + AI 每日简报生成器")
    print("=" * 60)
    print()

    if not os.getenv("GEMINI_API_KEY"):
        print("错误：未找到 GEMINI_API_KEY")
        print("请在 .env 文件中配置 API key")
        return

    sources = (
        list(AVAILABLE_SOURCES)
        if "all" in args.sources
        else list(args.sources)
    )

    all_items = _scrape_all_sources(sources, args)

    if not all_items:
        print("没有找到相关项目或新闻")
        return

    print()
    print(f"正在使用 Gemini API 分析 {len(all_items)} 条内容...")
    summarizer = Summarizer()
    analyzed = summarizer.batch_summarize(all_items, max_items=args.max)
    print(f"   完成 {len(analyzed)} 条内容分析")
    print()

    print("正在生成 Markdown 简报...")
    builder = ReportBuilder(output_dir=args.output_dir)
    filepath = builder.generate_report(items=analyzed)
    print(f"   简报已生成：{filepath}")
    print()

    _print_stats(analyzed, filepath)


def _scrape_all_sources(sources, args):
    """Run all requested scrapers, return combined ContentItem list."""
    all_items = []

    if "github" in sources:
        all_items.extend(_scrape_github(args))

    if "coindesk" in sources:
        all_items.extend(_scrape_rss("CoinDesk", CoinDeskScraper()))

    if "cointelegraph" in sources:
        all_items.extend(_scrape_rss("CoinTelegraph", CoinTelegraphScraper()))

    if "reddit" in sources:
        all_items.extend(_scrape_reddit())

    if "hackernews" in sources:
        all_items.extend(_scrape_hackernews())

    return all_items


def _scrape_reddit():
    """Scrape Reddit r/MachineLearning hot posts."""
    print("正在爬取 Reddit r/MachineLearning...")
    try:
        scraper = RedditScraper(subreddit="MachineLearning", sort="hot")
        items = scraper.fetch(max_items=10)
        print(f"   找到 {len(items)} 条 Reddit 帖子")
        return items
    except Exception as e:
        logger.warning("Failed to fetch Reddit: %s", e)
        print("   Reddit 爬取失败，跳过")
        return []


def _scrape_hackernews():
    """Scrape Hacker News AI-related top stories."""
    print("正在爬取 Hacker News (AI)...")
    try:
        scraper = HackerNewsScraper(min_points=10)
        items = scraper.fetch(max_items=10)
        print(f"   找到 {len(items)} 条 HN 故事")
        return items
    except Exception as e:
        logger.warning("Failed to fetch HackerNews: %s", e)
        print("   Hacker News 爬取失败，跳过")
        return []


def _scrape_github(args):
    """Scrape GitHub Trending with AI/Web3 keyword filtering."""
    items = []
    scraper = GitHubScraper()

    if not args.web3_only:
        print("正在爬取 GitHub Trending (AI 项目)...")
        ai_items = scraper.filter_by_keywords(
            scraper.fetch(since="daily"), AI_KEYWORDS
        )
        print(f"   找到 {len(ai_items)} 个 AI 相关项目")
        items.extend(ai_items)

    if not args.ai_only:
        print("正在爬取 GitHub Trending (Web3 项目)...")
        web3_items = scraper.filter_by_keywords(
            scraper.fetch(since="daily"), WEB3_KEYWORDS
        )
        print(f"   找到 {len(web3_items)} 个 Web3 相关项目")
        items.extend(web3_items)

    return _deduplicate(items)


def _scrape_rss(name, scraper):
    """Scrape an RSS source with error handling."""
    print(f"正在爬取 {name} 新闻...")
    try:
        items = scraper.fetch(max_items=10)
        print(f"   找到 {len(items)} 条 {name} 新闻")
        return items
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", name, e)
        print(f"   {name} 爬取失败，跳过")
        return []


def _deduplicate(items):
    """Remove duplicate ContentItem by URL."""
    seen_urls = set()
    result = []
    for item in items:
        url = item.url if isinstance(item, ContentItem) else item.get("url")
        if url not in seen_urls:
            seen_urls.add(url)
            result.append(item)
    return result


def _print_stats(analyzed, filepath):
    """Print final statistics."""
    source_counts = {}
    for item in analyzed:
        src = item.get("source", "github")
        source_counts = {
            **source_counts,
            src: source_counts.get(src, 0) + 1,
        }

    print("=" * 60)
    print("生成统计")
    print("=" * 60)
    for src, count in source_counts.items():
        print(f"{src}: {count} 条")
    print(f"输出文件：{filepath}")
    print(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


if __name__ == "__main__":
    main()
