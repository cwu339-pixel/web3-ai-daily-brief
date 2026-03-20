"""Command-line interface."""
import argparse
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file.
load_dotenv()

from src.analyzer.event_tracker import (
    EventTracker,
    canonicalize_url,
    deduplicate_items_by_event,
)
from src.analyzer.summarizer import Summarizer
from src.generator.report_builder import ReportBuilder
from src.models.content_item import ContentItem
from src.scrapers.blockworks_scraper import BlockworksScraper
from src.scrapers.coindesk_scraper import CoinDeskScraper
from src.scrapers.cointelegraph_scraper import CoinTelegraphScraper
from src.scrapers.deepmind_blog_scraper import DeepMindBlogScraper
from src.scrapers.defillama_scraper import DefiLlamaScraper
from src.scrapers.github_scraper import AI_KEYWORDS, WEB3_KEYWORDS, GitHubScraper
from src.scrapers.hackernews_scraper import HackerNewsScraper
from src.scrapers.openai_blog_scraper import OpenAIBlogScraper
from src.scrapers.reddit_scraper import RedditScraper
from src.scrapers.rwa_analytics_scraper import RWAAnalyticsScraper
from src.scrapers.rwa_protocol_scraper import RWAProtocolScraper
from src.scrapers.theblock_scraper import TheBlockScraper
from src.scrapers.x_scraper import XScraper

logger = logging.getLogger(__name__)

AVAILABLE_SOURCES = (
    "github",
    "x",
    "coindesk",
    "cointelegraph",
    "reddit",
    "hackernews",
    "openai_blog",
    "deepmind_blog",
    "bilibili",
    "theblock",
    "blockworks",
    "telegram",
    "defillama",
    "rwa_protocols",
)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Web3 + AI 每日简报生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s generate                          生成今日简报（全部数据源）
  %(prog)s generate --sources github         只用 GitHub Trending
  %(prog)s generate --sources coindesk       只用 CoinDesk 新闻
  %(prog)s generate --sources reddit hackernews  只用 Reddit + HN
  %(prog)s generate --ai-only               只生成 AI 简报
  %(prog)s generate --max 5                  每源最多处理 5 条
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
    parser.add_argument("--ai-only", action="store_true", help="只爬取 AI 项目")
    parser.add_argument("--web3-only", action="store_true", help="只爬取 Web3 项目")
    parser.add_argument("--max", type=int, default=12, help="分析总条数上限（默认 12）")
    parser.add_argument(
        "--per-source", type=int, default=2, help="每个数据源最多取几条（默认 2）"
    )
    parser.add_argument("--output-dir", default="outputs", help="输出目录（默认 outputs）")
    parser.add_argument(
        "--bilibili-urls",
        nargs="+",
        default=[],
        help="要分析的B站视频URL列表",
    )

    args = parser.parse_args()

    if args.command == "generate":
        generate_briefing(args)


