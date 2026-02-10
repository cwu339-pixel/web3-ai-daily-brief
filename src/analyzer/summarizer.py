"""AI-powered summarizer using Gemini API.

This project historically depended on `google-generativeai`, but the code was
partially migrated to the newer `google-genai` SDK (import path: `from google import genai`).
To avoid runtime failures, support both SDKs and pick whichever is installed.
"""
import json
import logging
import os
import time
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

    # Free tier: 5 RPM → wait 13s between calls to stay safely under limit.
    # Paid tier users can set GEMINI_RPM env var to override (e.g. "60").
    _DEFAULT_FREE_TIER_RPM = 5
    _MIN_REQUEST_INTERVAL = 60.0 / _DEFAULT_FREE_TIER_RPM  # 12 seconds
    _MAX_RETRIES = 3
    _RETRY_BACKOFF = 35  # seconds to wait after a 429 before retrying

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

        # Rate-limit state: track when the last API call was made
        self._last_call_ts: float = 0.0

        # Allow paid-tier users to raise the RPM via env var
        rpm = int(os.getenv("GEMINI_RPM", str(self._DEFAULT_FREE_TIER_RPM)))
        self._request_interval = 60.0 / max(rpm, 1)

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
        compatibility. Applies rate limiting and retries on 429 errors.

        Returns:
            Dict with original fields + summary, category, importance.
        """
        if isinstance(item, dict):
            return self._summarize_legacy_dict(item)

        prompt = build_prompt(item)

        for attempt in range(self._MAX_RETRIES):
            self._wait_for_rate_limit()
            try:
                text = self._call_api(prompt)
                analysis = self._parse_json_response(text)
                return {**item.to_dict(), **analysis}

            except Exception as e:
                err_str = str(e)
                is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str
                is_last_attempt = attempt == self._MAX_RETRIES - 1

                if is_rate_limit and not is_last_attempt:
                    logger.warning(
                        "Rate limited on '%s' (attempt %d/%d), "
                        "waiting %ds before retry...",
                        item.title, attempt + 1, self._MAX_RETRIES, self._RETRY_BACKOFF,
                    )
                    time.sleep(self._RETRY_BACKOFF)
                    continue

                logger.warning("Error summarizing %s: %s", item.title, e)
                return {
                    **item.to_dict(),
                    "summary": item.description[:50] + "..." if item.description else item.title,
                    "category": "其他",
                    "importance": 5,
                }

        # Should not reach here, but satisfy type checker
        return {**item.to_dict(), "summary": item.title, "category": "其他", "importance": 5}

    def _wait_for_rate_limit(self) -> None:
        """Sleep if needed to respect the configured requests-per-minute limit."""
        now = time.monotonic()
        elapsed = now - self._last_call_ts
        if elapsed < self._request_interval:
            sleep_for = self._request_interval - elapsed
            logger.debug("Rate limit: sleeping %.1fs before next API call", sleep_for)
            time.sleep(sleep_for)
        self._last_call_ts = time.monotonic()

    def _call_api(self, prompt: str) -> str:
        """Make a single Gemini API call and return the response text."""
        if self.backend == "google-genai":
            response = self.client.models.generate_content(
                model=self.model_id, contents=prompt
            )
        else:
            response = self.model.generate_content(prompt)
        return response.text

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
