"""Scrapers package with lazy imports.

Avoid importing optional heavy dependencies (RSS, Telegram, etc.) at package
import time. This keeps lightweight modules usable even when extras are absent.
"""

from importlib import import_module
from typing import Dict

__all__ = [
    "GitHubScraper",
    "CoinDeskScraper",
    "CoinTelegraphScraper",
    "RedditScraper",
    "HackerNewsScraper",
    "MarketScraper",
]

_MODULE_BY_CLASS: Dict[str, str] = {
    "GitHubScraper": "src.scrapers.github_scraper",
    "CoinDeskScraper": "src.scrapers.coindesk_scraper",
    "CoinTelegraphScraper": "src.scrapers.cointelegraph_scraper",
    "RedditScraper": "src.scrapers.reddit_scraper",
    "HackerNewsScraper": "src.scrapers.hackernews_scraper",
    "MarketScraper": "src.scrapers.market_scraper",
}


def __getattr__(name: str):
    module_path = _MODULE_BY_CLASS.get(name)
    if not module_path:
        raise AttributeError(f"module 'src.scrapers' has no attribute '{name}'")
    module = import_module(module_path)
    value = getattr(module, name)
    globals()[name] = value
    return value
