"""Reddit subreddit scraper using public JSON API (no auth required)"""
import logging
from typing import List

import requests

from src.models.content_item import ContentItem, SourceType
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "web3-ai-daily-brief/1.0 (automated research tool)"
}


class RedditScraper(BaseScraper):
    """Fetch top/hot posts from a subreddit via Reddit's public JSON API.

    No API key required. Uses the public *.json endpoint.

    Args:
        subreddit: Subreddit name without the r/ prefix (e.g. "MachineLearning").
        sort: Feed sort order — "hot", "new", or "top".
        time_filter: Used only when sort="top". One of "day", "week", "month".
    """

    BASE_URL = "https://www.reddit.com/r/{subreddit}/{sort}.json"

    def __init__(
        self,
        subreddit: str = "MachineLearning",
        sort: str = "hot",
        time_filter: str = "day",
    ) -> None:
        self._subreddit = subreddit
        self._sort = sort
        self._time_filter = time_filter

    # ------------------------------------------------------------------
    # BaseScraper interface
    # ------------------------------------------------------------------

    def source_name(self) -> str:
        return f"Reddit r/{self._subreddit}"

    def fetch(self, max_items: int = 20, **kwargs) -> List[ContentItem]:
        """Return top posts from the subreddit as ContentItem list.

        Args:
            max_items: Maximum number of posts to return.

        Returns:
            List of ContentItem objects, newest/hottest first.
        """
        url = self.BASE_URL.format(
            subreddit=self._subreddit, sort=self._sort
        )
        params: dict = {"limit": min(max_items, 100)}
        if self._sort == "top":
            params["t"] = self._time_filter

        try:
            response = requests.get(
                url, headers=_HEADERS, params=params, timeout=10
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            logger.error("Reddit fetch failed for r/%s: %s", self._subreddit, exc)
            return []
        except ValueError as exc:
            logger.error("Reddit JSON parse error for r/%s: %s", self._subreddit, exc)
            return []

        posts = data.get("data", {}).get("children", [])
        items: List[ContentItem] = []
        for post in posts[:max_items]:
            item = self._post_to_item(post.get("data", {}))
            if item is not None:
                items.append(item)
        return items

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _post_to_item(self, post: dict) -> ContentItem | None:
        """Convert a single Reddit post dict to a ContentItem."""
        try:
            title = post.get("title", "").strip()
            selftext = post.get("selftext", "") or ""
            description = selftext[:500].strip() if selftext else ""
            url = post.get("url") or f"https://www.reddit.com{post.get('permalink', '')}"
            score = post.get("score", 0)
            flair = post.get("link_flair_text") or ""
            created_utc = post.get("created_utc")
            published = (
                str(int(created_utc)) if created_utc is not None else None
            )

            return ContentItem(
                title=title,
                description=description,
                url=url,
                source=SourceType.REDDIT,
                published_date=published,
                engagement=str(score),
                content_type=flair,
            )
        except Exception as exc:
            logger.warning(
                "Failed to parse Reddit post from r/%s: %s",
                self._subreddit,
                exc,
            )
            return None
