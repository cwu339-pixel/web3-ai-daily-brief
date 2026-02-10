"""AI-powered summarizer using Gemini API.

This project historically depended on `google-generativeai`, but the code was
partially migrated to the newer `google-genai` SDK (import path: `from google import genai`).
To avoid runtime failures, support both SDKs and pick whichever is installed.
"""
import json
import logging
import os
from typing import Any, Dict, List, Union

_GENAI_BACKEND = "unknown"
try:
    # New SDK: `pip install google-genai`
    from google import genai as _genai  # type: ignore

    _GENAI_BACKEND = "google-genai"
except Exception:  # pragma: no cover
    # Old SDK: `pip install google-generativeai`
    import google.generativeai as _genai  # type: ignore

    _GENAI_BACKEND = "google-generativeai"

from src.analyzer.prompt_templates import build_prompt
from src.models.content_item import ContentItem, SourceType

logger = logging.getLogger(__name__)


class Summarizer:
    """Analyze content items using the Gemini API."""

    def __init__(self, api_key: str = None):
        """Initialize Summarizer.

        Args:
            api_key: Gemini API key. Falls back to GEMINI_API_KEY env var.

        Raises:
            ValueError: If no API key is available.
        """
        resolved_key = api_key or os.getenv("GEMINI_API_KEY")
        if not resolved_key:
            raise ValueError(
                "GEMINI_API_KEY not found. "
                "Set it in .env file or environment variable."
                )

        self.model_id = "gemini-2.5-flash"
        self.backend = _GENAI_BACKEND

        if self.backend == "google-genai":
            self.client = _genai.Client(api_key=resolved_key)
            self.model = None
        else:
            # google-generativeai uses module-level configure + model instance.
            _genai.configure(api_key=resolved_key)
            self.client = None
            self.model = _genai.GenerativeModel(self.model_id)

    def summarize_item(
        self, item: Union[ContentItem, Dict]
    ) -> Dict[str, Any]:
        """Summarize a single content item.

        Accepts both ContentItem and legacy Dict format for backward
        compatibility.

        Returns:
            Dict with original fields + summary, category, importance.
        """
        if isinstance(item, dict):
            return self._summarize_legacy_dict(item)

        prompt = build_prompt(item)

        try:
            if self.backend == "google-genai":
                response = self.client.models.generate_content(
                    model=self.model_id, contents=prompt
                )
                text = response.text
            else:
                response = self.model.generate_content(prompt)
                text = response.text

            analysis = self._parse_json_response(text)
            return {**item.to_dict(), **analysis}

        except Exception as e:
            logger.warning("Error summarizing %s: %s", item.title, e)
            return {
                **item.to_dict(),
                "summary": item.description[:50] + "...",
                "category": "其他",
                "importance": 5,
            }

    def batch_summarize(
        self,
        items: Union[List[ContentItem], List[Dict]],
        max_items: int = 20,
    ) -> List[Dict[str, Any]]:
        """Batch-summarize multiple items, sorted by importance desc."""
        if not items:
            return []

        results = [
            self.summarize_item(item) for item in items[:max_items]
        ]
        return sorted(
            results, key=lambda x: x.get("importance", 0), reverse=True
        )

    # kept for backward compat with old code calling summarize_project
    summarize_project = summarize_item

    def categorize_items(
        self, items: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """Group analyzed items by category (immutable)."""
        categorized: Dict[str, List[Dict]] = {}
        for item in items:
            category = item.get("category", "其他")
            categorized = {
                **categorized,
                category: [*categorized.get(category, []), item],
            }
        return categorized

    def _summarize_legacy_dict(self, project: Dict) -> Dict:
        """Handle old Dict[str, str] format from GitHubScraper v1."""
        item = ContentItem(
            title=project.get("repo_name", project.get("title", "")),
            description=project.get("description", ""),
            url=project.get("url", ""),
            source=SourceType.GITHUB,
            engagement=project.get("stars"),
            content_type=project.get("language"),
        )
        return self.summarize_item(item)

    @staticmethod
    def _parse_json_response(text: str) -> Dict:
        """Extract JSON from Gemini response (may be wrapped in ```json)."""
        content = text.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        return json.loads(content)
