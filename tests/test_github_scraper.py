"""Tests for GitHub Trending scraper"""
import pytest
from src.scrapers.github_scraper import GitHubScraper


class TestGitHubScraper:
    """GitHub scraper tests"""

    def test_scraper_initialization(self):
        """测试爬虫初始化"""
        scraper = GitHubScraper()
        assert scraper is not None

    def test_fetch_trending_returns_list(self):
        """测试获取 trending 返回列表"""
        scraper = GitHubScraper()
        results = scraper.fetch_trending(language="python", since="daily")

        assert isinstance(results, list)
        assert len(results) > 0

    def test_trending_item_structure(self):
        """测试每个 trending 项目的数据结构"""
        scraper = GitHubScraper()
        results = scraper.fetch_trending(language="python", since="daily")

        if results:
            item = results[0]
            assert "repo_name" in item
            assert "description" in item
            assert "url" in item
            assert "stars" in item
            assert "language" in item

    def test_filter_by_keywords(self):
        """测试关键词过滤"""
        scraper = GitHubScraper()
        all_results = scraper.fetch_trending(since="daily")

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
