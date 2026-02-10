"""CoinDesk RSS news scraper"""
from src.models.content_item import SourceType
from src.scrapers.rss_scraper import RSSBaseScraper


class CoinDeskScraper(RSSBaseScraper):
    """Fetch latest articles from CoinDesk RSS feed."""

    FEED = "https://www.coindesk.com/arc/outboundfeeds/rss/"

    def feed_url(self) -> str:
        return self.FEED

    def source_type(self) -> SourceType:
        return SourceType.COINDESK

    def source_name(self) -> str:
        return "CoinDesk"
