"""GitHub Trending scraper"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re


class GitHubScraper:
    """爬取 GitHub Trending 页面"""

    def __init__(self):
        self.base_url = "https://github.com/trending"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

    def fetch_trending(
        self, language: Optional[str] = None, since: str = "daily"
    ) -> List[Dict[str, str]]:
        """
        获取 GitHub Trending 项目

        Args:
            language: 编程语言过滤（如 "python", "javascript"）
            since: 时间范围 ("daily", "weekly", "monthly")

        Returns:
            项目列表，每个项目包含：repo_name, description, url, stars, language
        """
        url = self.base_url
        params = {"since": since}

        if language:
            url = f"{self.base_url}/{language}"

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"❌ Error fetching GitHub Trending: {e}")
            return []

        return self._parse_trending_page(response.text)

    def _parse_trending_page(self, html: str) -> List[Dict[str, str]]:
        """解析 trending 页面 HTML"""
        soup = BeautifulSoup(html, "html.parser")
        projects = []

        # 找到所有 trending 项目
        articles = soup.find_all("article", class_="Box-row")

        for article in articles:
            try:
                # 项目名称和链接
                h2 = article.find("h2", class_="h3")
                if not h2:
                    continue

                repo_link = h2.find("a")
                if not repo_link:
                    continue

                repo_name = repo_link.get("href", "").strip("/")
                repo_url = f"https://github.com{repo_link.get('href', '')}"

                # 描述
                description_elem = article.find("p", class_="col-9")
                description = (
                    description_elem.get_text(strip=True) if description_elem else ""
                )

                # 编程语言
                language_elem = article.find("span", attrs={"itemprop": "programmingLanguage"})
                language = language_elem.get_text(strip=True) if language_elem else "Unknown"

                # 今日 stars
                stars_elem = article.find("span", class_="d-inline-block float-sm-right")
                stars_text = stars_elem.get_text(strip=True) if stars_elem else "0"
                # 提取数字（例如 "1,234 stars today" -> "1234"）
                stars = re.sub(r"[^\d]", "", stars_text.split("today")[0]) if "today" in stars_text else "0"

                projects.append(
                    {
                        "repo_name": repo_name,
                        "description": description,
                        "url": repo_url,
                        "stars": stars,
                        "language": language,
                    }
                )

            except Exception as e:
                print(f"⚠️  Warning: Failed to parse project: {e}")
                continue

        return projects

    def filter_by_keywords(
        self, projects: List[Dict[str, str]], keywords: List[str]
    ) -> List[Dict[str, str]]:
        """
        根据关键词过滤项目

        Args:
            projects: 项目列表
            keywords: 关键词列表（不区分大小写）

        Returns:
            过滤后的项目列表
        """
        if not projects:
            return []

        filtered = []
        keywords_lower = [kw.lower() for kw in keywords]

        for project in projects:
            # 在项目名称和描述中搜索关键词
            text = f"{project['repo_name']} {project['description']}".lower()

            if any(keyword in text for keyword in keywords_lower):
                filtered.append(project)

        return filtered


# 便捷函数
def get_ai_trending() -> List[Dict[str, str]]:
    """获取 AI 相关的 trending 项目"""
    scraper = GitHubScraper()
    all_projects = scraper.fetch_trending(since="daily")

    ai_keywords = [
        "AI", "artificial intelligence", "machine learning", "ML",
        "deep learning", "neural", "LLM", "GPT", "transformer",
        "diffusion", "stable diffusion", "computer vision", "NLP",
        "Claude", "OpenAI", "Anthropic"
    ]

    return scraper.filter_by_keywords(all_projects, ai_keywords)


def get_web3_trending() -> List[Dict[str, str]]:
    """获取 Web3 相关的 trending 项目"""
    scraper = GitHubScraper()
    all_projects = scraper.fetch_trending(since="daily")

    web3_keywords = [
        "blockchain", "web3", "crypto", "ethereum", "solidity",
        "smart contract", "DeFi", "NFT", "DAO", "dApp",
        "solana", "polygon", "avalanche", "bitcoin", "wallet"
    ]

    return scraper.filter_by_keywords(all_projects, web3_keywords)
