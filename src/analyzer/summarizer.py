"""AI-powered summarizer using OpenAI API."""
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Union

from openai import OpenAI, RateLimitError

from src.analyzer.prompt_templates import build_prompt
from src.models.content_item import ContentItem, SourceType

logger = logging.getLogger(__name__)


class Summarizer:
    """Analyze content items using the OpenAI API."""

    _DEFAULT_RPM = 60
    _MAX_RETRIES = 3
    _RETRY_BACKOFF = 10  # seconds to wait after a 429 before retrying
    _DEFAULT_OWNER = "研究员"

    def __init__(self, api_key: str = None):
        """Initialize Summarizer.

        Args:
            api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.

        Raises:
            ValueError: If no API key is available.
        """
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise ValueError(
                "OPENAI_API_KEY not found. "
                "Set it in .env file or environment variable."
            )

        self.model_id = os.getenv("OPENAI_MODEL", "gpt-5-mini")
        self.client = OpenAI(api_key=resolved_key)
        input_price = os.getenv("OPENAI_INPUT_COST_PER_1M", "")
        output_price = os.getenv("OPENAI_OUTPUT_COST_PER_1M", "")
        self._pricing_configured = bool(input_price and output_price)
        self._input_cost_per_1m = float(input_price or 0.0)
        self._output_cost_per_1m = float(output_price or 0.0)
        self._metrics: Dict[str, Any] = {
            "model": self.model_id,
            "calls_total": 0,
            "calls_success": 0,
            "calls_failed": 0,
            "items_total": 0,
            "items_success": 0,
            "items_fallback": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "pricing_configured": self._pricing_configured,
            "failure_reasons": {},
        }

        # Rate-limit state
        self._last_call_ts: float = 0.0
        rpm = int(os.getenv("OPENAI_RPM", str(self._DEFAULT_RPM)))
        self._request_interval = 60.0 / max(rpm, 1)

    def summarize_item(
        self, item: Union[ContentItem, Dict]
    ) -> Dict[str, Any]:
        """Summarize a single content item.

        Accepts both ContentItem and legacy Dict format for backward
        compatibility. Applies rate limiting and retries on 429 errors.

        Returns:
            Dict with original fields + summary, category, importance.
        """
        self._metrics["items_total"] += 1

        if isinstance(item, dict):
            return self._summarize_legacy_dict(item)

        prompt = build_prompt(item)

        for attempt in range(self._MAX_RETRIES):
            self._wait_for_rate_limit()
            try:
                text, usage = self._call_api(prompt)
                analysis = self._parse_json_response(text)
                normalized = self._normalize_analysis(analysis, item)
                self._record_usage(usage)
                self._metrics["items_success"] += 1
                return {**item.to_dict(), **normalized, "analysis_status": "success"}

            except RateLimitError as e:
                self._record_failure("rate_limit")
                if attempt < self._MAX_RETRIES - 1:
                    logger.warning(
                        "Rate limited on '%s' (attempt %d/%d), waiting %ds before retry...",
                        item.title,
                        attempt + 1,
                        self._MAX_RETRIES,
                        self._RETRY_BACKOFF,
                    )
                    time.sleep(self._RETRY_BACKOFF)
                    continue
                logger.warning("Rate limit error summarizing %s: %s", item.title, e)
                return self._fallback_result(item)
            except Exception as e:
                self._record_failure(type(e).__name__)
                logger.warning("Error summarizing %s: %s", item.title, e)
                return self._fallback_result(item)

        # Should not reach here, but satisfy type checker
        return self._fallback_result(item)

    def _wait_for_rate_limit(self) -> None:
        """Sleep if needed to respect the configured requests-per-minute limit."""
        now = time.monotonic()
        elapsed = now - self._last_call_ts
        if elapsed < self._request_interval:
            sleep_for = self._request_interval - elapsed
            logger.debug("Rate limit: sleeping %.1fs before next API call", sleep_for)
            time.sleep(sleep_for)
        self._last_call_ts = time.monotonic()

    def _call_api(self, prompt: str) -> tuple[str, Dict[str, int]]:
        """Make a single OpenAI API call and return text + usage tokens."""
        self._metrics["calls_total"] += 1
        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是VC投资研究助手。仅输出JSON对象。"
                            "必须包含 summary/category/importance/action_item/owner/deadline/expected_gain/execution_risk/editorial_angle/market_impact/evidence_points 字段。"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception:
            self._metrics["calls_failed"] += 1
            raise

        self._metrics["calls_success"] += 1
        usage = {
            "prompt_tokens": int(getattr(response.usage, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(response.usage, "completion_tokens", 0) or 0),
            "total_tokens": int(getattr(response.usage, "total_tokens", 0) or 0),
        }
        content = response.choices[0].message.content
        if isinstance(content, str):
            return content, usage
        if content is None:
            return "{}", usage
        return str(content), usage

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

    def get_metrics(self) -> Dict[str, Any]:
        """Return a copy of summarization metrics for dashboarding."""
        return {**self._metrics}

    def _record_usage(self, usage: Dict[str, int]) -> None:
        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage.get("completion_tokens", 0) or 0)
        total_tokens = int(usage.get("total_tokens", 0) or 0)
        self._metrics["prompt_tokens"] += prompt_tokens
        self._metrics["completion_tokens"] += completion_tokens
        self._metrics["total_tokens"] += total_tokens
        if self._pricing_configured:
            input_cost = (prompt_tokens / 1_000_000.0) * self._input_cost_per_1m
            output_cost = (completion_tokens / 1_000_000.0) * self._output_cost_per_1m
            self._metrics["estimated_cost_usd"] += input_cost + output_cost

    def _record_failure(self, reason: str) -> None:
        reasons = self._metrics.get("failure_reasons", {})
        reasons[reason] = int(reasons.get(reason, 0)) + 1
        self._metrics["failure_reasons"] = reasons

    @staticmethod
    def _parse_json_response(text: str) -> Dict:
        """Extract JSON from model response (may be wrapped in ```json)."""
        content = text.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", content)
            if not match:
                raise
            return json.loads(match.group(0))

    def _normalize_analysis(
        self, analysis: Dict[str, Any], item: ContentItem
    ) -> Dict[str, Any]:
        summary = str(analysis.get("summary", "")).strip()
        category = str(analysis.get("category", "Other")).strip() or "Other"
        investment_thesis = str(analysis.get("investment_thesis", "")).strip()
        risk_factor = str(analysis.get("risk_factor", "")).strip()
        competitive_landscape = str(analysis.get("competitive_landscape", "")).strip()
        valuation_context = str(analysis.get("valuation_context", "")).strip()
        editorial_angle = str(analysis.get("editorial_angle", "")).strip()
        market_impact = str(analysis.get("market_impact", "")).strip()
        evidence_points = str(analysis.get("evidence_points", "")).strip()
        action_item = str(analysis.get("action_item", "")).strip()
        owner = str(analysis.get("owner", "")).strip() or self._DEFAULT_OWNER
        deadline = str(analysis.get("deadline", "")).strip()
        expected_gain = str(analysis.get("expected_gain", "")).strip()
        execution_risk = str(analysis.get("execution_risk", "")).strip()

        try:
            importance = int(analysis.get("importance", 5))
        except (TypeError, ValueError):
            importance = 5
        importance = max(1, min(10, importance))

        if not action_item:
            action_item = f"针对「{item.title}」输出下一步执行计划并验证结果。"
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", deadline):
            deadline = (
                datetime.now(timezone.utc) + timedelta(days=1)
            ).strftime("%Y-%m-%d")
        if not expected_gain:
            expected_gain = "提升决策效率，缩短从信息到执行的路径。"

        summary = self._upgrade_summary(
            item=item,
            summary=summary,
            editorial_angle=editorial_angle,
            market_impact=market_impact,
            investment_thesis=investment_thesis,
        )
        summary, summary_impact, summary_risk = self._extract_structured_fields(summary)
        editorial_angle, angle_impact, angle_risk = self._extract_structured_fields(editorial_angle)
        if not market_impact:
            market_impact = summary_impact or angle_impact
        if not execution_risk:
            execution_risk = summary_risk or angle_risk

        summary = self._strip_action_phrases(summary)
        summary = self._strip_leading_label(summary, "判断")
        summary = self._strip_leading_label(summary, "立场")
        summary = self._strip_leading_label(summary, "观点")
        summary = self._strip_leading_label(summary, "结论")
        editorial_angle = self._strip_action_phrases(editorial_angle)
        editorial_angle = self._strip_leading_label(editorial_angle, "判断")
        editorial_angle = self._strip_leading_label(editorial_angle, "立场")
        editorial_angle = self._strip_leading_label(editorial_angle, "观点")
        editorial_angle = self._strip_leading_label(editorial_angle, "结论")
        market_impact = self._strip_leading_label(self._strip_action_phrases(market_impact), "影响")
        market_impact = self._strip_leading_label(market_impact, "市场影响")
        market_impact = self._strip_leading_label(market_impact, "影响对象")
        execution_risk = self._strip_leading_label(execution_risk, "风险")
        execution_risk = self._strip_leading_label(execution_risk, "风险边界")
        execution_risk = self._strip_leading_label(execution_risk, "不确定性")
        if not editorial_angle:
            editorial_angle = summary
        if not market_impact:
            market_impact = expected_gain
        if not execution_risk:
            execution_risk = risk_factor or "信息噪声可能导致误判，需要二次验证。"
        evidence_points = self._normalize_evidence_points(evidence_points, item)
        summary = self._tighten_sentence(summary, max_chars=72)
        editorial_angle = self._tighten_sentence(editorial_angle, max_chars=78)
        market_impact = self._tighten_sentence(market_impact, max_chars=90)
        execution_risk = self._tighten_sentence(execution_risk, max_chars=70)

        return {
            "summary": summary or "暂无总结",
            "category": category,
            "importance": importance,
            "action_item": action_item,
            "owner": owner,
            "deadline": deadline,
            "expected_gain": expected_gain,
            "execution_risk": execution_risk,
            "investment_thesis": investment_thesis,
            "risk_factor": risk_factor,
            "competitive_landscape": competitive_landscape,
            "valuation_context": valuation_context,
            "editorial_angle": editorial_angle,
            "market_impact": market_impact,
            "evidence_points": evidence_points,
        }

    def _fallback_result(self, item: ContentItem) -> Dict[str, Any]:
        summary = item.description[:50] + "..." if item.description else item.title
        self._metrics["items_fallback"] += 1
        return {
            **item.to_dict(),
            "summary": summary,
            "category": "其他",
            "importance": 5,
            "action_item": f"人工复核「{item.title}」并补全执行动作。",
            "owner": self._DEFAULT_OWNER,
            "deadline": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d"),
            "expected_gain": "避免漏掉高价值信号，保持内容质量。",
            "execution_risk": "模型输出失败，需人工判断优先级。",
            "editorial_angle": summary,
            "market_impact": "证据不足，需人工验证后再决定是否发布。",
            "evidence_points": "",
            "analysis_status": "fallback",
        }

    @staticmethod
    def _upgrade_summary(
        item: ContentItem,
        summary: str,
        editorial_angle: str,
        market_impact: str,
        investment_thesis: str,
    ) -> str:
        """Avoid title-like rewrites; force a judgment-first sentence."""
        title = str(item.title or "").strip()
        base = str(summary or "").strip()
        if editorial_angle:
            candidate = editorial_angle.strip()
            if len(candidate) >= 14:
                return candidate

        # If summary is too close to title, synthesize from thesis/impact.
        base_norm = re.sub(r"\W+", "", base.lower())
        title_norm = re.sub(r"\W+", "", title.lower())
        too_close = bool(base_norm and title_norm and (base_norm in title_norm or title_norm in base_norm))

        if too_close or len(base) < 14:
            thesis = str(investment_thesis or "").strip()
            impact = str(market_impact or "").strip()
            if thesis and impact:
                return f"{thesis}；{impact}"
            if thesis:
                return thesis
            if impact:
                return impact

        return base or "该信号提示结构性变化，需结合仓位与流动性窗口执行。"

    @staticmethod
    def _strip_action_phrases(text: str) -> str:
        raw = str(text or "").strip()
        if not raw:
            return raw
        cleaned = raw
        cleaned = re.sub(r"(可执行动作|下一步动作|行动建议|动作)[:：].*$", "", cleaned)
        cleaned = re.sub(r"[；;，,]\s*建议[^；。]*", "", cleaned)
        cleaned = re.sub(r"[；;，,]\s*可执行[^；。]*", "", cleaned)
        cleaned = re.sub(r"(对读者影响[:：]\s*)(可关注|需|需要|应当|应该|应|优先)\s*", r"\1", cleaned)
        cleaned = cleaned.replace("我们应", "市场通常会")
        cleaned = cleaned.replace("投资者应", "投资者通常会")
        cleaned = cleaned.replace("项目方应", "项目方通常会")
        cleaned = cleaned.replace("建议", "显示")
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip("；;，, ")
        return cleaned or raw

    @staticmethod
    def _strip_leading_label(text: str, label: str) -> str:
        out = str(text or "").strip()
        if not out:
            return out
        pattern = re.compile(rf"^(?:{re.escape(label)}[：:]\s*)+")
        return pattern.sub("", out).strip() or out

    @staticmethod
    def _extract_structured_fields(text: str) -> tuple[str, str, str]:
        """Split mixed '判断/影响/风险' sentence into dedicated fields."""
        raw = str(text or "").strip()
        if not raw:
            return "", "", ""

        parts = [seg.strip(" ，,。") for seg in re.split(r"[；;]", raw) if seg.strip(" ，,。")]
        summary_parts: List[str] = []
        impact_parts: List[str] = []
        risk_parts: List[str] = []

        for part in parts:
            if match := re.match(r"^(?:判断|立场|观点|结论|核心判断)[：:]\s*(.+)$", part):
                summary_parts.append(match.group(1).strip())
                continue
            if match := re.match(r"^(?:影响|市场影响|影响对象|影响范围|影响方向|对读者影响|impact)[：:]\s*(.+)$", part, flags=re.IGNORECASE):
                impact_parts.append(match.group(1).strip())
                continue
            if match := re.match(r"^(?:风险|风险边界|风险提示|不确定性|execution_risk)[：:]\s*(.+)$", part, flags=re.IGNORECASE):
                risk_parts.append(match.group(1).strip())
                continue

            if not summary_parts:
                summary_parts.append(part)
                continue
            if not impact_parts and re.search(r"(对象|窗口|方向|流入|流出|成交|估值|融资|波动|影响)", part):
                impact_parts.append(part)
                continue
            if not risk_parts and re.search(r"(风险|不确定|延后|兼容|监管|波动|噪声|误判)", part):
                risk_parts.append(part)
                continue
            summary_parts.append(part)

        summary = "；".join([row for row in summary_parts if row]).strip()
        impact = "；".join([row for row in impact_parts if row]).strip()
        risk = "；".join([row for row in risk_parts if row]).strip()
        return summary, impact, risk

    @staticmethod
    def _tighten_sentence(text: str, max_chars: int = 72) -> str:
        raw = str(text or "").strip()
        if not raw:
            return raw
        compact = re.sub(r"\s+", " ", raw).strip()
        if len(compact) <= max_chars:
            return compact
        segments = [seg.strip() for seg in re.split(r"[。！？；;]", compact) if seg.strip()]
        if segments:
            first = segments[0]
            if len(first) <= max_chars:
                return first + ("。" if not first.endswith("。") else "")
        return compact[: max(1, max_chars - 1)].rstrip("，,；; ") + "…"

    @staticmethod
    def _normalize_evidence_points(evidence_points: str, item: ContentItem) -> str:
        points = [p.strip() for p in re.split(r"[；;]", str(evidence_points or "")) if p.strip()]
        has_numeric = any(re.search(r"\d", p) for p in points)
        numeric_point = ""

        if not has_numeric:
            if item.source == SourceType.GITHUB and str(item.engagement or "").strip():
                numeric_point = f"GitHub Stars {item.engagement}，显示初步社区关注度"
            elif str(item.published_date or "").strip():
                numeric_point = f"发布时间 {item.published_date}，为当期增量事件"
            else:
                numeric_point = "证据条数 1，需补充二次数据验证"

        if not points:
            if item.source == SourceType.GITHUB and str(item.engagement or "").strip():
                points = [f"GitHub Stars {item.engagement}，显示初步社区关注度"]
            elif str(item.published_date or "").strip():
                points = [f"发布时间 {item.published_date}，为当期增量事件"]
            else:
                points = [f"来源 {item.source.value}，需结合后续数据验证"]
        elif numeric_point:
            if len(points) >= 2:
                points = [points[0], numeric_point]
            else:
                points.append(numeric_point)

        unique_points: List[str] = []
        seen = set()
        for p in points:
            if p in seen:
                continue
            seen.add(p)
            unique_points.append(p)
            if len(unique_points) >= 2:
                break
        return "；".join(unique_points)
