"""GitHub Trending scraper"""
import logging
import re
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from src.models.content_item import ContentItem, SourceType
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


# Investment-focused keywords (Summer Capital priority sectors)
AI_KEYWORDS = [
    "AI", "artificial intelligence", "machine learning", "ML",
    "deep learning", "neural", "LLM", "GPT", "transformer",
    "agent", "autonomous agent", "reasoning", "o1", "o3",
    "Claude", "OpenAI", "Anthropic", "AGI", "multimodal",
]

WEB3_KEYWORDS = [
    # Core infrastructure
    "blockchain", "web3", "crypto", "ethereum", "solidity",
    "smart contract", "L1", "L2", "layer 2", "rollup",
    "solana", "polygon", "avalanche", "bitcoin", "wallet",

    # Priority sectors (Joey mentioned)
    "perpetual", "perp", "DEX", "decentralized exchange",
    "stablecoin", "stable coin", "USDC", "USDT", "payment",
    "RWA", "real world asset", "tokenization", "tokenized",

    # DeFi & Trading
    "DeFi", "AMM", "liquidity", "yield", "staking",
    "trading terminal", "derivatives", "options",

    # Ecosystem
    "DAO", "dApp", "NFT", "oracle", "bridge",
]


class GitHubScraper(BaseScraper):
    """Scrape GitHub Trending page and return ContentItem list."""

    BASE_URL = "https://github.com/trending"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36"
        )
    }

    def source_name(self) -> str:
        return "GitHub Trending"

    def fetch(
        self,
        language: Optional[str] = None,
        since: str = "daily",
        **kwargs,
    ) -> List[ContentItem]:
        """Fetch trending projects from GitHub.

        Args:
            language: Filter by programming language (e.g. "python").
            since: Time range ("daily", "weekly", "monthly").

        Returns:
            List of ContentItem with source=GITHUB.
        """
        url = (
            f"{self.BASE_URL}/{language}" if language else self.BASE_URL
        )
        params = {"since": since}

        try:
            response = requests.get(
                url, headers=self.HEADERS, params=params, timeout=10
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error("Failed to fetch GitHub Trending: %s", e)
            return []

        return self._parse_trending_page(response.text)

    # Backward-compatible API (v1) returning list[dict].
    # Some scripts/tests used `fetch_trending()` with legacy field names.
    def fetch_trending(
        self,
        language: Optional[str] = None,
        since: str = "daily",
    ) -> List[dict]:
        items = self.fetch(language=language, since=since)
        return [
            {
                "repo_name": item.title,
                "description": item.description,
                "url": item.url,
                "stars": item.engagement,
                "language": item.content_type,
            }
            for item in items
        ]

    def _parse_trending_page(self, html: str) -> List[ContentItem]:
        """Parse trending page HTML into ContentItem list."""
        soup = BeautifulSoup(html, "html.parser")
        items = []

        for article in soup.find_all("article", class_="Box-row"):
            try:
                item = self._parse_single_article(article)
                if item is not None:
                    items.append(item)
            except Exception as e:
                logger.warning("Failed to parse project: %s", e)

        return items

    def _parse_single_article(self, article) -> Optional[ContentItem]:
        """Parse a single <article> element. Returns None on failure."""
        h2 = article.find("h2", class_="h3")
        if not h2:
            return None

        repo_link = h2.find("a")
        if not repo_link:
            return None

        repo_name = repo_link.get("href", "").strip("/")
        repo_url = f"https://github.com{repo_link.get('href', '')}"

        desc_elem = article.find("p", class_="col-9")
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        lang_elem = article.find(
            "span", attrs={"itemprop": "programmingLanguage"}
        )
        language = lang_elem.get_text(strip=True) if lang_elem else "Unknown"

        stars_elem = article.find(
            "span", class_="d-inline-block float-sm-right"
        )
        stars_text = (
            stars_elem.get_text(strip=True) if stars_elem else "0"
        )
        stars = (
            re.sub(r"[^\d]", "", stars_text.split("today")[0])
            if "today" in stars_text
            else "0"
        )

        return ContentItem(
            title=repo_name,
            description=description,
            url=repo_url,
            source=SourceType.GITHUB,
            engagement=stars,
            content_type=language,
        )


def get_ai_trending() -> List[ContentItem]:
    """Convenience: fetch AI-related trending projects."""
    scraper = GitHubScraper()
    all_projects = scraper.fetch(since="daily")
    return scraper.filter_by_keywords(all_projects, AI_KEYWORDS)


def get_web3_trending() -> List[ContentItem]:
    """Convenience: fetch Web3-related trending projects."""
    scraper = GitHubScraper()
    all_projects = scraper.fetch(since="daily")
    return scraper.filter_by_keywords(all_projects, WEB3_KEYWORDS)