def generate_briefing(args) -> None:
    """Orchestrate: scrape -> analyze -> report -> queue -> quality dashboard."""
    run_start = time.time()
    run_date = datetime.now().strftime("%Y-%m-%d")

    print("=" * 60)
    print("Web3 + AI 每日简报生成器")
    print("=" * 60)
    print()

    if not os.getenv("OPENAI_API_KEY"):
        print("错误：未找到 OPENAI_API_KEY")
        print("请在 .env 文件中配置 API key")
        return

    sources = list(AVAILABLE_SOURCES) if "all" in args.sources else list(args.sources)

    all_items = _scrape_all_sources(sources, args)

    if not all_items:
        print("没有找到相关项目或新闻")
        return

    deduped_items, event_meta = _deduplicate_by_event(all_items)
    print(f"事件去重：{len(all_items)} -> {len(deduped_items)}")

    selected = _select_per_source(deduped_items, per_source=args.per_source, total=args.max)

    print()
    print(
        f"正在使用 OpenAI API 分析 {len(selected)} 条内容（共抓取 {len(all_items)} 条，去重后 {len(deduped_items)} 条）..."
    )
    summarizer = Summarizer()
    analyzed = summarizer.batch_summarize(selected, max_items=len(selected))
    analyzed = _attach_event_metadata(analyzed, event_meta)

    tracker = EventTracker(output_dir=args.output_dir, run_date=run_date)
    analyzed = tracker.annotate(analyzed)
    tracker.update(analyzed)
    print(f"   完成 {len(analyzed)} 条内容分析")
    print()

    print("正在生成 Markdown 简报...")
    builder = ReportBuilder(output_dir=args.output_dir)
    briefing_path = builder.generate_report(items=analyzed)
    print(f"   简报已生成：{briefing_path}")
    print()

    queue_path = builder.generate_social_queue(items=analyzed, max_posts=args.max)
    print(f"   社媒队列已生成：{queue_path}")
    print()

    digest_path = builder.generate_editorial_digest(items=analyzed, date=run_date, max_items=args.max)
    print(f"   编辑摘要已生成：{digest_path}")
    story_card_path = os.path.join(args.output_dir, f"{run_date}-story-card.md")
    if os.path.exists(story_card_path):
        print(f"   固定展示稿已生成：{story_card_path}")
    print()

    digest_payload = {}
    try:
        digest_payload = json.loads(Path(digest_path).read_text(encoding="utf-8"))
    except Exception as err:
        logger.warning("Failed to read digest json at %s: %s", digest_path, err)
    drafts_path = builder.generate_distribution_drafts(
        items=analyzed,
        digest=digest_payload,
        date=run_date,
        max_items=min(args.max, 3),
    )
    print(f"   分发草稿已生成：{drafts_path}")
    print()

    dashboard_path = _write_quality_cost_dashboard(
        output_dir=args.output_dir,
        run_date=run_date,
        elapsed_seconds=time.time() - run_start,
        analyzed=analyzed,
        selected_count=len(selected),
        scraped_count=len(all_items),
        deduped_count=len(deduped_items),
        summarizer_metrics=summarizer.get_metrics(),
    )
    print(f"   质量成本看板：{dashboard_path}")
    print()

    _print_stats(analyzed, briefing_path, queue_path, digest_path, drafts_path, dashboard_path)


def _scrape_all_sources(sources, args):
    """Run all requested scrapers, return combined ContentItem list."""
    all_items = []

    if "github" in sources:
        all_items.extend(_scrape_github(args))

    if "x" in sources:
        all_items.extend(_scrape_x())

    if "coindesk" in sources:
        all_items.extend(_scrape_rss("CoinDesk", CoinDeskScraper()))

    if "cointelegraph" in sources:
        all_items.extend(_scrape_rss("CoinTelegraph", CoinTelegraphScraper()))

    if "openai_blog" in sources:
        all_items.extend(_scrape_rss("OpenAI Blog", OpenAIBlogScraper()))

    if "deepmind_blog" in sources:
        all_items.extend(_scrape_rss("DeepMind Blog", DeepMindBlogScraper()))

    if "theblock" in sources:
        all_items.extend(_scrape_rss("The Block", TheBlockScraper()))

    if "blockworks" in sources:
        all_items.extend(_scrape_rss("Blockworks", BlockworksScraper()))

    if "telegram" in sources:
        all_items.extend(_scrape_telegram())

    if "defillama" in sources:
        all_items.extend(_scrape_defillama())

    if "rwa_protocols" in sources:
        all_items.extend(_scrape_rwa_protocols())

    if "bilibili" in sources:
        all_items.extend(_scrape_bilibili(args))

    if "reddit" in sources:
        all_items.extend(_scrape_reddit())

    if "hackernews" in sources:
        all_items.extend(_scrape_hackernews())

    return all_items


