"""X source scraper via Nitter RSS feeds.

This scraper is optional and requires at least one handle configured in
`X_HANDLES` (comma-separated), for example:
  X_HANDLES=openai,elonmusk

By default it uses `https://nitter.net`, configurable via `NITTER_BASE_URL`.
"""

from __future__ import annotations

import logging
import os
from typing import List
from urllib.parse import quote

import feedparser

from src.models.content_item import ContentItem, SourceType
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class XScraper(BaseScraper):
    """Fetch posts from configured X handles through Nitter RSS."""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36"
        )
    }

    def __init__(self, base_url: str | None = None, handles: List[str] | None = None):
        self.base_url = (base_url or os.getenv("NITTER_BASE_URL", "https://nitter.net")).rstrip("/")
        self.handles = handles or self._read_handles_from_env()

    def source_name(self) -> str:
        return "X"

    def fetch(self, max_items: int = 10, **kwargs) -> List[ContentItem]:
        if not self.handles:
            return []

        per_handle = max(1, int(kwargs.get("per_handle", 3)))
        all_items: List[ContentItem] = []

        for handle in self.handles:
            feed_url = f"{self.base_url}/{quote(handle)}/rss"
            try:
                feed = feedparser.parse(feed_url, request_headers=self.HEADERS)
            except Exception as exc:
                logger.warning("Failed to fetch X RSS for @%s: %s", handle, exc)
                continue

            if getattr(feed, "bozo", False) and not getattr(feed, "entries", []):
                logger.warning("X RSS parse error for @%s from %s", handle, feed_url)
                continue

            count = 0
            for entry in getattr(feed, "entries", []):
                title = str(getattr(entry, "title", "")).strip()
                link = str(getattr(entry, "link", "")).strip()
                summary = str(getattr(entry, "summary", "")).strip()
                published = str(getattr(entry, "published", "")).strip() or None
                if not link or not title:
                    continue
                all_items.append(
                    ContentItem(
                        title=title,
                        description=summary[:500],
                        url=link,
                        source=SourceType.X,
                        published_date=published,
                        content_type=f"@{handle}",
                    )
                )
                count += 1
                if count >= per_handle:
                    break

            if len(all_items) >= max_items:
                break

        return all_items[:max_items]

    @staticmethod
    def _read_handles_from_env() -> List[str]:
        raw = os.getenv("X_HANDLES", "").strip()
        if not raw:
            return []
        handles: List[str] = []
        for token in raw.split(","):
            value = token.strip()
            if not value:
                continue
            if value.startswith("@"):
                value = value[1:]
            handles.append(value)
        return handles
