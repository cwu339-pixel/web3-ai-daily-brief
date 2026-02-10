"""Base RSS feed scraper"""
import logging
from abc import abstractmethod
from typing import List

import feedparser
from bs4 import BeautifulSoup

from src.models.content_item import ContentItem, SourceType
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class RSSBaseScraper(BaseScraper):
    """Shared logic for RSS-based news scrapers.

    Subclasses only need to implement feed_url(), source_type(),
    and source_name().
    """

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36"
        )
    }

    @abstractmethod
    def feed_url(self) -> str:
        """RSS feed URL to parse."""
        ...

    @abstractmethod
    def source_type(self) -> SourceType:
        """SourceType enum value for this feed."""
        ...

    def fetch(self, max_items: int = 20, **kwargs) -> List[ContentItem]:
        """Parse the RSS feed and return ContentItem list.

        Args:
            max_items: Maximum number of items to return.

        Returns:
            List of ContentItem from this RSS source.
        """
        try:
            feed = feedparser.parse(
                self.feed_url(),
                request_headers=self.HEADERS,
            )
        except Exception as e:
            logger.error("Failed to fetch RSS feed %s: %s", self.feed_url(), e)
            return []

        if feed.bozo and not feed.entries:
            logger.error(
                "RSS feed parse error for %s: %s",
                self.source_name(),
                feed.bozo_exception,
            )
            return []

        return [
            self._entry_to_item(entry)
            for entry in feed.entries[:max_items]
            if self._entry_to_item(entry) is not None
        ]

    def _entry_to_item(self, entry) -> ContentItem:
        """Convert a single feedparser entry to ContentItem."""
        try:
            title = getattr(entry, "title", "")
            raw_summary = getattr(entry, "summary", "")
            description = self._strip_html(raw_summary)[:500]
            link = getattr(entry, "link", "")
            published = getattr(entry, "published", None)
            tags = getattr(entry, "tags", [])
            content_type = tags[0].get("term", "") if tags else ""

            return ContentItem(
                title=title,
                description=description,
                url=link,
                source=self.source_type(),
                published_date=published,
                content_type=content_type,
            )
        except Exception as e:
            logger.warning(
                "Failed to parse RSS entry from %s: %s",
                self.source_name(),
                e,
            )
            return None

    @staticmethod
    def _strip_html(text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ""
        return BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)
