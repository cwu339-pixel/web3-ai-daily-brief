"""AI-powered summarizer using Gemini API"""
import os
from typing import List, Dict
from google import genai
from google.genai import types
import json


class Summarizer:
    """使用 Gemini API 总结和分类内容"""

    def __init__(self, api_key: str = None):
        """
        初始化 Summarizer

        Args:
            api_key: Google Gemini API key（如果不提供，从环境变量读取）

        Raises:
            ValueError: 如果没有找到 API key
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. "
                "Set it in .env file or environment variable."
            )

        self.client = genai.Client(api_key=self.api_key)
        self.model_id = 'gemini-2.5-flash'

    def summarize_project(self, project: Dict[str, str]) -> Dict[str, any]:
        """
        总结单个 GitHub 项目

        Args:
            project: 项目信息字典，包含 repo_name, description, url 等

        Returns:
            包含 summary, category, importance 的字典
        """
        prompt = f"""请分析以下 GitHub 项目：

项目名称：{project['repo_name']}
描述：{project['description']}
编程语言：{project.get('language', 'Unknown')}
今日 Stars：{project.get('stars', '0')}

请提供：
1. 一句话总结（中文，<30 字）
2. 分类（从以下选择一个）：AI技术/Web3技术/开发工具/其他
3. 重要性评分（1-10，10 最重要）

请严格按照以下 JSON 格式输出，不要有任何其他文字：
{{
  "summary": "项目的一句话总结",
  "category": "分类名称",
  "importance": 8
}}"""

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            content = response.text.strip()

            # 提取 JSON（Gemini 可能会在前后加 ```json）
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)

            # 添加原始项目信息
            result.update(project)

            return result

        except Exception as e:
            print(f"⚠️  Error summarizing {project['repo_name']}: {e}")
            # 返回降级结果
            return {
                **project,
                "summary": project["description"][:50] + "...",
                "category": "其他",
                "importance": 5,
            }

    def batch_summarize(
        self, projects: List[Dict[str, str]], max_items: int = 20
    ) -> List[Dict[str, any]]:
        """
        批量总结多个项目

        Args:
            projects: 项目列表
            max_items: 最多处理的项目数

        Returns:
            总结后的项目列表
        """
        if not projects:
            return []

        results = []
        for project in projects[:max_items]:
            result = self.summarize_project(project)
            results.append(result)

        # 按重要性排序
        results.sort(key=lambda x: x.get("importance", 0), reverse=True)

        return results

    def categorize_items(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        """
        将项目按类别分组

        Args:
            items: 已总结的项目列表

        Returns:
            按类别分组的字典
        """
        categorized = {}

        for item in items:
            category = item.get("category", "其他")
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(item)

        return categorized
