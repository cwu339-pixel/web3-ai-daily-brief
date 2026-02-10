"""CoinTelegraph RSS news scraper"""
from src.models.content_item import SourceType
from src.scrapers.rss_scraper import RSSBaseScraper


class CoinTelegraphScraper(RSSBaseScraper):
    """Fetch latest articles from CoinTelegraph RSS feed."""

    FEED = "https://cointelegraph.com/rss"

    def feed_url(self) -> str:
        return self.FEED

    def source_type(self) -> SourceType:
        return SourceType.COINTELEGRAPH

    def source_name(self) -> str:
        return "CoinTelegraph"
