"""Tests for AI summarizer"""
import pytest
from src.analyzer.summarizer import Summarizer


class TestSummarizer:
    """Summarizer tests"""

    @pytest.fixture
    def sample_project(self):
        """Sample GitHub project data"""
        return {
            "repo_name": "openai/gpt-4",
            "description": "GPT-4 is a large multimodal model that can solve difficult problems with greater accuracy than previous models.",
            "url": "https://github.com/openai/gpt-4",
            "stars": "1234",
            "language": "Python",
        }

    def test_summarizer_initialization(self):
        """测试初始化（需要 API key）"""
        # 如果没有 API key，跳过测试
        try:
            summarizer = Summarizer()
            assert summarizer is not None
        except ValueError:
            pytest.skip("ANTHROPIC_API_KEY not set")

    def test_summarize_project(self, sample_project):
        """测试项目总结"""
        try:
            summarizer = Summarizer()
            result = summarizer.summarize_project(sample_project)

            assert "summary" in result
            assert "category" in result
            assert "importance" in result

            # 总结应该比原描述短
            assert len(result["summary"]) < len(sample_project["description"])
            # 重要性应该在 1-10 之间
            assert 1 <= result["importance"] <= 10

        except ValueError:
            pytest.skip("ANTHROPIC_API_KEY not set")

    def test_batch_summarize(self):
        """测试批量总结"""
        projects = [
            {
                "repo_name": "test/repo1",
                "description": "A machine learning framework",
                "url": "https://github.com/test/repo1",
                "stars": "100",
                "language": "Python",
            },
            {
                "repo_name": "test/repo2",
                "description": "A blockchain platform",
                "url": "https://github.com/test/repo2",
                "stars": "200",
                "language": "Rust",
            },
        ]

        try:
            summarizer = Summarizer()
            results = summarizer.batch_summarize(projects, max_items=2)

            assert len(results) <= 2
            for result in results:
                assert "summary" in result
                assert "category" in result

        except ValueError:
            pytest.skip("ANTHROPIC_API_KEY not set")

    def test_empty_input(self):
        """测试空输入"""
        try:
            summarizer = Summarizer()
            results = summarizer.batch_summarize([])
            assert results == []
        except ValueError:
            pytest.skip("ANTHROPIC_API_KEY not set")