def _scrape_bilibili(args):
    """Scrape Bilibili videos from URLs."""
    if not args.bilibili_urls:
        return []

    print("正在爬取 Bilibili 视频文本...")
    try:
        from src.scrapers.bilibili_scraper import BilibiliScraper

        scraper = BilibiliScraper()
        items = scraper.fetch(
            video_urls=args.bilibili_urls, max_items=len(args.bilibili_urls)
        )
        print(f"   找到 {len(items)} 个 Bilibili 视频的文本")
        return items
    except ImportError as e:
        logger.warning("Bilibili dependencies are missing: %s", e)
        print("   Bilibili 依赖缺失，跳过")
        return []
    except Exception as e:
        logger.warning("Failed to fetch Bilibili videos: %s", e)
        print("   Bilibili 爬取失败，跳过")
        return []


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


def _scrape_x():
    """Scrape X feeds from configured handles via Nitter RSS."""
    print("正在爬取 X 账号动态 (Nitter RSS)...")
    try:
        scraper = XScraper()
        items = scraper.fetch(max_items=10, per_handle=3)
        if not scraper.handles:
            print("   未配置 X_HANDLES，跳过")
            return []
        print(f"   找到 {len(items)} 条 X 动态")
        return items
    except Exception as e:
        logger.warning("Failed to fetch X: %s", e)
        print("   X 爬取失败，跳过")
        return []


def _scrape_github(args):
    """Scrape GitHub Trending with AI/Web3 keyword filtering."""
    items = []
    scraper = GitHubScraper()

    if not args.web3_only:
        print("正在爬取 GitHub Trending (AI 项目)...")
        ai_items = scraper.filter_by_keywords(scraper.fetch(since="daily"), AI_KEYWORDS)
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


def _scrape_telegram():
    """Scrape Telegram channels."""
    print("正在爬取 Telegram 频道 (Telethon)...")
    try:
        from src.scrapers.telegram_scraper import TelegramScraper

        scraper = TelegramScraper()
        items = scraper.fetch(max_items=5)
        print(f"   找到 {len(items)} 条 Telegram 消息")
        return items
    except ImportError as e:
        logger.warning("Telegram dependencies are missing: %s", e)
        print("   Telegram 依赖缺失，跳过")
        return []
    except Exception as e:
        logger.warning("Failed to fetch Telegram: %s", e)
        print("   Telegram 爬取失败，跳过")
        return []


def _scrape_defillama():
    """Scrape DefiLlama metrics."""
    print("正在抓取 DefiLlama 链上指标 (Quant Alpha)...")
    try:
        scraper = DefiLlamaScraper()
        items = scraper.fetch()
        print("   已获取 Perp DEX 核心指标")
        return items
    except Exception as e:
        logger.warning("Failed to fetch DefiLlama: %s", e)
        return []


def _scrape_rwa_protocols():
    """Scrape RWA protocol news and analytics."""
    print("正在抓取 RWA 协议信号...")
    items = []
    try:
        items.extend(RWAAnalyticsScraper().fetch())
    except Exception as e:
        logger.warning("Failed to fetch RWA analytics: %s", e)
    try:
        items.extend(RWAProtocolScraper().fetch(max_items=5))
    except Exception as e:
        logger.warning("Failed to fetch RWA protocol feeds: %s", e)

    print(f"   找到 {len(items)} 条 RWA 相关信号")
    return items


def _select_per_source(items, per_source: int = 2, total: int = 10):
    """Pick up to `per_source` items from each source, capped at `total`."""
    counts: dict = {}
    selected = []
    for item in items:
        src = item.source.value if isinstance(item, ContentItem) else item.get("source", "unknown")
        if counts.get(src, 0) < per_source:
            selected.append(item)
            counts[src] = counts.get(src, 0) + 1
        if len(selected) >= total:
            break
    return selected


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


def _deduplicate_by_event(items):
    """Collapse multi-source duplicates into event-level items."""
    deduped, meta = deduplicate_items_by_event(items)
    return deduped, meta


