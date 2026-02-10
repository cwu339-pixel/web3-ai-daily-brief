"""Abstract base class for all content scrapers"""
from abc import ABC, abstractmethod
from typing import List

from src.models.content_item import ContentItem


class BaseScraper(ABC):
    """All scrapers must extend this class."""

    @abstractmethod
    def fetch(self, **kwargs) -> List[ContentItem]:
        """Fetch content items from the source."""
        ...

    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name for display in logs."""
        ...

    def filter_by_keywords(
        self, items: List[ContentItem], keywords: List[str]
    ) -> List[ContentItem]:
        """Filter items by keyword match in title + description.

        Case-insensitive. Returns items matching ANY keyword.
        """
        if not items or not keywords:
            return items or []

        keywords_lower = tuple(kw.lower() for kw in keywords)
        return [
            item
            for item in items
            if any(
                kw in f"{item.title} {item.description}".lower()
                for kw in keywords_lower
            )
        ]
