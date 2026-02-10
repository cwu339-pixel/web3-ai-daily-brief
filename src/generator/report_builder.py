"""Markdown report generator"""
import os
from datetime import datetime
from typing import Dict, List


SOURCE_LABELS = {
    "github": "GitHub Trending",
    "coindesk": "CoinDesk",
    "cointelegraph": "CoinTelegraph",
}

# Investment priority order (Summer Capital focus)
CATEGORY_ORDER = [
    "DeFi交易", "支付稳定币", "RWA资产代币化",  # Joey's priority sectors
    "融资动态", "前沿技术", "基础设施",
    "开发者工具", "市场动态", "监管政策", "其他",
]


class ReportBuilder:
    """Generate Markdown daily briefing reports."""

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_report(
        self,
        items: List[Dict] = None,
        date: str = None,
        ai_projects: List[Dict] = None,
        web3_projects: List[Dict] = None,
    ) -> str:
        """Generate a full daily briefing.

        Args:
            items: Unified list of analyzed items (from any source).
            date: Date string YYYY-MM-DD (defaults to today).
            ai_projects: (Legacy) AI projects list.
            web3_projects: (Legacy) Web3 projects list.

        Returns:
            File path of the generated report.
        """
        if items is None:
            items = [*(ai_projects or []), *(web3_projects or [])]

        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        content = self._build_markdown(date, items)

        filename = f"{date}-briefing.md"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath

    def _build_markdown(self, date: str, items: List[Dict]) -> str:
        """Build the full markdown report content."""
        source_counts = self._count_by_source(items)
        lines = self._render_header(date, source_counts)

        # Add market snapshot
        lines.extend(self._render_market_snapshot())

        by_domain = self._group_by_domain(items)

        # High priority items section (importance >= 8)
        high_priority = [item for item in items if item.get("importance", 0) >= 8]
        if high_priority:
            lines.append("## 🎯 高优先级项目 (投资相关性 ≥8分)")
            lines.append("")
            lines.extend(self._render_priority_items(high_priority))

        if by_domain.get("ai"):
            lines.append("## 🤖 前沿技术进展")
            lines.append("")
            lines.extend(self._render_domain_section(by_domain["ai"]))

        if by_domain.get("web3"):
            lines.append("## ⛓️ Crypto & Web3 动态")
            lines.append("")
            lines.extend(self._render_domain_section(by_domain["web3"]))

        if by_domain.get("other"):
            lines.append("## 📰 其他资讯")
            lines.append("")
            lines.extend(self._render_domain_section(by_domain["other"]))

        lines.extend(self._render_stats(source_counts))

        return "\n".join(lines)

    def _render_market_snapshot(self) -> List[str]:
        """Render real-time market data section."""
        try:
            from src.scrapers.market_scraper import MarketScraper

            scraper = MarketScraper()
            data = scraper.get_market_snapshot()
            fear_greed = scraper.get_fear_greed_index()

            if not data:
                return []

            lines = ["## 📊 市场快照", ""]

            # Render each coin
            coin_lines = []
            for coin, info in data.items():
                price = info["price"]
                change = info["change_24h"]
                sign = "+" if change >= 0 else ""
                color = "🟢" if change >= 0 else "🔴"
                coin_lines.append(
                    f"{color} **{coin}**: ${price:,.2f} ({sign}{change:.2f}%)"
                )

            lines.append(" | ".join(coin_lines))
            lines.append("")

            # Add Fear & Greed Index if available
            if fear_greed is not None:
                sentiment = (
                    "Extreme Greed"
                    if fear_greed >= 75
                    else "Greed"
                    if fear_greed >= 55
                    else "Neutral"
                    if fear_greed >= 45
                    else "Fear"
                    if fear_greed >= 25
                    else "Extreme Fear"
                )
                lines.append(f"📉 **Fear & Greed Index**: {fear_greed}/100 ({sentiment})")
                lines.append("")

            lines.append("---")
            lines.append("")
            return lines

        except Exception as e:
            # Fail gracefully if market data unavailable
            return []

    def _render_header(
        self, date: str, source_counts: Dict[str, int]
    ) -> List[str]:
        counts_str = " / ".join(
            f"{SOURCE_LABELS.get(src, src)} {count} 条"
            for src, count in source_counts.items()
        )
        return [
            f"# Tech & Crypto Investment Brief | {date}",
            "",
            f"> 📊 Summer Capital Daily Intelligence Report",
            f"> 🕐 Generated at {datetime.now().strftime('%H:%M')} UTC+8",
            f"> 📈 Data Sources: {counts_str}" if counts_str else "",
            "",
            "---",
            "",
        ]

    def _render_domain_section(self, items: List[Dict]) -> List[str]:
        """Render items grouped by source, then by category."""
        lines = []
        by_source = self._group_by_source(items)

        for source_key in ("github", "coindesk", "cointelegraph"):
            source_items = by_source.get(source_key, [])
            if not source_items:
                continue

            label = SOURCE_LABELS.get(source_key, source_key)
            lines.append(f"### {label}")
            lines.append("")

            by_cat = self._group_by_category(source_items)
            sorted_cats = sorted(
                by_cat.keys(),
                key=lambda x: (
                    CATEGORY_ORDER.index(x)
                    if x in CATEGORY_ORDER
                    else 999
                ),
            )

            for cat in sorted_cats:
                cat_items = by_cat[cat]
                if len(by_cat) > 1:
                    lines.append(f"**{cat}**")
                    lines.append("")

                for item in cat_items:
                    lines.extend(self._render_single_item(item))

        lines.append("---")
        lines.append("")
        return lines

    def _render_single_item(
        self, item: Dict, investment_focus: bool = False
    ) -> List[str]:
        """Render one item. Format differs by source type."""
        importance = item.get("importance", 5)
        stars_display = "⭐" * min(importance // 2, 5)
        title = item.get("title", item.get("repo_name", ""))
        url = item.get("url", "")
        source = item.get("source", "github")
        category = item.get("category", "其他")

        # Investment-focused header
        if investment_focus:
            lines = [
                f"**{stars_display} [{title}]({url})** "
                f"`{category}` `评分: {importance}/10`",
                "",
            ]
        else:
            lines = [f"**{stars_display} [{title}]({url})**", ""]

        lines.append(f"- 📝 **投资视角**：{item.get('summary', '')}")

        if source == "github":
            lines.append(
                f"- 🔧 **技术栈**："
                f"{item.get('content_type', item.get('language', 'Unknown'))}"
            )
            lines.append(
                f"- 🌟 **GitHub热度**："
                f"{item.get('engagement', item.get('stars', '0'))} stars"
            )
        else:
            source_label = SOURCE_LABELS.get(source, source)
            lines.append(f"- 📰 **来源**：{source_label}")
            pub_date = item.get("published_date", "")
            if pub_date:
                lines.append(f"- 🕐 **发布时间**：{pub_date}")

        lines.append("")
        return lines

    def _render_priority_items(self, items: List[Dict]) -> List[str]:
        """Render high-priority items with investment focus."""
        lines = []
        sorted_items = sorted(
            items, key=lambda x: x.get("importance", 0), reverse=True
        )

        for item in sorted_items:
            lines.extend(self._render_single_item(item, investment_focus=True))

        lines.append("---")
        lines.append("")
        return lines

    def _render_stats(self, source_counts: Dict[str, int]) -> List[str]:
        total = sum(source_counts.values())
        lines = [
            "---",
            "",
            "## 📈 今日数据",
            "",
            f"- 总计：{total} 条内容",
        ]
        for src, count in source_counts.items():
            label = SOURCE_LABELS.get(src, src)
            lines.append(f"- {label}：{count} 条")

        lines.append(
            f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        lines.extend([
            "",
            "---",
            "",
            "💡 **Focus Sectors**: Perp DEX | Stablecoin & Payment | RWA Tokenization | AI Infrastructure",
            "",
            "*Automated Intelligence Report | Powered by [Tech-Crypto-Brief](https://github.com/yourusername/web3-ai-daily-brief)*",
            "",
        ])
        return lines

    @staticmethod
    def _count_by_source(items: List[Dict]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for item in items:
            src = item.get("source", "github")
            counts = {**counts, src: counts.get(src, 0) + 1}
        return counts

    @staticmethod
    def _group_by_source(items: List[Dict]) -> Dict[str, List[Dict]]:
        groups: Dict[str, List[Dict]] = {}
        for item in items:
            src = item.get("source", "github")
            groups = {**groups, src: [*groups.get(src, []), item]}
        return groups

    @staticmethod
    def _group_by_category(items: List[Dict]) -> Dict[str, List[Dict]]:
        groups: Dict[str, List[Dict]] = {}
        for item in items:
            cat = item.get("category", "其他")
            groups = {**groups, cat: [*groups.get(cat, []), item]}

        return {
            cat: sorted(
                cat_items,
                key=lambda x: x.get("importance", 0),
                reverse=True,
            )
            for cat, cat_items in groups.items()
        }

    @staticmethod
    def _group_by_domain(items: List[Dict]) -> Dict[str, List[Dict]]:
        """Group items into ai / web3 / other based on category."""
        ai_categories = {"前沿技术"}
        web3_categories = {
            "DeFi交易", "支付稳定币", "RWA资产代币化",
            "融资动态", "市场动态", "监管政策", "基础设施"
        }

        result: Dict[str, List[Dict]] = {"ai": [], "web3": [], "other": []}
        for item in items:
            cat = item.get("category", "其他")
            # Skip items already shown in high-priority section
            if item.get("importance", 0) >= 8:
                continue
            if cat in ai_categories:
                result = {**result, "ai": [*result["ai"], item]}
            elif cat in web3_categories:
                result = {**result, "web3": [*result["web3"], item]}
            else:
                result = {**result, "other": [*result["other"], item]}
        return result
