"""Hacker News scraper via Algolia HN Search API (no auth required)"""
import logging
import time
from typing import List

import requests

from src.models.content_item import ContentItem, SourceType
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

# Default keywords to keep HN content focused on AI/ML topics
_DEFAULT_AI_KEYWORDS = [
    "AI", "artificial intelligence", "machine learning", "LLM",
    "GPT", "Claude", "Gemini", "deep learning", "neural network",
    "transformer", "diffusion", "RAG", "agent", "OpenAI", "Anthropic",
    "Mistral", "Llama", "open source AI",
]

_HEADERS = {
    "User-Agent": "web3-ai-daily-brief/1.0 (automated research tool)"
}

# Algolia HN Search API endpoint
_HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
_HN_ITEM_BASE = "https://news.ycombinator.com/item?id="


class HackerNewsScraper(BaseScraper):
    """Fetch AI-related stories from Hacker News via Algolia Search API.

    Queries Algolia for stories matching AI keywords, filtered by a
    minimum points threshold to keep signal-to-noise high.

    Args:
        keywords: List of search terms. Each term is queried separately
                  and results are deduplicated by story ID.
        min_points: Minimum upvote score. Stories below this are dropped.
        hours_back: Only include stories published within this window.
    """

    def __init__(
        self,
        keywords: List[str] | None = None,
        min_points: int = 10,
        hours_back: int = 24,
    ) -> None:
        self._keywords = keywords if keywords is not None else _DEFAULT_AI_KEYWORDS
        self._min_points = min_points
        self._hours_back = hours_back

    # ------------------------------------------------------------------
    # BaseScraper interface
    # ------------------------------------------------------------------

    def source_name(self) -> str:
        return "Hacker News (AI)"

    def fetch(self, max_items: int = 20, **kwargs) -> List[ContentItem]:
        """Return AI-related HN stories as ContentItem list.

        Queries multiple keywords in parallel (sequentially for simplicity),
        deduplicates, and sorts by points descending.

        Args:
            max_items: Maximum number of stories to return after dedup + sort.

        Returns:
            List of ContentItem objects sorted by engagement (points).
        """
        seen_ids: set[str] = set()
        all_hits: List[dict] = []

        for keyword in self._keywords:
            hits = self._search_keyword(keyword)
            for hit in hits:
                story_id = hit.get("objectID", "")
                if story_id and story_id not in seen_ids:
                    seen_ids.add(story_id)
                    all_hits.append(hit)

        # Sort by points descending so highest-signal stories come first
        all_hits.sort(key=lambda h: h.get("points", 0) or 0, reverse=True)

        items: List[ContentItem] = []
        for hit in all_hits[:max_items]:
            item = self._hit_to_item(hit)
            if item is not None:
                items.append(item)
        return items

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _search_keyword(self, keyword: str) -> List[dict]:
        """Query Algolia for one keyword; return raw hit dicts."""
        since_ts = int(time.time()) - self._hours_back * 3600
        params = {
            "query": keyword,
            "tags": "story",
            "numericFilters": f"points>={self._min_points},created_at_i>{since_ts}",
            "hitsPerPage": 20,
        }

        try:
            response = requests.get(
                _HN_SEARCH_URL, headers=_HEADERS, params=params, timeout=10
            )
            response.raise_for_status()
            return response.json().get("hits", [])
        except requests.RequestException as exc:
            logger.error("HN Algolia fetch failed for query '%s': %s", keyword, exc)
            return []
        except ValueError as exc:
            logger.error("HN JSON parse error for query '%s': %s", keyword, exc)
            return []

    def _hit_to_item(self, hit: dict) -> ContentItem | None:
        """Convert a single Algolia HN hit to a ContentItem."""
        try:
            title = hit.get("title", "").strip()
            story_text = hit.get("story_text") or ""
            description = story_text[:500].strip() if story_text else ""

            # External URL if available, else fall back to HN thread
            url = hit.get("url") or f"{_HN_ITEM_BASE}{hit.get('objectID', '')}"

            points = hit.get("points", 0) or 0
            created_at = hit.get("created_at")  # ISO 8601 string
            author = hit.get("author", "")

            return ContentItem(
                title=title,
                description=description,
                url=url,
                source=SourceType.HACKERNEWS,
                published_date=created_at,
                engagement=str(points),
                content_type=author,
            )
        except Exception as exc:
            logger.warning("Failed to parse HN hit %s: %s", hit.get("objectID"), exc)
            return None
