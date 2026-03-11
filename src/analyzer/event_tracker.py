"""Event deduplication and 3/7-day trend tracking."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from src.models.content_item import ContentItem

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
    "will",
    "after",
    "new",
}

_DROP_QUERY_PREFIXES = (
    "utm_",
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
)


def canonicalize_url(url: str) -> str:
    """Normalize URL for cross-source deduplication."""
    raw = str(url or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
    except Exception:
        return raw
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path.rstrip("/")
    if not path:
        path = "/"
    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=False)
        if not any(k.lower().startswith(prefix) for prefix in _DROP_QUERY_PREFIXES)
    ]
    query = urlencode(sorted(query_pairs))
    return urlunparse((scheme, netloc, path, "", query, ""))


def tokenize_event_text(text: str) -> List[str]:
    """Tokenize text for event-level similarity matching."""
    clean = re.sub(r"\s+", " ", str(text or "").strip().lower())
    if not clean:
        return []
    words = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{1,4}", clean)
    tokens = []
    for tok in words:
        if tok in _STOPWORDS:
            continue
        tokens.append(tok)
    # Add bi-grams for CJK to improve title matching.
    cjk = re.findall(r"[\u4e00-\u9fff]", clean)
    for i in range(max(0, len(cjk) - 1)):
        tokens.append("".join(cjk[i : i + 2]))
    return list(dict.fromkeys(tokens))


def _jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    sa = set(a)
    sb = set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(1, len(sa | sb))


def _source_priority(source: str) -> int:
    order = {
        "openai_blog": 6,
        "deepmind_blog": 6,
        "x": 4,
        "theblock": 5,
        "blockworks": 5,
        "coindesk": 5,
        "cointelegraph": 4,
        "github": 4,
        "hackernews": 3,
        "reddit": 2,
    }
    return order.get(str(source or "").lower(), 1)


def _to_int(value: Any) -> int:
    try:
        return int(str(value or "0").replace(",", ""))
    except Exception:
        return 0


def _item_rank_score(item: ContentItem) -> float:
    return (
        float(_source_priority(item.source.value)) * 10_000.0
        + float(_to_int(item.engagement))
        + float(len(item.description or ""))
    )


def _cluster_event_id(tokens: Sequence[str], canonical_urls: Sequence[str]) -> str:
    token_key = "|".join(sorted(tokens)[:10])
    url_key = "|".join(sorted(canonical_urls)[:3])
    digest = hashlib.sha1(f"{token_key}|{url_key}".encode("utf-8")).hexdigest()[:12]
    return f"evt_{digest}"


@dataclass
class _Cluster:
    items: List[ContentItem]
    tokens: List[str]
    canonical_urls: List[str]


def deduplicate_items_by_event(
    items: Sequence[ContentItem],
    similarity_threshold: float = 0.58,
) -> Tuple[List[ContentItem], Dict[str, Dict[str, Any]]]:
    """Deduplicate same events across sources and return metadata by canonical URL."""
    clusters: List[_Cluster] = []

    for item in items:
        canonical_url = canonicalize_url(item.url)
        tokens = tokenize_event_text(f"{item.title} {item.description}")
        best_idx = -1
        best_score = 0.0

        for idx, cluster in enumerate(clusters):
            if canonical_url and canonical_url in cluster.canonical_urls:
                best_idx = idx
                break
            score = _jaccard(tokens, cluster.tokens)
            if score >= similarity_threshold and score > best_score:
                best_idx = idx
                best_score = score

        if best_idx == -1:
            clusters.append(
                _Cluster(
                    items=[item],
                    tokens=tokens,
                    canonical_urls=[canonical_url] if canonical_url else [],
                )
            )
            continue

        cluster = clusters[best_idx]
        cluster.items.append(item)
        cluster.tokens = list(dict.fromkeys([*cluster.tokens, *tokens]))
        if canonical_url and canonical_url not in cluster.canonical_urls:
            cluster.canonical_urls.append(canonical_url)

    deduped: List[ContentItem] = []
    metadata_by_url: Dict[str, Dict[str, Any]] = {}

    for cluster in clusters:
        representative = sorted(
            cluster.items,
            key=lambda item: _item_rank_score(item),
            reverse=True,
        )[0]
        deduped.append(representative)
        event_id = _cluster_event_id(cluster.tokens, cluster.canonical_urls)
        sources = sorted({it.source.value for it in cluster.items})
        urls = [canonicalize_url(it.url) for it in cluster.items if canonicalize_url(it.url)]
        titles = list(dict.fromkeys([str(it.title or "").strip() for it in cluster.items if str(it.title or "").strip()]))
        metadata = {
            "event_id": event_id,
            "event_duplicate_count": len(cluster.items),
            "event_source_count": len(sources),
            "event_sources": sources,
            "event_urls": list(dict.fromkeys(urls))[:8],
            "event_headlines": titles[:5],
        }
        rep_url = canonicalize_url(representative.url)
        if rep_url:
            metadata_by_url[rep_url] = metadata

    return deduped, metadata_by_url


class EventTracker:
    """Track event evolution and annotate 3/7-day trend context."""

    def __init__(self, output_dir: str, run_date: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.output_dir / "event_history.json"
        self.run_date = run_date
        self._history = self._load_history()

    def annotate(self, analyzed_items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Attach 3-day and 7-day trend context for each event."""
        annotated: List[Dict[str, Any]] = []
        for item in analyzed_items:
            event_id = str(item.get("event_id", "")).strip()
            if not event_id:
                event_id = self._fallback_event_id(item)
                item = {**item, "event_id": event_id}
            recent3 = self._recent_occurrences(event_id, days=3)
            recent7 = self._recent_occurrences(event_id, days=7)
            trend3 = self._infer_trend(item, recent3, recent7, window=3)
            trend7 = self._infer_trend(item, recent7, recent7, window=7)
            last_seen = recent7[-1]["date"] if recent7 else "new"
            enriched = {
                **item,
                "event_seen_last_3d": len(recent3),
                "event_seen_last_7d": len(recent7),
                "event_trend_3d": trend3,
                "event_trend_7d": trend7,
                "event_last_seen": last_seen,
            }
            annotated.append(enriched)
        return annotated

    def update(self, analyzed_items: Sequence[Dict[str, Any]]) -> None:
        """Persist current run events to history for future 3/7-day comparisons."""
        events = self._history.setdefault("events", {})
        day_rows: Dict[str, Dict[str, Any]] = {}
        for item in analyzed_items:
            event_id = str(item.get("event_id", "")).strip()
            if not event_id:
                continue
            day_rows[event_id] = {
                "date": self.run_date,
                "importance": int(item.get("importance", 0) or 0),
                "title": str(item.get("title", "")),
                "url": str(item.get("url", "")),
                "sources": list(item.get("event_sources", [])),
                "source_count": int(item.get("event_source_count", 1) or 1),
            }

        for event_id, row in day_rows.items():
            event_state = events.setdefault(event_id, {"occurrences": []})
            occurrences = event_state.setdefault("occurrences", [])
            occurrences = [o for o in occurrences if str(o.get("date", "")) != self.run_date]
            occurrences.append(row)
            occurrences.sort(key=lambda o: str(o.get("date", "")))
            cutoff = datetime.now(timezone.utc).date() - timedelta(days=90)
            event_state["occurrences"] = [
                o
                for o in occurrences
                if self._parse_date(str(o.get("date", ""))) >= cutoff
            ]
            event_state["first_seen"] = event_state["occurrences"][0]["date"]
            event_state["last_seen"] = event_state["occurrences"][-1]["date"]

        self._history["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.history_file.write_text(
            json.dumps(self._history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_history(self) -> Dict[str, Any]:
        if not self.history_file.exists():
            return {"events": {}}
        try:
            return json.loads(self.history_file.read_text(encoding="utf-8"))
        except Exception:
            return {"events": {}}

    def _recent_occurrences(self, event_id: str, days: int) -> List[Dict[str, Any]]:
        events = self._history.get("events", {})
        event_state = events.get(event_id, {}) if isinstance(events, dict) else {}
        occurrences = event_state.get("occurrences", []) if isinstance(event_state, dict) else []
        now_day = self._parse_date(self.run_date)
        cutoff = now_day - timedelta(days=max(1, int(days)))
        rows: List[Dict[str, Any]] = []
        for row in occurrences:
            date_str = str(row.get("date", "")).strip()
            day = self._parse_date(date_str)
            if cutoff <= day < now_day:
                rows.append(row)
        rows.sort(key=lambda r: str(r.get("date", "")))
        return rows

    def _infer_trend(
        self,
        item: Dict[str, Any],
        rows: Sequence[Dict[str, Any]],
        baseline_rows: Sequence[Dict[str, Any]],
        window: int,
    ) -> str:
        if not baseline_rows:
            return "new"
        current = int(item.get("importance", 0) or 0)
        baseline = sum(int(r.get("importance", 0) or 0) for r in baseline_rows) / max(1, len(baseline_rows))
        if len(rows) >= max(2, window // 2) or current >= baseline + 1:
            return "rising"
        if current <= baseline - 1:
            return "cooling"
        return "steady"

    @staticmethod
    def _parse_date(value: str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except Exception:
            return datetime.now(timezone.utc).date()

    @staticmethod
    def _fallback_event_id(item: Dict[str, Any]) -> str:
        title = str(item.get("title", ""))
        digest = hashlib.sha1(title.encode("utf-8")).hexdigest()[:12]
        return f"evt_{digest}"
