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

HOT_LANGUAGE = re.compile(
    r"全网最火|最有流量|流量最大|刷屏|暴涨|霸榜|爆了|都在讨论|热度飙升|"
    r"hottest|viral|trending everywhere",
    re.I,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rank evidence-backed AI topics; this is not a view predictor."
    )
    parser.add_argument("path", help="UTF-8 radar.json input")
    parser.add_argument(
        "--mode",
        choices=sorted(WEIGHTS),
        help="Override run.mode (balanced, news, tutorial, or technical)",
    )
    parser.add_argument("--markdown", help="Optional Markdown output path")
    parser.add_argument("--json", dest="json_output", help="Optional JSON output path")
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
    topic: dict[str, Any], weights: dict[str, int], index: int
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


def build_output(data: dict[str, Any], mode: str) -> dict[str, Any]:
    weights = WEIGHTS[mode]
    errors = validate_run(data["run"])
    warnings: list[str] = []
    ranked: list[dict[str, Any]] = []

    seen_ids: set[str] = set()
    seen_angles: Counter[str] = Counter()
    for index, topic in enumerate(data["topics"], start=1):
        if not isinstance(topic, dict):
            errors.append(f"topic-{index}: must be an object")
            continue
        topic_errors, topic_warnings = validate_topic(topic, weights, index)
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
            ranked.append(
                {
                    "id": topic_id,
                    "title": topic["title"],
                    "track": str(topic.get("track", "unclassified")).lower(),
                    "evidence_grade": str(topic["evidence_grade"]).upper(),
                    "opportunity_score": score,
                    "risk_penalty": penalty,
                    "why_now": topic.get("why_now", ""),
                    "allowed_heat_wording": topic.get("allowed_heat_wording", ""),
                    "next_checks": topic.get("next_checks", []),
                    "screenshots": topic.get("screenshots", []),
                }
            )

    for angle, count in seen_angles.items():
        if count > 1:
            warnings.append(f"duplicate angle_key {angle!r} appears {count} times")

    ranked.sort(key=lambda item: (-item["opportunity_score"], item["id"]))
    for position, item in enumerate(ranked, start=1):
        item["rank"] = position

    return {
        "mode": mode,
        "captured_at": data["run"].get("captured_at"),
        "region": data["run"].get("region"),
        "audience": data["run"].get("audience"),
        "score_name": "内容机会分（非播放量预测）",
        "weights": weights,
        "ranked_topics": ranked,
        "warnings": sorted(set(warnings)),
        "errors": sorted(set(errors)),
    }


def render_markdown(output: dict[str, Any]) -> str:
    lines = [
        "# AI选题雷达排序",
        "",
        f"- 模式：{output['mode']}",
        f"- 采集时间：{output.get('captured_at') or '未记录'}",
        f"- 地区：{output.get('region') or '未记录'}",
        f"- 受众：{output.get('audience') or '未记录'}",
        "- 分数：内容机会分，不是播放量、爆款概率或平台推荐预测。",
        "",
        "| 排名 | 轨道 | 选题 | 等级 | 机会分 | 风险扣分 | 允许的热度表述 |",
        "|---:|---|---|:---:|---:|---:|---|",
    ]
    for item in output["ranked_topics"]:
        wording = str(item["allowed_heat_wording"]).replace("|", "\\|")
        title = str(item["title"]).replace("|", "\\|")
        lines.append(
            f"| {item['rank']} | {item['track']} | {title} | {item['evidence_grade']} | "
            f"{item['opportunity_score']:.1f} | {item['risk_penalty']:.1f} | {wording} |"
        )
    if output["warnings"]:
        lines.extend(["", "## 需要复核"])
        lines.extend(f"- {warning}" for warning in output["warnings"])
    if output["errors"]:
        lines.extend(["", "## 输入错误"])
        lines.extend(f"- {error}" for error in output["errors"])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    try:
        data = load_input(args.path)
        mode = args.mode or str(data["run"].get("mode", "balanced"))
        if mode not in WEIGHTS:
            raise ValueError(f"Unknown mode: {mode!r}")
        output = build_output(data, mode)
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
