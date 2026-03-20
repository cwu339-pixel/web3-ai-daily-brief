"""Elite Markdown report generator (Hardened Version)."""
import json
import os
import logging
import re
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

SOURCE_LABELS = {
    "github": "GitHub Trending",
    "x": "X (Twitter)",
    "coindesk": "CoinDesk",
    "cointelegraph": "CoinTelegraph",
    "theblock": "The Block (Fast)",
    "blockworks": "Blockworks (Fast)",
    "telegram": "Telegram (Alpha)",
    "openai_blog": "OpenAI Blog",
    "deepmind_blog": "DeepMind Blog",
    "defillama": "DefiLlama (Quant)",
    "protocol_blog": "Protocol Alpha (RWA)",
}

CATEGORY_ORDER = [
    "Institutional Adoption", "Regulatory", "Funding & M&A",
    "AI Infrastructure", "AI Agent Framework", "DePIN",
    "ZK&Privacy", "L1&L2 Scaling", "DeFi Alpha", "DeFi&Yield",
    "RWA&Stables", "Developer Tools", "Market Sentiment", "Core Infrastructure", "Other",
]

class ReportBuilder:
    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        flag = str(os.getenv("INCLUDE_ACTION_LINES", "0")).strip().lower()
        self.include_action_lines = flag in {"1", "true", "yes", "on"}

    def generate_report(self, items: List[Dict], date: str = None) -> str:
        if date is None: date = datetime.now().strftime("%Y-%m-%d")
        
        source_counts = {}
        for i in items:
            s = i.get("source", "unknown")
            source_counts[s] = source_counts.get(s, 0) + 1

        lines = [
            f"# Tech & Crypto Investment Brief | {date}",
            "",
            f"> 📊 Summer Capital Daily Intelligence Report",
            f"> 🕐 Generated at {datetime.now().strftime('%H:%M')} UTC+8",
            f"> 📈 Data Sources: {' / '.join([f'{SOURCE_LABELS.get(s, s)} {n}条' for s, n in source_counts.items()])}",
            "",
            "---",
            "",
        ]

        # 1. Market Snapshot
        lines.extend(self._render_market_snapshot())

        # 2. RWA Dashboard (Explicit check)
        rwa_items = [i for i in items if i.get("source") == "defillama"]
        if rwa_items:
            lines.append("## 🏛️ RWA Institutional Dashboard (Ondo Focused)")
            lines.append("")
            for item in rwa_items:
                desc = item.get("description", "").replace("| ", "\n- ")
                lines.append(f"> {desc}")
            lines.append("")
            lines.append("---")
            lines.append("")

        # 3. Alpha Signal (Score >= 8)
        high_priority = [i for i in items if i.get("importance", 0) >= 8]
        if high_priority:
            lines.append("## 🎯 Alpha Signal (High Priority ≥8)")
            lines.append("")
            for item in sorted(high_priority, key=lambda x: x.get("importance", 0), reverse=True):
                lines.extend(self._render_item_card(item, True))
                lines.append("> ---")
                lines.append("")

        # 4. Sector Deep-Dive (Score 5-7)
        remaining = [i for i in items if 5 <= i.get("importance", 0) < 8]
        if remaining:
            lines.append("## 🧩 Sector Deep-Dive")
            lines.append("")
            # Group by category
            by_cat = {}
            for i in remaining:
                cat = i.get("category", "Other")
                if cat not in by_cat: by_cat[cat] = []
                by_cat[cat].append(i)
            
            sorted_cats = sorted(by_cat.keys(), key=lambda x: CATEGORY_ORDER.index(x) if x in CATEGORY_ORDER else 999)
            for cat in sorted_cats:
                lines.append(f"### 🏷️ {cat}")
                lines.append("")
                for item in by_cat[cat]:
                    lines.extend(self._render_item_card(item, False))

        lines.append("---")
        lines.append("💡 **Focus Sectors**: Perp DEX | Stablecoin & Payment | RWA Tokenization | AI Infrastructure")
        lines.append("\n*Automated Intelligence Report | Powered by [Tech-Crypto-Brief]*")

        filepath = os.path.join(self.output_dir, f"{date}-briefing.md")
        with open(filepath, "w", encoding="utf-8") as f: f.write("\n".join(lines))
        return filepath

    def _render_item_card(self, item: Dict, is_alpha: bool) -> List[str]:
        stars = "⭐" * min(item.get("importance", 5) // 2, 5)
        lines = [f"**{stars} [{item.get('title', 'Unknown')}]({item.get('url', '#')})**", f"- 💡 **Insight**: {item.get('summary', '')}"]
        if item.get("investment_thesis"): lines.append(f"- 📈 **Thesis**: {item['investment_thesis']}")
        if item.get("competitive_landscape"): lines.append(f"- ⚔️ **Landscape**: {item['competitive_landscape']}")
        if item.get("valuation_context"): lines.append(f"- 💰 **Valuation**: {item['valuation_context']}")
        if item.get("risk_factor"): lines.append(f"- ⚠️ **Risk**: {item['risk_factor']}")
        
        meta = [f"📰 {SOURCE_LABELS.get(item.get('source'), item.get('source'))}"]
        if item.get("published_date"): meta.append(f"🕐 {item['published_date']}")
        if not is_alpha: meta.append(f"⚖️ Score: {item.get('importance')}/10")
        lines.append(f"- 📊 **Context**: {' | '.join(meta)}\n")
        return lines

    def _render_market_snapshot(self) -> List[str]:
        try:
            from src.scrapers.market_scraper import MarketScraper
            scraper = MarketScraper()
            data = scraper.get_market_snapshot()
            if not data: return []
            lines = ["## 📊 Market Snapshot", ""]
            coins = [f"{'🟢' if info['change_24h'] >= 0 else '🔴'} **{c}**: ${info['price']:,.2f} ({'+' if info['change_24h'] >= 0 else ''}{info['change_24h']:.2f}%)" for c, info in data.items()]
            lines.append(" | ".join(coins))
            lines.append("\n---\n")
            return lines
        except: return []

    def generate_social_queue(
        self, items: List[Dict], date: str = None, max_posts: int = 5
    ) -> str:
        """Generate a social queue consumed by X ops / video scripts."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        ranked = sorted(items, key=lambda row: int(row.get("importance", 0) or 0), reverse=True)
        seen = set()
        queue_items = []
        for item in ranked:
            dedupe_key = str(item.get("event_id", "")).strip() or str(item.get("title", "")).strip()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            queue_items.append(self._build_queue_item(item))
            if len(queue_items) >= max_posts:
                break

        payload = {
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "items": queue_items,
        }

        filepath = os.path.join(self.output_dir, f"{date}-social-queue.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return filepath

    def generate_editorial_digest(
        self, items: List[Dict], date: str = None, max_items: int = 7
    ) -> str:
        """Generate a professional editorial digest from analyzed items."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        ranked = sorted(items, key=lambda row: int(row.get("importance", 0) or 0), reverse=True)
        deduped = []
        seen = set()
        for item in ranked:
            dedupe_key = str(item.get("event_id", "")).strip() or str(item.get("title", "")).strip()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            deduped.append(item)
            if len(deduped) >= max_items:
                break

        if self._should_use_model_digest():
            try:
                digest = self._generate_digest_with_model(deduped, date)
            except Exception as err:  # pragma: no cover - network/api failures
                logger.warning("Model digest failed, fallback to rule-based digest: %s", err)
                digest = self._generate_digest_fallback(deduped, date)
        else:
            digest = self._generate_digest_fallback(deduped, date)

        filepath = os.path.join(self.output_dir, f"{date}-digest.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(digest, f, ensure_ascii=False, indent=2)

        md_path = os.path.join(self.output_dir, f"{date}-digest.md")
        md_lines = [
            f"# 今日编辑摘要 | {date}",
            "",
            f"## {digest.get('title', '今日内容总结')}",
            "",
            digest.get("meta_line", ""),
            "",
            digest.get("summary_paragraph", ""),
            "",
            digest.get("focus_paragraph", ""),
            "",
            "### Key Points",
        ]
        for point in digest.get("key_points", []):
            md_lines.append(f"- {point}")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines) + "\n")

        story_card_path = os.path.join(self.output_dir, f"{date}-story-card.md")
        self._write_story_card(
            path=story_card_path,
            items=deduped,
            digest=digest,
        )
        return filepath

    def _write_story_card(self, path: str, items: List[Dict[str, Any]], digest: Dict[str, Any]) -> None:
        ranked = sorted(items, key=lambda row: int(row.get("importance", 0) or 0), reverse=True)
        top_items = ranked[:6]

        title = self._sanitize_text(digest.get("title"), "今日主线")
        one_line = self._tighten_sentence(
            self._sanitize_text(digest.get("summary_paragraph"), self._fallback_summary_text(top_items)),
            max_chars=120,
        )
        impact_risk = self._tighten_sentence(
            self._sanitize_text(digest.get("focus_paragraph"), self._fallback_focus_text(top_items)),
            max_chars=140,
        )

        lines = [
            "主标题",
            title,
            "",
            "一句话主线",
            one_line,
            "",
            "影响与风险",
            impact_risk,
            "",
            "Top 6 信号",
            "",
        ]

        for item in top_items:
            title_text = str(item.get("title", "Untitled")).strip()
            raw_summary = str(item.get("summary", "")).strip()
            raw_impact = str(item.get("market_impact", "")).strip()
            raw_risk = str(item.get("execution_risk", "")).strip()

            summary, parsed_impact, parsed_risk = self._extract_structured_fields(raw_summary)
            if not raw_impact:
                raw_impact = parsed_impact
            if not raw_risk:
                raw_risk = parsed_risk

            summary = self._strip_leading_label(self._strip_action_phrases(summary or raw_summary), "判断")
            summary = self._strip_leading_label(summary, "立场")
            summary = self._strip_leading_label(summary, "观点")
            impact = self._strip_leading_label(self._strip_action_phrases(raw_impact), "影响")
            impact = self._strip_leading_label(impact, "市场影响")
            risk = self._strip_leading_label(raw_risk, "风险")
            risk = self._strip_leading_label(risk, "风险边界")

            summary = self._tighten_sentence(summary, max_chars=78)
            impact = self._tighten_sentence(impact, max_chars=96)
            risk = self._tighten_sentence(risk, max_chars=72)
            evidence = self._tighten_sentence(str(item.get("evidence_points", "")).strip(), max_chars=88)
            lines.extend(
                [
                    title_text,
                    f"判断：{summary or '-'}",
                    f"影响：{impact or '-'}",
                    f"风险：{risk or '-'}",
                    f"证据：{evidence or '-'}",
                    "",
                ]
            )

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines).strip() + "\n")

    def _should_use_model_digest(self) -> bool:
        flag = str(os.getenv("EDITORIAL_DIGEST_USE_MODEL", "1")).strip().lower()
        return flag not in {"0", "false", "off", "no"}

    def _generate_digest_with_model(self, items: List[Dict], date: str) -> Dict[str, Any]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY missing")

        from openai import OpenAI

        model_id = os.getenv("OPENAI_DIGEST_MODEL", os.getenv("OPENAI_MODEL", "gpt-5-mini"))
        client = OpenAI(api_key=api_key)

        signals = [
            {
                "title": str(item.get("title", "")).strip(),
                "source": str(item.get("source", "unknown")).strip(),
                "category": str(item.get("category", "Other")).strip(),
                "importance": int(item.get("importance", 0) or 0),
                "summary": str(item.get("summary", "")).strip(),
                "editorial_angle": str(item.get("editorial_angle", "")).strip(),
                "market_impact": str(item.get("market_impact", "")).strip(),
                "trend_3d": str(item.get("event_trend_3d", "new")).strip(),
            }
            for item in items
        ]
        input_payload = {
            "date": date,
            "signals": signals,
        }

        system_prompt = (
            "你是资深Web3媒体主编。把信号列表改写成专业编辑摘要，"
            "不要机械报数，不要空话，不要夸张语气。"
            "输出必须是JSON对象，不要Markdown，不要额外解释。"
        )
        user_prompt = (
            "请基于输入信号，输出 JSON：\n"
            "{\n"
            '  "title": "短标题",\n'
            '  "meta_line": "一行概览",\n'
            '  "summary_paragraph": "第一段：今天主线与原因",\n'
            '  "focus_paragraph": "第二段：对读者有什么影响+风险提示",\n'
            '  "key_points": ["要点1", "要点2", "要点3"]\n'
            "}\n"
            "约束：\n"
            "1) 用简体中文；\n"
            "2) 每段 60-120 字；\n"
            "3) 要体现主题聚类和优先级；\n"
            "4) 不要直接写成 source(1)/new(7) 这种统计口吻。\n\n"
            f"输入:\n{json.dumps(input_payload, ensure_ascii=False)}"
        )

        resp = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = resp.choices[0].message.content
        text = content if isinstance(content, str) else str(content or "{}")
        parsed = self._parse_json_object(text)

        title = self._sanitize_text(parsed.get("title"), "今日内容总结")
        meta_line = self._sanitize_text(
            parsed.get("meta_line"),
            self._default_meta_line(items),
        )
        summary_paragraph = self._sanitize_text(
            parsed.get("summary_paragraph"),
            self._fallback_summary_text(items),
        )
        focus_paragraph = self._sanitize_text(
            parsed.get("focus_paragraph"),
            self._fallback_focus_text(items),
        )
        summary_paragraph = self._strip_action_phrases(summary_paragraph)
        focus_paragraph = self._strip_action_phrases(focus_paragraph)
        key_points_raw = parsed.get("key_points") or []
        key_points = []
        for row in key_points_raw[:3]:
            text = self._sanitize_text(row, "")
            if text:
                key_points.append(text)
        if not key_points:
            key_points = self._default_key_points(items)

        return {
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "title": title,
            "meta_line": meta_line,
            "summary_paragraph": summary_paragraph,
            "focus_paragraph": focus_paragraph,
            "key_points": key_points,
            "item_count": len(items),
            "style": "model",
        }

    def _generate_digest_fallback(self, items: List[Dict], date: str) -> Dict[str, Any]:
        return {
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "title": "今日内容总结",
            "meta_line": self._default_meta_line(items),
            "summary_paragraph": self._fallback_summary_text(items),
            "focus_paragraph": self._fallback_focus_text(items),
            "key_points": self._default_key_points(items),
            "item_count": len(items),
            "style": "fallback",
        }

    def _default_meta_line(self, items: List[Dict]) -> str:
        source_count = len({str(item.get("source", "unknown")).strip() for item in items})
        item_count = len(items)
        high_priority = sum(1 for item in items if int(item.get("importance", 0) or 0) >= 8)
        avg_score = (
            sum(int(item.get("importance", 0) or 0) for item in items) / max(item_count, 1)
            if items
            else 0.0
        )
        return f"来源 {source_count} 个 · 信号 {item_count} 条 · 高优先级 {high_priority} 条 · 均分 {avg_score:.1f}/10"

    def _fallback_summary_text(self, items: List[Dict]) -> str:
        if not items:
            return "今日暂无可发布信号，建议检查抓取源健康和筛选阈值。"
        themes = self._top_labels([self._infer_theme(row) for row in items], limit=3)
        theme_text = "、".join([name for name, _ in themes]) or "新兴技术与生态信号"
        top_sources = self._top_labels([str(row.get("source", "unknown")) for row in items], limit=2)
        if top_sources and top_sources[0][1] > 1:
            source_text = f"信息源相对集中在 {top_sources[0][0]}"
        else:
            source_text = "信息源分散，未出现单一媒体主导"
        top_title = self._short_text(str(items[0].get("title", "核心事件")), 28)
        return (
            f"今天内容主线集中在 {theme_text}。{source_text}，"
            f"其中「{top_title}」是最值得优先跟进的高优先级事件。"
        )

    def _fallback_focus_text(self, items: List[Dict]) -> str:
        if not items:
            return "当前信号不足，建议暂不做结论性判断。"
        trend_counts = self._top_labels([self._trend_cn(str(row.get("event_trend_3d", "new"))) for row in items], limit=2)
        trend_text = "、".join([f"{name}{count}条" for name, count in trend_counts]) if trend_counts else "趋势信号不足"
        top_a = self._short_text(str(items[0].get("title", "核心事件")), 24)
        top_b = self._short_text(str(items[1].get("title", "")), 20) if len(items) > 1 else ""
        if top_b:
            return (
                f"编辑判断：短期以{trend_text}为主，增量信息密度较高。"
                f"需重点观察「{top_a}」与「{top_b}」是否形成连续性信号，避免将单日情绪误判为趋势反转。"
            )
        return f"编辑判断：短期以{trend_text}为主。需持续跟踪「{top_a}」的后续证据，避免过度外推。"

    def _default_key_points(self, items: List[Dict]) -> List[str]:
        if not items:
            return ["暂无要点"]
        points = []
        for row in items[:3]:
            title = self._short_text(str(row.get("title", "Untitled")), 24)
            summary = self._short_text(str(row.get("summary", "")), 36)
            points.append(f"{title}：{summary}")
        return points

    @staticmethod
    def _sanitize_text(value: Any, fallback: str) -> str:
        text = str(value or "").strip()
        return text if text else fallback

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
    def _parse_json_object(text: str) -> Dict[str, Any]:
        raw = str(text or "").strip()
        if "```json" in raw:
            raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in raw:
            raw = raw.split("```", 1)[1].split("```", 1)[0].strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", raw)
            if not match:
                return {}
            try:
                return json.loads(match.group(0))
            except Exception:
                return {}

    @staticmethod
    def _short_text(text: str, limit: int = 24) -> str:
        clean = str(text or "").strip()
        if len(clean) <= limit:
            return clean
        return f"{clean[: max(1, limit - 1)]}…"

    @staticmethod
    def _top_labels(values: List[str], limit: int = 3) -> List[tuple]:
        counts: Dict[str, int] = {}
        for value in values:
            key = str(value or "unknown").strip() or "unknown"
            counts[key] = counts.get(key, 0) + 1
        ranked = sorted(counts.items(), key=lambda row: row[1], reverse=True)
        return ranked[:limit]

    @staticmethod
    def _trend_cn(value: str) -> str:
        raw = str(value or "new").strip().lower()
        if raw == "up":
            return "升温"
        if raw == "flat":
            return "持平"
        if raw == "down":
            return "降温"
        return "新增"

    @staticmethod
    def _infer_theme(item: Dict) -> str:
        text = (
            f"{item.get('category', '')} {item.get('title', '')} {item.get('summary', '')}"
        ).lower()
        if re.search(r"(监管|银行|合规|fed|stablecoin|法务|清算)", text):
            return "监管与资金通道"
        if re.search(r"(perp|衍生|dex|流动性|成交|funding|btc|宏观|market)", text):
            return "市场结构与流动性"
        if re.search(r"(ai|infra|browser|数据|计算|engine|ml|machine learning)", text):
            return "AI 基础设施"
        if re.search(r"(rwa|tokenization)", text):
            return "RWA 与资产上链"
        return "新兴技术与生态信号"

    def generate_distribution_drafts(
        self,
        items: List[Dict],
        digest: Dict[str, Any],
        date: str = None,
        max_items: int = 3,
    ) -> str:
        """Generate reusable drafts for multiple channels from digest + top signals."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        ranked = sorted(items, key=lambda row: int(row.get("importance", 0) or 0), reverse=True)
        top_items = ranked[:max_items]
        title = self._sanitize_text(digest.get("title"), "今日内容总结")
        summary = self._strip_action_phrases(
            self._sanitize_text(digest.get("summary_paragraph"), self._fallback_summary_text(top_items))
        )
        focus = self._strip_action_phrases(
            self._sanitize_text(digest.get("focus_paragraph"), self._fallback_focus_text(top_items))
        )
        key_points = digest.get("key_points") or self._default_key_points(top_items)
        key_points = [self._sanitize_text(row, "") for row in key_points if self._sanitize_text(row, "")]

        x_hook = f"今天最值得关注的主线：{title}"
        x_lines = [
            x_hook,
            self._short_text(summary, 130),
            self._short_text(focus, 120),
        ]
        if key_points:
            x_lines.append("要点：")
            x_lines.extend([f"- {self._short_text(point, 40)}" for point in key_points[:2]])
        x_lines.append("#Web3 #Crypto #AI")
        x_post = "\n".join([line for line in x_lines if line])

        linkedin_lines = [
            f"Today’s Web3 Editorial Brief: {title}",
            "",
            summary,
            "",
            focus,
            "",
            "Key takeaways:",
        ]
        linkedin_lines.extend([f"- {point}" for point in key_points[:3]])
        linkedin_lines.append("")
        linkedin_lines.append("What are you seeing on the desk today?")

        newsletter_intro = (
            f"今天我们把市场噪音压缩成一条可判断主线：{title}。"
            f"{self._short_text(summary, 96)}"
        )

        payload = {
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "source_digest_title": title,
            "channels": {
                "x_thread_cn": {
                    "hook": x_hook,
                    "post": x_post,
                },
                "linkedin_post_en": {
                    "title": f"Web3 Daily Signal: {title}",
                    "post": "\n".join(linkedin_lines),
                },
                "newsletter_intro_cn": {
                    "subject_candidate": f"今日主线：{title}",
                    "intro": newsletter_intro,
                },
            },
            "top_signals": [
                {
                    "title": row.get("title", ""),
                    "source": row.get("source", "unknown"),
                    "importance": int(row.get("importance", 0) or 0),
                }
                for row in top_items
            ],
        }

        filepath = os.path.join(self.output_dir, f"{date}-distribution-drafts.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return filepath

    def _build_queue_item(self, item: Dict) -> Dict:
        title = str(item.get("title", "Untitled")).strip()
        summary = str(item.get("summary", "")).strip() or "Signal worth tracking today."
        editorial_angle = str(item.get("editorial_angle", "")).strip()
        market_impact = str(item.get("market_impact", "")).strip()
        evidence_points = str(item.get("evidence_points", "")).strip()
        execution_risk = str(item.get("execution_risk", "")).strip()
        importance = int(item.get("importance", 0) or 0)
        mixed_summary, mixed_impact, mixed_risk = self._extract_structured_fields(editorial_angle or summary)
        if mixed_summary:
            summary = mixed_summary
        if not market_impact:
            market_impact = mixed_impact
        if not execution_risk:
            execution_risk = mixed_risk
        narrative_summary = self._strip_leading_label(
            self._strip_action_phrases(summary),
            "判断",
        )
        narrative_summary = self._strip_leading_label(narrative_summary, "立场")
        narrative_summary = self._strip_leading_label(narrative_summary, "观点")
        narrative_summary = self._strip_leading_label(narrative_summary, "结论")
        market_impact = self._strip_leading_label(
            self._strip_action_phrases(market_impact),
            "影响",
        )
        market_impact = self._strip_leading_label(market_impact, "市场影响")
        market_impact = self._strip_leading_label(market_impact, "影响对象")
        execution_risk = self._strip_leading_label(execution_risk, "风险")
        execution_risk = self._strip_leading_label(execution_risk, "风险边界")
        execution_risk = self._strip_leading_label(execution_risk, "不确定性")
        narrative_summary = self._tighten_sentence(narrative_summary, max_chars=76)
        market_impact = self._tighten_sentence(market_impact, max_chars=100)
        execution_risk = self._tighten_sentence(execution_risk, max_chars=72)
        evidence_points = self._normalize_evidence_points(evidence_points, item, importance)
        action_item = str(item.get("action_item", "")).strip() or f"Review '{title}' and define an execution step."
        source_key = str(item.get("source", "unknown")).strip()
        source_label = SOURCE_LABELS.get(source_key, source_key)
        evidence_strength = self._score_evidence_strength(source_key, evidence_points)
        post = self._build_post_text(
            title=title,
            summary=narrative_summary,
            action_item=action_item,
            importance=importance,
            market_impact=market_impact,
            include_action=self.include_action_lines,
        )
        report = self._build_report_text(
            title=title,
            summary=narrative_summary,
            action_item=action_item,
            source=source_label,
            importance=importance,
            market_impact=market_impact,
            evidence_points=evidence_points,
            include_action=self.include_action_lines,
        )
        hooks = self._build_hook_variants(summary=narrative_summary, importance=importance)
        post_variants = {
            "A": self._apply_hook(post, hooks["A"]),
            "B": self._apply_hook(post, hooks["B"]),
        }
        return {
            "title": title,
            "url": item.get("url", ""),
            "source": source_key,
            "category": item.get("category", "Other"),
            "importance": importance,
            "summary": narrative_summary,
            "action_item": action_item,
            "editorial_angle": editorial_angle,
            "market_impact": market_impact,
            "evidence_points": evidence_points,
            "evidence_strength": evidence_strength,
            "owner": item.get("owner", "研究员"),
            "deadline": item.get("deadline", ""),
            "expected_gain": item.get("expected_gain", ""),
            "execution_risk": execution_risk,
            "event_id": item.get("event_id", ""),
            "event_seen_last_3d": item.get("event_seen_last_3d", 0),
            "event_seen_last_7d": item.get("event_seen_last_7d", 0),
            "event_trend_3d": item.get("event_trend_3d", "new"),
            "event_trend_7d": item.get("event_trend_7d", "new"),
            "post": post,
            "report": report,
            "hook_variants": hooks,
            "post_variants": post_variants,
            "selected_variant": "A",
            "template_hit": True,
        }

    @staticmethod
    def _build_post_text(
        title: str,
        summary: str,
        action_item: str,
        importance: int,
        market_impact: str = "",
        include_action: bool = False,
    ) -> str:
        lines = [f"{title} | score {importance}/10", summary]
        if market_impact:
            lines.append(f"Impact: {market_impact}")
        if include_action:
            lines.append(f"Next: {action_item}")
        lines.append("#Web3")
        return "\n".join(lines)

    @staticmethod
    def _build_report_text(
        title: str,
        summary: str,
        action_item: str,
        source: str,
        importance: int,
        market_impact: str = "",
        evidence_points: str = "",
        include_action: bool = False,
    ) -> str:
        lines = [
            f"Title: {title}",
            f"Source: {source}",
            f"Importance: {importance}/10",
            f"Summary: {summary}",
        ]
        if market_impact:
            lines.append(f"Market Impact: {market_impact}")
        if evidence_points:
            lines.append(f"Evidence: {evidence_points}")
        if include_action:
            lines.append(f"Action: {action_item}")
        return "\n".join(lines)

    @staticmethod
    def _build_hook_variants(summary: str, importance: int) -> Dict[str, str]:
        snippet = summary[:20] if summary else "key signal"
        return {
            "A": "观点A: 这不是噪音，是结构性变化。",
            "B": f"观点B: 重要度 {importance}/10，重点是 {snippet}。",
        }

    @staticmethod
    def _score_evidence_strength(source: str, evidence_points: str) -> str:
        source_key = str(source or "").strip().lower()
        high_cred = {"coindesk", "cointelegraph", "theblock", "defillama", "github", "blockworks"}
        medium_cred = {"reddit", "hackernews", "x", "telegram"}
        points = [p.strip() for p in re.split(r"[；;]", str(evidence_points or "")) if p.strip()]
        point_count = len(points)

        if source_key in high_cred and point_count >= 2:
            return "A"
        if (source_key in high_cred and point_count >= 1) or (source_key in medium_cred and point_count >= 2):
            return "B"
        return "C"

    @staticmethod
    def _strip_leading_label(text: str, label: str) -> str:
        out = str(text or "").strip()
        if not out:
            return out
        pattern = re.compile(rf"^(?:{re.escape(label)}[：:]\s*)+")
        return pattern.sub("", out).strip() or out

    @staticmethod
    def _apply_hook(post: str, hook: str) -> str:
        lines = [ln for ln in str(post or "").splitlines() if ln.strip()]
        body = lines
        if lines and lines[0].startswith("观点"):
            body = lines[1:]
        if hook:
            return "\n".join([hook] + body)
        return "\n".join(body)

    @staticmethod
    def _extract_structured_fields(text: str) -> tuple[str, str, str]:
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
    def _tighten_sentence(text: str, max_chars: int = 80) -> str:
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
    def _normalize_evidence_points(evidence_points: str, item: Dict[str, Any], importance: int) -> str:
        points = [p.strip() for p in re.split(r"[；;]", str(evidence_points or "")) if p.strip()]
        has_numeric = any(re.search(r"\d", p) for p in points)
        numeric_point = ""

        if not has_numeric:
            stars = str(item.get("engagement", "")).strip()
            if stars:
                numeric_point = f"GitHub Stars {stars}，显示社区关注度"
            else:
                pub = str(item.get("published_date", "")).strip()
                if pub:
                    numeric_point = f"发布时间 {pub}，属于当期增量事件"
                else:
                    numeric_point = f"重要性评分 {importance}/10"

        if not points:
            points = [numeric_point or f"重要性评分 {importance}/10"]
        elif numeric_point:
            if len(points) >= 2:
                points = [points[0], numeric_point]
            else:
                points.append(numeric_point)

        deduped: List[str] = []
        seen = set()
        for p in points:
            if p in seen:
                continue
            seen.add(p)
            deduped.append(p)
            if len(deduped) >= 2:
                break
        return "；".join(deduped)
