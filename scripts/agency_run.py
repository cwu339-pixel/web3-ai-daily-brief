#!/usr/bin/env python3
"""Lightweight agency runner for daily brief gating.

Pipeline:
1) Load daily outputs
2) QA block (run-level gates)
3) Research gate (item-level gates)
4) Editor output (fixed story format)
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_latest_date(output_dir: Path) -> str:
    files = sorted(output_dir.glob("*-social-queue.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"No *-social-queue.json found in {output_dir}")
    return files[0].name.split("-social-queue.json")[0]


def _clean(text: str, limit: int) -> str:
    raw = str(text or "").strip()
    if len(raw) <= limit:
        return raw
    return raw[: max(1, limit - 1)].rstrip("，,；; ") + "…"


def _has_hard_evidence(evidence: str) -> bool:
    text = str(evidence or "")
    return bool(re.search(r"\d", text) or re.search(r"\b(UTC|GMT|\d{4}-\d{2}-\d{2})\b", text, re.IGNORECASE))


def qa_block(
    quality: Dict[str, Any],
    min_success_rate: float,
    min_selected_count: int,
    require_zero_fallback: bool,
) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    success_rate = float(quality.get("success_rate", 0.0) or 0.0)
    selected_count = int(quality.get("selected_count", 0) or 0)
    fallback_count = int(quality.get("fallback_count", 0) or 0)

    if success_rate < min_success_rate:
        reasons.append(f"success_rate {success_rate:.1f}% < {min_success_rate:.1f}%")
    if selected_count < min_selected_count:
        reasons.append(f"selected_count {selected_count} < {min_selected_count}")
    if require_zero_fallback and fallback_count > 0:
        reasons.append(f"fallback_count {fallback_count} > 0")

    return len(reasons) == 0, reasons


def research_gate(
    items: List[Dict[str, Any]],
    min_importance: int,
    require_hard_evidence: bool,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    approved: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    for item in sorted(items, key=lambda x: int(x.get("importance", 0) or 0), reverse=True):
        importance = int(item.get("importance", 0) or 0)
        evidence = str(item.get("evidence_points", "") or "")
        reasons: List[str] = []

        if importance < min_importance:
            reasons.append(f"importance<{min_importance}")
        if require_hard_evidence and not _has_hard_evidence(evidence):
            reasons.append("missing_hard_evidence")

        if reasons:
            rejected.append(
                {
                    "title": item.get("title", ""),
                    "source": item.get("source", ""),
                    "importance": importance,
                    "reasons": reasons,
                }
            )
        else:
            approved.append(item)

    return approved, rejected


def build_editor_card(date: str, digest: Dict[str, Any], approved: List[Dict[str, Any]]) -> str:
    title = str(digest.get("title", "今日主线")).strip()
    one_line = _clean(str(digest.get("summary_paragraph", "")).strip(), 120)
    impact_risk = _clean(str(digest.get("focus_paragraph", "")).strip(), 140)

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

    for item in approved[:6]:
        lines.extend(
            [
                str(item.get("title", "Untitled")).strip(),
                f"判断：{_clean(str(item.get('summary', '')).strip(), 78) or '-'}",
                f"影响：{_clean(str(item.get('market_impact', '')).strip(), 96) or '-'}",
                f"风险：{_clean(str(item.get('execution_risk', '')).strip(), 72) or '-'}",
                f"证据：{_clean(str(item.get('evidence_points', '')).strip(), 88) or '-'}",
                "",
            ]
        )

    if not approved:
        lines.extend(["（无通过项）", "判断：-", "影响：-", "风险：-", "证据：-", ""])

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run agency gates on daily brief outputs")
    parser.add_argument("--date", default="", help="YYYY-MM-DD, default latest")
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--min-importance", type=int, default=9)
    parser.add_argument("--min-selected-count", type=int, default=5)
    parser.add_argument("--min-success-rate", type=float, default=80.0)
    parser.add_argument("--allow-fallback", action="store_true", help="Allow fallback_count > 0")
    parser.add_argument("--allow-soft-evidence", action="store_true", help="Do not require numeric/time evidence")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    date = args.date.strip() or _find_latest_date(output_dir)

    queue_file = output_dir / f"{date}-social-queue.json"
    digest_file = output_dir / f"{date}-digest.json"
    quality_file = output_dir / f"{date}-quality-cost.json"

    queue_payload = _read_json(queue_file)
    digest = _read_json(digest_file)
    quality = _read_json(quality_file)

    items = queue_payload.get("items", []) or []

    qa_passed, qa_reasons = qa_block(
        quality=quality,
        min_success_rate=args.min_success_rate,
        min_selected_count=args.min_selected_count,
        require_zero_fallback=not args.allow_fallback,
    )
    approved, rejected = research_gate(
        items=items,
        min_importance=args.min_importance,
        require_hard_evidence=not args.allow_soft_evidence,
    )

    agency_gate = {
        "date": date,
        "generated_at": datetime.now().isoformat(),
        "qa": {
            "passed": qa_passed,
            "reasons": qa_reasons,
            "min_success_rate": args.min_success_rate,
            "min_selected_count": args.min_selected_count,
            "require_zero_fallback": not args.allow_fallback,
            "metrics": {
                "success_rate": quality.get("success_rate", 0.0),
                "selected_count": quality.get("selected_count", 0),
                "fallback_count": quality.get("fallback_count", 0),
            },
        },
        "research": {
            "min_importance": args.min_importance,
            "require_hard_evidence": not args.allow_soft_evidence,
            "approved_count": len(approved),
            "rejected_count": len(rejected),
            "rejected": rejected,
        },
        "publish_ready": bool(qa_passed and len(approved) > 0),
        "top_titles": [str(i.get("title", "")) for i in approved[:6]],
    }

    gate_file = output_dir / f"{date}-agency-gate.json"
    gate_file.write_text(json.dumps(agency_gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    card_text = build_editor_card(date=date, digest=digest, approved=approved)
    card_file = output_dir / f"{date}-agency-card.md"
    card_file.write_text(card_text, encoding="utf-8")

    print(f"date={date}")
    print(f"qa_passed={qa_passed}")
    print(f"approved={len(approved)} rejected={len(rejected)}")
    print(f"publish_ready={agency_gate['publish_ready']}")
    print(f"gate_file={gate_file}")
    print(f"card_file={card_file}")


if __name__ == "__main__":
    main()
