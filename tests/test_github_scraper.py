"""Tests for GitHub Trending scraper"""
import requests

from src.scrapers.github_scraper import GitHubScraper
from src.models.content_item import ContentItem


SAMPLE_HTML = """
<html>
  <body>
    <article class="Box-row">
      <h2 class="h3"><a href="/owner1/repo1">owner1 / repo1</a></h2>
      <p class="col-9">An AI project</p>
      <span itemprop="programmingLanguage">Python</span>
      <span class="d-inline-block float-sm-right">1,234 stars today</span>
    </article>
    <article class="Box-row">
      <h2 class="h3"><a href="/owner2/repo2">owner2 / repo2</a></h2>
      <p class="col-9">A web3 project</p>
      <span itemprop="programmingLanguage">Go</span>
      <span class="d-inline-block float-sm-right">56 stars today</span>
    </article>
  </body>
</html>
""".strip()


class TestGitHubScraper:
    """GitHub scraper tests"""

    def test_scraper_initialization(self):
        """测试爬虫初始化"""
        scraper = GitHubScraper()
        assert scraper is not None

    def test_fetch_trending_returns_list(self):
        """fetch() 返回 ContentItem 列表（不依赖外网）"""
        scraper = GitHubScraper()

        class _Resp:
            text = SAMPLE_HTML

            @staticmethod
            def raise_for_status():
                return None

        def _fake_get(*args, **kwargs):
            return _Resp()

        # Mock requests.get so tests don't depend on network / GitHub.
        _orig_get = requests.get
        try:
            requests.get = _fake_get  # type: ignore

            results = scraper.fetch(language="python", since="daily")
            assert isinstance(results, list)
            assert len(results) == 2
            assert all(isinstance(x, ContentItem) for x in results)
        finally:
            requests.get = _orig_get

    def test_trending_item_structure(self):
        """测试解析出的 ContentItem 字段"""
        scraper = GitHubScraper()

        items = scraper._parse_trending_page(SAMPLE_HTML)
        item = items[0]
        assert item.title == "owner1/repo1"
        assert item.description == "An AI project"
        assert item.url == "https://github.com/owner1/repo1"
        assert item.content_type == "Python"
        assert item.engagement == "1234"

    def test_filter_by_keywords(self):
        """测试关键词过滤"""
        scraper = GitHubScraper()
        all_results = scraper._parse_trending_page(SAMPLE_HTML)

        ai_results = scraper.filter_by_keywords(
            all_results, keywords=["AI", "machine learning", "LLM"]
        )

        assert isinstance(ai_results, list)
        # AI 相关项目应该少于全部项目
        assert len(ai_results) <= len(all_results)

    def test_empty_results_handling(self):
        """测试空结果处理"""
        scraper = GitHubScraper()
        results = scraper.filter_by_keywords([], keywords=["test"])

        assert results == []

    def test_fetch_trending_legacy_shape(self):
        """fetch_trending() 兼容旧的 list[dict] 形状"""
        scraper = GitHubScraper()
        items = scraper._parse_trending_page(SAMPLE_HTML)

        # Monkeypatch fetch() to avoid network and focus on conversion.
        scraper.fetch = lambda **kwargs: items  # type: ignore
        results = scraper.fetch_trending(since="daily")
        assert isinstance(results, list)
        assert results[0]["repo_name"] == "owner1/repo1"
        assert results[0]["stars"] == "1234"
