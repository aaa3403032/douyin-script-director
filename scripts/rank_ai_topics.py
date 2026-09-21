#!/usr/bin/env python3
"""Rank AI content candidates with an auditable, non-predictive score.

The script does not crawl the web and does not predict views. Research tools
collect evidence; this helper validates the evidence ledger, normalizes scores,
flags risky trend language, and produces a reproducible ranking.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


WEIGHTS = {
    "balanced": {
        "heat": 4,
        "audience_relevance": 4,
        "evidence_strength": 3,
        "real_world_consequence": 3,
        "freshness": 2,
        "conflict_novelty": 2,
        "teachability": 1,
        "visual_evidence": 1,
    },
    "news": {
        "heat": 5,
        "audience_relevance": 4,
        "evidence_strength": 4,
        "real_world_consequence": 3,
        "freshness": 4,
        "conflict_novelty": 3,
        "teachability": 0,
        "visual_evidence": 1,
    },
    "tutorial": {
        "heat": 2,
        "audience_relevance": 4,
        "evidence_strength": 3,
        "real_world_consequence": 3,
        "freshness": 1,
        "conflict_novelty": 1,
        "teachability": 5,
        "visual_evidence": 3,
    },
    "technical": {
        "heat": 1,
        "audience_relevance": 4,
        "evidence_strength": 4,
        "real_world_consequence": 4,
        "freshness": 2,
        "conflict_novelty": 1,
        "teachability": 5,
        "visual_evidence": 4,
    },
}

TRACKS = {"breaking", "rising", "technical"}
DEFAULT_MINIMUM_SCORE = 70.0
MAX_DISPLAY_COUNT = 10

HOT_LANGUAGE = re.compile(
    r"全网最火|最有流量|流量最大|刷屏|暴涨|霸榜|爆了|都在讨论|热度飙升|"
    r"hottest|viral|trending everywhere",
    re.I,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rank evidence-backed AI topics; this is not a view predictor."
    )
    parser.add_argument("path", nargs="?", help="UTF-8 radar.json input")
    parser.add_argument(
        "--mode",
        choices=sorted(WEIGHTS),
        help="Override run.mode (balanced, news, tutorial, or technical)",
    )
    parser.add_argument("--markdown", help="Optional Markdown output path")
    parser.add_argument("--json", dest="json_output", help="Optional JSON output path")
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum qualified cards to display (1-10); default is dynamic up to 10",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run the schema-v2 dynamic-list regression test",
    )
    return parser.parse_args()


def load_input(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Top-level input must be an object")
    if not isinstance(data.get("run"), dict):
        raise ValueError("Missing object: run")
    if not isinstance(data.get("topics"), list) or not data["topics"]:
        raise ValueError("topics must be a non-empty array")
    return data


def parse_iso_date(value: str, label: str) -> None:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be ISO-8601: {value!r}") from exc


def validate_run(run: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("captured_at", "timezone", "region", "audience"):
        if not run.get(field):
            errors.append(f"run.{field} is required")
    if run.get("captured_at"):
        try:
            parse_iso_date(str(run["captured_at"]), "run.captured_at")
        except ValueError as exc:
            errors.append(str(exc))
    if not isinstance(run.get("windows"), dict) or not run["windows"]:
        errors.append("run.windows must record at least one research window")
    schema_version = run.get("schema_version", 1)
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        errors.append("run.schema_version must be an integer")
    elif schema_version >= 2:
        research = run.get("research")
        if not isinstance(research, dict):
            errors.append("run.research is required for schema_version >= 2")
        else:
            for field in ("started_at", "ended_at"):
                if not research.get(field):
                    errors.append(f"run.research.{field} is required")
                else:
                    try:
                        parse_iso_date(
                            str(research[field]), f"run.research.{field}"
                        )
                    except ValueError as exc:
                        errors.append(str(exc))
            passes = research.get("passes")
            if not isinstance(passes, list) or len(passes) < 3:
                errors.append("run.research.passes must record at least three passes")
            baskets = research.get("source_baskets")
            if not isinstance(baskets, list) or len(set(map(str, baskets))) < 5:
                errors.append(
                    "run.research.source_baskets must cover five source baskets"
                )
            for field in (
                "query_count",
                "source_family_count",
                "raw_signal_count",
                "clustered_candidate_count",
                "qualified_candidate_count",
            ):
                value = research.get(field)
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    errors.append(f"run.research.{field} must be a non-negative integer")
        threshold = run.get("minimum_opportunity_score", DEFAULT_MINIMUM_SCORE)
        if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
            errors.append("run.minimum_opportunity_score must be numeric")
        elif not 0 <= float(threshold) <= 100:
            errors.append("run.minimum_opportunity_score must be between 0 and 100")
    return errors


def source_counts(topic: dict[str, Any]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for source in topic.get("sources", []):
        if isinstance(source, dict):
            counts[str(source.get("kind", "unknown"))] += 1
    return counts


def penalty_total(topic: dict[str, Any], warnings: list[str]) -> float:
    total = 0.0
    penalties = topic.get("risk_penalties", [])
    if not isinstance(penalties, list):
        warnings.append("risk_penalties must be an array; ignored")
        return total
    for item in penalties:
        if not isinstance(item, dict):
            warnings.append("invalid risk penalty entry ignored")
            continue
        try:
            points = float(item.get("points", 0))
        except (TypeError, ValueError):
            warnings.append(f"invalid penalty points: {item.get('points')!r}")
            continue
        if points < 0:
            warnings.append("negative risk penalty ignored")
            continue
        total += points
    return total


def validate_topic(
    topic: dict[str, Any], weights: dict[str, int], index: int, schema_version: int
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    label = str(topic.get("id") or f"topic-{index}")

    for field in ("id", "title", "evidence_grade", "allowed_heat_wording"):
        if not topic.get(field):
            errors.append(f"{label}: {field} is required")

    track = str(topic.get("track", "")).lower()
    if not track:
        warnings.append(f"{label}: track is missing (breaking, rising, or technical)")
    elif track not in TRACKS:
        errors.append(f"{label}: track must be breaking, rising, or technical")

    grade = str(topic.get("evidence_grade", "")).upper()
    if grade not in {"A", "B", "C", "D"}:
        errors.append(f"{label}: evidence_grade must be A, B, C, or D")

    event_date = topic.get("event_date")
    if not event_date:
        warnings.append(f"{label}: event_date is missing")
    else:
        try:
            parse_iso_date(str(event_date), f"{label}.event_date")
        except ValueError as exc:
            errors.append(str(exc))

    if track in {"breaking", "rising"} and not event_date:
        errors.append(f"{label}: {track} topics require event_date")
    if track == "rising":
        latest_signal_at = topic.get("latest_signal_at")
        if not latest_signal_at:
            errors.append(f"{label}: rising topics require latest_signal_at")
        else:
            try:
                parse_iso_date(str(latest_signal_at), f"{label}.latest_signal_at")
            except ValueError as exc:
                errors.append(str(exc))
    if track == "technical":
        version_verified_at = topic.get("version_verified_at")
        if not version_verified_at:
            errors.append(f"{label}: technical topics require version_verified_at")
        else:
            try:
                parse_iso_date(
                    str(version_verified_at), f"{label}.version_verified_at"
                )
            except ValueError as exc:
                errors.append(str(exc))
        if not topic.get("demo_evidence"):
            errors.append(f"{label}: technical topics require demo_evidence")

    if schema_version >= 2:
        for field in (
            "content_summary",
            "audience_value",
            "why_now",
            "hook",
            "recommended_format",
            "visual_plan",
            "risk_boundary",
            "discussion_question",
        ):
            if not topic.get(field):
                errors.append(f"{label}: {field} is required for schema_version >= 2")
        talking_points = topic.get("talking_points")
        if not isinstance(talking_points, list) or len(talking_points) != 3:
            errors.append(f"{label}: talking_points must contain exactly three beats")
        duration = topic.get("recommended_duration_seconds")
        if not isinstance(duration, (int, float)) or isinstance(duration, bool):
            errors.append(f"{label}: recommended_duration_seconds must be numeric")
        elif not 30 <= float(duration) <= 300:
            errors.append(
                f"{label}: recommended_duration_seconds must be between 30 and 300"
            )
        if not isinstance(topic.get("production_ready"), bool):
            errors.append(f"{label}: production_ready must be boolean")
        review_at = topic.get("expires_at") or topic.get("next_review_at")
        if not review_at:
            errors.append(f"{label}: expires_at or next_review_at is required")
        else:
            try:
                parse_iso_date(str(review_at), f"{label}.review_at")
            except ValueError as exc:
                errors.append(str(exc))
        if track == "technical":
            demo_verified_at = topic.get("demo_verified_at")
            if not demo_verified_at:
                errors.append(
                    f"{label}: technical topics require demo_verified_at in schema v2"
                )
            else:
                try:
                    parse_iso_date(
                        str(demo_verified_at), f"{label}.demo_verified_at"
                    )
                except ValueError as exc:
                    errors.append(str(exc))

    scores = topic.get("scores")
    if not isinstance(scores, dict):
        errors.append(f"{label}: scores must be an object")
    else:
        for name in weights:
            value = scores.get(name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errors.append(f"{label}: scores.{name} must be numeric")
            elif not 0 <= float(value) <= 5:
                errors.append(f"{label}: scores.{name} must be between 0 and 5")

    sources = topic.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(f"{label}: sources must be a non-empty array")
        sources = []
    urls: list[str] = []
    families: list[str] = []
    for source in sources:
        if not isinstance(source, dict) or not source.get("url"):
            errors.append(f"{label}: each source needs a URL")
            continue
        urls.append(str(source["url"]))
        if source.get("family"):
            families.append(str(source["family"]).casefold())
    if len(urls) != len(set(urls)):
        warnings.append(f"{label}: duplicate source URL")

    counts = source_counts(topic)
    if counts["primary"] == 0:
        warnings.append(f"{label}: no primary source")
    if grade in {"A", "B"} and counts["attention"] == 0:
        warnings.append(f"{label}: A/B grade without an attention source")
    if grade == "A" and len(set(families)) < 2:
        warnings.append(f"{label}: A grade has fewer than two source families")

    heat_text = " ".join(
        str(topic.get(key, ""))
        for key in ("title", "why_now", "allowed_heat_wording", "hook")
    )
    if grade in {"C", "D"} and HOT_LANGUAGE.search(heat_text):
        warnings.append(f"{label}: C/D evidence uses strong popularity language")

    if not topic.get("screenshots"):
        warnings.append(f"{label}: no screenshot IDs recorded")
    return errors, warnings


def score_topic(topic: dict[str, Any], weights: dict[str, int]) -> tuple[float, float]:
    weighted = sum(float(topic["scores"][key]) * weight for key, weight in weights.items())
    maximum = 5 * sum(weights.values())
    base = weighted / maximum * 100 if maximum else 0.0
    local_warnings: list[str] = []
    penalty = penalty_total(topic, local_warnings)
    return round(max(0.0, min(100.0, base - penalty)), 1), round(penalty, 1)


def build_output(
    data: dict[str, Any], mode: str, requested_limit: int | None = None
) -> dict[str, Any]:
    weights = WEIGHTS[mode]
    errors = validate_run(data["run"])
    warnings: list[str] = []
    ranked: list[dict[str, Any]] = []
    schema_version = data["run"].get("schema_version", 1)
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        schema_version = 1
    minimum_score = float(
        data["run"].get("minimum_opportunity_score", DEFAULT_MINIMUM_SCORE)
    )

    seen_ids: set[str] = set()
    seen_angles: Counter[str] = Counter()
    for index, topic in enumerate(data["topics"], start=1):
        if not isinstance(topic, dict):
            errors.append(f"topic-{index}: must be an object")
            continue
        topic_errors, topic_warnings = validate_topic(
            topic, weights, index, schema_version
        )
        errors.extend(topic_errors)
        warnings.extend(topic_warnings)
        topic_id = str(topic.get("id", f"topic-{index}"))
        if topic_id in seen_ids:
            errors.append(f"duplicate topic id: {topic_id}")
        seen_ids.add(topic_id)
        if topic.get("angle_key"):
            seen_angles[str(topic["angle_key"]).casefold()] += 1

        if not topic_errors:
            score, penalty = score_topic(topic, weights)
            grade = str(topic["evidence_grade"]).upper()
            qualification_reasons: list[str] = []
            if score < minimum_score:
                qualification_reasons.append(
                    f"score {score:.1f} is below {minimum_score:.1f}"
                )
            if grade == "D":
                qualification_reasons.append("D-grade evidence belongs in watchlist")
            if source_counts(topic)["primary"] == 0:
                qualification_reasons.append("no primary source")
            if topic.get("production_ready") is False:
                qualification_reasons.append("production_ready is false")
            if topic.get("disqualified") is True:
                qualification_reasons.append("candidate is explicitly disqualified")
            ranked.append(
                {
                    "id": topic_id,
                    "title": topic["title"],
                    "angle_key": topic.get("angle_key", ""),
                    "track": str(topic.get("track", "unclassified")).lower(),
                    "evidence_grade": grade,
                    "opportunity_score": score,
                    "risk_penalty": penalty,
                    "score_breakdown": {
                        key: topic["scores"].get(key) for key in weights
                    },
                    "qualified": not qualification_reasons,
                    "qualification_reasons": qualification_reasons,
                    "event_date": topic.get("event_date"),
                    "latest_signal_at": topic.get("latest_signal_at"),
                    "version_verified_at": topic.get("version_verified_at"),
                    "demo_verified_at": topic.get("demo_verified_at"),
                    "content_summary": topic.get("content_summary", ""),
                    "talking_points": topic.get("talking_points", []),
                    "audience_value": topic.get("audience_value", ""),
                    "why_now": topic.get("why_now", ""),
                    "hook": topic.get("hook", ""),
                    "recommended_format": topic.get("recommended_format", ""),
                    "recommended_duration_seconds": topic.get(
                        "recommended_duration_seconds"
                    ),
                    "visual_plan": topic.get("visual_plan", ""),
                    "risk_boundary": topic.get("risk_boundary", ""),
                    "discussion_question": topic.get("discussion_question", ""),
                    "expires_at": topic.get("expires_at"),
                    "next_review_at": topic.get("next_review_at"),
                    "allowed_heat_wording": topic.get("allowed_heat_wording", ""),
                    "next_checks": topic.get("next_checks", []),
                    "screenshots": topic.get("screenshots", []),
                    "sources": [
                        {
                            "kind": source.get("kind"),
                            "family": source.get("family"),
                            "url": source.get("url"),
                        }
                        for source in topic.get("sources", [])
                        if isinstance(source, dict)
                    ],
                }
            )

    for angle, count in seen_angles.items():
        if count > 1:
            warnings.append(f"duplicate angle_key {angle!r} appears {count} times")

    ranked.sort(key=lambda item: (-item["opportunity_score"], item["id"]))
    for position, item in enumerate(ranked, start=1):
        item["rank"] = position

    display_limit = requested_limit or MAX_DISPLAY_COUNT
    qualified = [item for item in ranked if item["qualified"]]
    selected: list[dict[str, Any]] = []
    selected_angles: set[str] = set()
    for item in qualified:
        angle = str(item.get("angle_key", "")).casefold()
        if angle and angle in selected_angles:
            continue
        selected.append(item)
        if angle:
            selected_angles.add(angle)
        if len(selected) >= display_limit:
            break
    for display_rank, item in enumerate(selected, start=1):
        item["display_rank"] = display_rank
    if len(selected) < 5:
        warnings.append(
            f"only {len(selected)} candidates passed the qualification gate; do not pad to five"
        )
    selected_tracks = Counter(item["track"] for item in selected[:5])
    available_tracks = Counter(item["track"] for item in qualified)
    for track, floor in {"breaking": 2, "rising": 1, "technical": 1}.items():
        if available_tracks[track] >= floor and selected_tracks[track] < floor:
            warnings.append(
                f"top-five diversity review: {track} has qualified candidates but misses its floor {floor}"
            )

    return {
        "schema_version": schema_version,
        "mode": mode,
        "captured_at": data["run"].get("captured_at"),
        "region": data["run"].get("region"),
        "audience": data["run"].get("audience"),
        "research": data["run"].get("research", {}),
        "score_name": "内容机会分（非播放量预测）",
        "qualification_threshold": minimum_score,
        "display_limit": display_limit,
        "display_count": len(selected),
        "weights": weights,
        "ranked_topics": ranked,
        "selected_topics": selected,
        "warnings": sorted(set(warnings)),
        "errors": sorted(set(errors)),
    }


def render_markdown(output: dict[str, Any]) -> str:
    research = output.get("research") or {}
    lines = [
        "# AI选题雷达排序",
        "",
        f"- 模式：{output['mode']}",
        f"- 采集时间：{output.get('captured_at') or '未记录'}",
        f"- 地区：{output.get('region') or '未记录'}",
        f"- 受众：{output.get('audience') or '未记录'}",
        f"- 研究起止：{research.get('started_at') or '未记录'} → {research.get('ended_at') or '未记录'}",
        f"- 研究漏斗：{research.get('raw_signal_count', '未记录')} 原始信号 → {research.get('clustered_candidate_count', '未记录')} 聚类候选 → {output.get('display_count', 0)} 上榜",
        f"- 入榜线：{output.get('qualification_threshold', DEFAULT_MINIMUM_SCORE):.1f}分，D级证据不入主榜，上限{output.get('display_limit', MAX_DISPLAY_COUNT)}条。",
        "- 分数：内容机会分，不是播放量、爆款概率或平台推荐预测。",
        "",
        "| 排名 | 轨道 | 选题 | 等级 | 机会分 | 风险扣分 | 允许的热度表述 |",
        "|---:|---|---|:---:|---:|---:|---|",
    ]
    for item in output["selected_topics"]:
        wording = str(item["allowed_heat_wording"]).replace("|", "\\|")
        title = str(item["title"]).replace("|", "\\|")
        lines.append(
            f"| {item['display_rank']} | {item['track']} | {title} | {item['evidence_grade']} | "
            f"{item['opportunity_score']:.1f} | {item['risk_penalty']:.1f} | {wording} |"
        )
    for item in output["selected_topics"]:
        source_links = "；".join(
            f"[{source.get('kind') or '来源'}]({source.get('url')})"
            for source in item.get("sources", [])[:6]
            if source.get("url")
        )
        lines.extend(
            [
                "",
                f"## Top {item['display_rank']}｜{item['track']}｜{item['title']}",
                "",
                f"- 时间：事件 {item.get('event_date') or '不适用'}；最新信号 {item.get('latest_signal_at') or '不适用'}；版本核验 {item.get('version_verified_at') or '不适用'}；演示复现 {item.get('demo_verified_at') or '不适用'}",
                f"- 发生了什么：{item.get('content_summary') or '未记录'}",
                "- 口播三节拍："
                + " → ".join(str(x) for x in item.get("talking_points", [])),
                f"- 观众与收益：{item.get('audience_value') or '未记录'}",
                f"- 为什么现在做：{item.get('why_now') or '未记录'}",
                f"- 钩子：{item.get('hook') or '未记录'}",
                f"- 形态/时长：{item.get('recommended_format') or '未记录'} / {item.get('recommended_duration_seconds') or '未记录'}秒",
                f"- 画面：{item.get('visual_plan') or '未记录'}",
                f"- 分数：{item['opportunity_score']:.1f}/100；分项 {json.dumps(item.get('score_breakdown', {}), ensure_ascii=False)}；风险扣分 {item['risk_penalty']:.1f}",
                f"- 关键来源：{source_links or '未记录'}",
                f"- 边界：{item.get('risk_boundary') or '未记录'}",
                f"- 复核/有效期：{item.get('expires_at') or item.get('next_review_at') or '未记录'}",
                f"- 讨论问题：{item.get('discussion_question') or '未记录'}",
            ]
        )
    if output["warnings"]:
        lines.extend(["", "## 需要复核"])
        lines.extend(f"- {warning}" for warning in output["warnings"])
    if output["errors"]:
        lines.extend(["", "## 输入错误"])
        lines.extend(f"- {error}" for error in output["errors"])
    return "\n".join(lines) + "\n"


def run_self_test() -> None:
    run = {
        "schema_version": 2,
        "captured_at": "2026-09-21T16:00:00+08:00",
        "timezone": "Asia/Shanghai",
        "region": "CN",
        "audience": "Chinese AI creators",
        "mode": "balanced",
        "windows": {"breaking_hours": 72, "rising_days": 14},
        "minimum_opportunity_score": 70,
        "research": {
            "started_at": "2026-09-21T13:00:00+08:00",
            "ended_at": "2026-09-21T16:00:00+08:00",
            "passes": ["broad", "snowball", "gap-review"],
            "source_baskets": [
                "primary",
                "independent",
                "attention",
                "community",
                "tutorial",
            ],
            "query_count": 36,
            "source_family_count": 18,
            "raw_signal_count": 42,
            "clustered_candidate_count": 12,
            "qualified_candidate_count": 6,
        },
    }
    topics: list[dict[str, Any]] = []
    specifications = [
        ("b1", "breaking", 5.0),
        ("b2", "breaking", 4.7),
        ("r1", "rising", 4.5),
        ("t1", "technical", 4.4),
        ("r2", "rising", 4.1),
        ("t2", "technical", 3.9),
        ("low", "breaking", 3.0),
    ]
    for topic_id, track, score in specifications:
        topic: dict[str, Any] = {
            "id": topic_id,
            "title": f"Candidate {topic_id}",
            "angle_key": topic_id,
            "track": track,
            "evidence_grade": "B",
            "allowed_heat_wording": "recently received attention",
            "event_date": "2026-09-20T10:00:00+08:00",
            "content_summary": "A verified event with a concrete audience consequence.",
            "talking_points": ["result", "evidence or steps", "boundary"],
            "audience_value": "Helps the audience make a concrete decision.",
            "why_now": "A new verifiable signal appeared in the current window.",
            "hook": "The important change is not the headline but the new constraint.",
            "recommended_format": "explainer",
            "recommended_duration_seconds": 120,
            "visual_plan": "Show the primary page and a reproducible result.",
            "risk_boundary": "Do not generalize beyond the documented scope.",
            "discussion_question": "Which boundary would change your decision?",
            "next_review_at": "2026-09-22T12:00:00+08:00",
            "production_ready": True,
            "scores": {name: score for name in WEIGHTS["balanced"]},
            "risk_penalties": [],
            "sources": [
                {
                    "kind": "primary",
                    "family": f"official-{topic_id}",
                    "url": f"https://example.com/{topic_id}/primary",
                },
                {
                    "kind": "attention",
                    "family": f"signal-{topic_id}",
                    "url": f"https://example.net/{topic_id}/signal",
                },
            ],
            "screenshots": [f"shot-{topic_id}"],
        }
        if track == "rising":
            topic["latest_signal_at"] = "2026-09-21T11:00:00+08:00"
        if track == "technical":
            topic["version_verified_at"] = "2026-09-21T12:00:00+08:00"
            topic["demo_verified_at"] = "2026-09-21T12:30:00+08:00"
            topic["demo_evidence"] = "reproducible output"
        topics.append(topic)
    output = build_output({"run": run, "topics": topics}, "balanced")
    assert not output["errors"], output["errors"]
    assert output["display_count"] == 6, output["display_count"]
    assert len(output["ranked_topics"]) == 7
    assert output["selected_topics"][-1]["id"] == "t2"
    assert not next(x for x in output["ranked_topics"] if x["id"] == "low")[
        "qualified"
    ]
    markdown = render_markdown(output)
    assert "## Top 6" in markdown
    assert "口播三节拍" in markdown
    print("rank_ai_topics self-test passed: dynamic Top 6 from 7 candidates")


def main() -> int:
    args = parse_args()
    try:
        if args.self_test:
            run_self_test()
            return 0
        if not args.path:
            raise ValueError("path is required unless --self-test is used")
        if args.limit is not None and not 1 <= args.limit <= MAX_DISPLAY_COUNT:
            raise ValueError("--limit must be between 1 and 10")
        data = load_input(args.path)
        mode = args.mode or str(data["run"].get("mode", "balanced"))
        if mode not in WEIGHTS:
            raise ValueError(f"Unknown mode: {mode!r}")
        output = build_output(data, mode, args.limit)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    markdown = render_markdown(output)
    if args.markdown:
        Path(args.markdown).write_text(markdown, encoding="utf-8")
    else:
        print(markdown, end="")
    if args.json_output:
        Path(args.json_output).write_text(
            json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return 1 if output["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
