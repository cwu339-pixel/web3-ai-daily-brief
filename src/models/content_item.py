"""Unified content item model for all data sources"""
from dataclasses import dataclass, asdict
from typing import Optional
from enum import Enum


class SourceType(Enum):
    GITHUB = "github"
    COINDESK = "coindesk"
    COINTELEGRAPH = "cointelegraph"


@dataclass(frozen=True)
class ContentItem:
    """Immutable data model for content from any source.

    Fields:
        title: Display name (repo name for GitHub, article title for news)
        description: Content summary or body excerpt
        url: Source link
        source: Which scraper produced this item
        published_date: ISO date string (None for GitHub)
        engagement: Stars for GitHub, None for news
        content_type: Language for GitHub, section/tag for news
    """

    title: str
    description: str
    url: str
    source: SourceType
    published_date: Optional[str] = None
    engagement: Optional[str] = None
    content_type: Optional[str] = None

    def to_legacy_dict(self) -> dict:
        """Convert to the old Dict[str, str] format for backward compatibility."""
        return {
            "repo_name": self.title,
            "description": self.description,
            "url": self.url,
            "stars": self.engagement or "0",
            "language": self.content_type or "Unknown",
        }

    def to_dict(self) -> dict:
        """Convert to a plain dict representation."""
        result = asdict(self)
        result["source"] = self.source.value
        return result
