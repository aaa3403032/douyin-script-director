#!/usr/bin/env python3
"""First-pass audit for Chinese spoken-video scripts.

This checks timing and obvious hygiene issues. It cannot score creativity,
truth, or likely platform performance; those require sources and a read-through.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path


INTRO_PATTERNS = {
    "大家好": r"大家好",
    "自我介绍": r"(?:大家好.{0,8})?我是.{0,10}",
    "今天给大家": r"今天(?:来|要)?给大家",
    "空泛新闻开场": r"最近(?:有|发生了|出现了).{0,10}(?:一件事|一个消息|一条新闻)",
    "时代背景": r"随着.{0,16}(?:发展|兴起|普及)",
}

CLICHE_PATTERNS = {
    "综上所述": r"综上所述",
    "值得深思": r"值得(?:我们)?深思",
    "瞬息万变": r"瞬息万变的时代",
    "拭目以待": r"让我们拭目以待",
    "重要性不言而喻": r"重要性不言而喻",
}

INTERACTION_PATTERNS = {
    "选择": r"你(?:会|更愿意|到底会)?选.{0,24}(?:还是|或者)",
    "二选一": r"你(?:会|更愿意).{0,64}(?:还是|或者)",
    "判断": r"你觉得|你认为",
    "经历": r"你有没有(?:遇到|经历)|你也遇到过",
    "边界": r"到哪一步|什么情况下.{0,12}(?:不能|不会|不再)",
    "行动": r"如果是你.{0,24}(?:怎么|会)",
    "标准": r"(?:该不该|应不应该|是否应该|真的应该|同一个标准).{0,16}(?:吗|？)",
}

VIRAL_GUARANTEE_PATTERNS = {
    "保证爆火": r"保证.{0,4}(?:爆火|爆款|上热门)",
    "必然爆火": r"(?:必爆|必火|必上热门|一定上热门)",
    "百分百提升": r"(?:百分之百|100%)(?:能|会|可以)?(?:提升|增加).{0,8}(?:播放|流量|完播|互动)",
}

ABSOLUTE_CLAIM_PATTERN = re.compile(
    r"绝不|保证|一定|完全不会|必然|确保|百分之百|100%|永远不会|不可能",
    re.I,
)

SPEECH_TOKEN_PATTERN = re.compile(
    r"[\u3400-\u9fff]|[A-Za-z]+(?:[.-][A-Za-z]+)*|\d+(?:[.,]\d+)*"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit a Chinese oral-video script for duration and obvious hygiene issues."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="-",
        help="UTF-8 text file, or - to read stdin (default: -)",
    )
    parser.add_argument(
        "--target",
        type=float,
        required=True,
        help="Target spoken duration in seconds",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=300.0,
        help="Calibrated speech units per minute (default: 300)",
    )
    return parser.parse_args()


def read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def spoken_only(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        if stripped.startswith(
            (
                ":::",
                "#",
                "来源：",
                "资料来源：",
                "核验依据：",
                "事实核验：",
                "核验来源：",
                "预计时长：",
            )
        ):
            continue
        if re.fullmatch(r"\[(?:画面|字幕|音效|停顿|重音|镜头|B-?ROLL)[^\]]*\]", stripped, re.I):
            continue
        lines.append(line)
    value = "\n".join(lines)
    value = re.sub(r"https?://\S+", "", value)
    value = re.sub(
        r"\[(?:画面|字幕|音效|停顿|重音|镜头|B-?ROLL)[^\]]*\]",
        "",
        value,
        flags=re.I,
    )
    return value


def speech_units(text: str) -> dict[str, float | int]:
    han = len(re.findall(r"[\u3400-\u9fff]", text))
    latin_tokens = re.findall(r"[A-Za-z]+(?:[.-][A-Za-z]+)*", text)
    numeric_tokens = re.findall(r"\d+(?:[.,]\d+)*", text)

    return {
        "han_chars": han,
        "latin_tokens": len(latin_tokens),
        "numeric_tokens": len(numeric_tokens),
        "speech_units": han + len(latin_tokens) + len(numeric_tokens),
    }


def matching_labels(patterns: dict[str, str], text: str) -> list[str]:
    return [label for label, pattern in patterns.items() if re.search(pattern, text, re.I)]


def first_sentence(text: str) -> str:
    compact = re.sub(r"\s+", "", text)
    parts = re.split(r"(?<=[。！？!?])", compact, maxsplit=1)
    return parts[0][:120]


def first_sentences(text: str, count: int = 2) -> list[str]:
    compact = re.sub(r"\s+", "", text)
    parts = [part for part in re.split(r"(?<=[。！？!?])", compact) if part]
    return [part[:160] for part in parts[:count]]


def prefix_by_speech_units(text: str, max_units: int) -> str:
    """Return the text heard within an approximate speech-unit budget."""
    if max_units <= 0:
        return ""

    end = 0
    for index, match in enumerate(SPEECH_TOKEN_PATTERN.finditer(text), start=1):
        end = match.end()
        if index >= max_units:
            break
    return re.sub(r"\s+", "", text[:end])


def absolute_claims_with_context(text: str) -> list[dict[str, str]]:
    compact = re.sub(r"\s+", "", text)
    results: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for match in ABSOLUTE_CLAIM_PATTERN.finditer(compact):
        context = compact[max(0, match.start() - 18) : match.end() + 24]
        key = (match.group(0), context)
        if key in seen:
            continue
        seen.add(key)
        results.append({"term": match.group(0), "context": context})
    return results


def unique_latin_terms(text: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for term in re.findall(r"[A-Za-z]+(?:[.-][A-Za-z]+)*", text):
        key = term.casefold()
        if key in seen:
            continue
        seen.add(key)
        terms.append(term)
    return terms


def main() -> int:
    args = parse_args()
    if args.target <= 0 or args.rate <= 0:
        raise SystemExit("--target and --rate must be positive")

    raw = read_text(args.path)
    speech = spoken_only(raw)
    compact = re.sub(r"\s+", "", speech)
    opening = compact[:80]
    ending = compact[-180:]
    paragraph_texts = [p.strip() for p in re.split(r"\n\s*\n", speech) if p.strip()]
    final_paragraph = paragraph_texts[-1] if paragraph_texts else ""
    counts = speech_units(speech)
    units = float(counts["speech_units"])
    opening_twenty_units = max(1, math.ceil(units * 0.2))
    opening_payoff_window = prefix_by_speech_units(speech, opening_twenty_units)
    opening_three_second_units = max(1, math.ceil(args.rate * 3 / 60))
    opening_three_second_preview = prefix_by_speech_units(
        speech, opening_three_second_units
    )
    sentences = first_sentences(speech)
    first_sentence_counts = speech_units(sentences[0] if sentences else "")

    estimated = units / args.rate * 60
    slow = units / 260 * 60
    brisk = units / 320 * 60
    error_pct = abs(estimated - args.target) / args.target * 100

    intro_hits = matching_labels(INTRO_PATTERNS, opening)
    cliche_hits = matching_labels(CLICHE_PATTERNS, speech)
    interaction_hits = matching_labels(INTERACTION_PATTERNS, ending)
    guarantee_hits = matching_labels(VIRAL_GUARANTEE_PATTERNS, speech)
    numeric_claims = re.findall(
        r"(?:约|近|超过|不到|高达)?\s*\d+(?:\.\d+)?\s*(?:多|余)?\s*(?:%|％|万条|万人|万元|万|亿|元|年|个月|个|人|名|次|条|秒|分钟|小时|款|章|倍)?",
        speech,
    )
    numeric_claims = [re.sub(r"\s+", "", item) for item in numeric_claims]

    result = {
        **counts,
        "target_seconds": args.target,
        "calibrated_rate_units_per_minute": args.rate,
        "estimated_seconds": round(estimated, 1),
        "estimated_range_seconds_at_260_to_320": [round(brisk, 1), round(slow, 1)],
        "duration_error_pct": round(error_pct, 1),
        "duration_soft_pass": error_pct <= 10,
        "duration_hard_pass": error_pct <= 15,
        "first_sentence": first_sentence(speech),
        "first_two_sentences": sentences,
        "first_sentence_estimated_seconds": round(
            float(first_sentence_counts["speech_units"]) / args.rate * 60, 1
        ),
        "opening_preview_at_3s": opening_three_second_preview,
        "opening_payoff_window_first_20pct": opening_payoff_window,
        "opening_has_intro_tax": bool(intro_hits),
        "intro_tax_hits": intro_hits,
        "ai_cliche_hits": cliche_hits,
        "ending_has_interaction": bool(interaction_hits),
        "interaction_hits": interaction_hits,
        "final_paragraph_question_count": len(re.findall(r"[?？]", final_paragraph)),
        "multiple_final_questions_to_review": len(
            re.findall(r"[?？]", final_paragraph)
        )
        > 1,
        "has_viral_guarantee": bool(guarantee_hits),
        "viral_guarantee_hits": guarantee_hits,
        "numeric_claims_to_audit": numeric_claims,
        "absolute_claims_to_audit": absolute_claims_with_context(speech),
        "jargon_to_review": {
            "all_unique_latin_terms": unique_latin_terms(speech),
            "opening_20pct_unique_latin_terms": unique_latin_terms(
                opening_payoff_window
            ),
            "note": "Diagnostic only; translate or remove unfamiliar terms based on the target audience.",
        },
        "paragraphs": len(paragraph_texts),
        "hard_gate_pass": (
            error_pct <= 15 and not intro_hits and not guarantee_hits and bool(compact)
        ),
        "note": "Mechanical audit only; verify every claim and perform a full human read-through.",
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