def _attach_event_metadata(analyzed, event_meta):
    """Attach event metadata onto analyzed dict rows."""
    attached = []
    for item in analyzed:
        key = canonicalize_url(item.get("url", ""))
        meta = event_meta.get(key, {})
        attached.append({**item, **meta})
    return attached


def _write_quality_cost_dashboard(
    output_dir: str,
    run_date: str,
    elapsed_seconds: float,
    analyzed,
    selected_count: int,
    scraped_count: int,
    deduped_count: int,
    summarizer_metrics,
):
    """Write per-run and rolling quality/cost dashboards."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fallback_count = sum(
        1 for row in analyzed if str(row.get("analysis_status", "")) == "fallback"
    )
    success_count = max(0, len(analyzed) - fallback_count)
    success_rate = round((success_count / max(1, selected_count)) * 100.0, 2)

    run_payload = {
        "run_date": run_date,
        "generated_at": datetime.now().isoformat(),
        "duration_seconds": round(float(elapsed_seconds), 2),
        "scraped_count": int(scraped_count),
        "deduped_count": int(deduped_count),
        "selected_count": int(selected_count),
        "analyzed_count": int(len(analyzed)),
        "success_count": int(success_count),
        "fallback_count": int(fallback_count),
        "success_rate": success_rate,
        "token_usage": {
            "prompt_tokens": int(summarizer_metrics.get("prompt_tokens", 0)),
            "completion_tokens": int(summarizer_metrics.get("completion_tokens", 0)),
            "total_tokens": int(summarizer_metrics.get("total_tokens", 0)),
        },
        "estimated_cost_usd": round(
            float(summarizer_metrics.get("estimated_cost_usd", 0.0)), 6
        ),
        "pricing_configured": bool(summarizer_metrics.get("pricing_configured", False)),
        "failure_reasons": summarizer_metrics.get("failure_reasons", {}),
        "api_calls": {
            "total": int(summarizer_metrics.get("calls_total", 0)),
            "success": int(summarizer_metrics.get("calls_success", 0)),
            "failed": int(summarizer_metrics.get("calls_failed", 0)),
        },
    }

    daily_json = out_dir / f"{run_date}-quality-cost.json"
    daily_json.write_text(
        json.dumps(run_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    rolling_file = out_dir / "quality_cost_dashboard.json"
    if rolling_file.exists():
        try:
            rolling = json.loads(rolling_file.read_text(encoding="utf-8"))
        except Exception:
            rolling = {"runs": []}
    else:
        rolling = {"runs": []}
    runs = rolling.get("runs", [])
    runs.append(run_payload)
    rolling["runs"] = runs[-60:]
    rolling_file.write_text(
        json.dumps(rolling, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md_lines = [
        f"# Quality & Cost Dashboard | {run_date}",
        "",
        f"- Duration: `{run_payload['duration_seconds']}s`",
        f"- Success Rate: `{run_payload['success_rate']}%` ({success_count}/{selected_count})",
        f"- Scraped -> Deduped -> Selected: `{scraped_count} -> {deduped_count} -> {selected_count}`",
        f"- Tokens: `{run_payload['token_usage']['total_tokens']}` (prompt {run_payload['token_usage']['prompt_tokens']}, completion {run_payload['token_usage']['completion_tokens']})",
        f"- Estimated Cost (USD): `{run_payload['estimated_cost_usd']}`",
        f"- Pricing Configured: `{run_payload['pricing_configured']}`",
        f"- Failure Reasons: `{json.dumps(run_payload['failure_reasons'], ensure_ascii=False)}`",
    ]
    daily_md = out_dir / f"{run_date}-quality-cost.md"
    daily_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return str(daily_json)


def _print_stats(analyzed, filepath, queue_path, digest_path, drafts_path, dashboard_path):
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
    print(f"社媒队列：{queue_path}")
    print(f"编辑摘要：{digest_path}")
    print(f"分发草稿：{drafts_path}")
    print(f"质量看板：{dashboard_path}")
    print(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


if __name__ == "__main__":
    main()
