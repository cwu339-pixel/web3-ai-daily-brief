"""Scrapers package"""
from src.scrapers.github_scraper import GitHubScraper
from src.scrapers.coindesk_scraper import CoinDeskScraper
from src.scrapers.cointelegraph_scraper import CoinTelegraphScraper
from src.scrapers.reddit_scraper import RedditScraper
from src.scrapers.hackernews_scraper import HackerNewsScraper
from src.scrapers.market_scraper import MarketScraper

__all__ = [
    "GitHubScraper",
    "CoinDeskScraper",
    "CoinTelegraphScraper",
    "RedditScraper",
    "HackerNewsScraper",
    "MarketScraper",
]
