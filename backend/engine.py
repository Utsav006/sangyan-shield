"""Deterministic scam-risk rule engine for Sangyan Shield."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent

DISCLAIMER = {
    "en": "This is a risk indicator, not a legal finding.",
    "hi": "यह केवल जोखिम संकेत है, कानूनी निर्णय नहीं।",
}

NEXT_STEPS = {
    "high": {
        "en": [
            "Do not send money",
            "Do not share OTP or PIN",
            "Block and report the sender",
            "If money was already sent, call your bank fraud helpline now",
        ],
        "hi": [
            "पैसे न भेजें",
            "ओटीपी या पिन न बताएँ",
            "भेजने वाले को ब्लॉक और रिपोर्ट करें",
            "अगर पैसे भेज दिए हैं, तुरंत बैंक फ्रॉड हेल्पलाइन पर कॉल करें",
        ],
    },
    "careful": {
        "en": [
            "Do not send money yet",
            "Verify any SEBI claim on the official SEBI website",
            "Ask a trusted person before acting",
            "Never share OTP",
        ],
        "hi": [
            "अभी पैसे न भेजें",
            "सेबी का दावा आधिकारिक सेबी वेबसाइट पर जाँचें",
            "कुछ करने से पहले किसी भरोसेमंद व्यक्ति से पूछें",
            "कभी ओटीपी न बताएँ",
        ],
    },
    "looks_okay": {
        "en": [
            "Still verify before investing",
            "Use only SEBI-registered intermediaries",
            "Never share OTP with anyone",
        ],
        "hi": [
            "निवेश से पहले फिर भी जाँच करें",
            "केवल सेबी-रजिस्टर्ड मध्यस्थों का उपयोग करें",
            "किसी को भी ओटीपी न बताएँ",
        ],
    },
    "cant_tell": {
        "en": [
            "Share more of the message for a clearer check",
            "Or try Guided Mode (yes/no questions)",
            "When unsure, do not send money",
        ],
        "hi": [
            "स्पष्ट जाँच के लिए संदेश का और हिस्सा साझा करें",
            "या गाइडेड मोड आज़माएँ (हाँ/नहीं प्रश्न)",
            "संदेह होने पर पैसे न भेजें",
        ],
    },
}


def _load_json(name: str) -> Any:
    with open(BASE_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def load_rules() -> list[dict]:
    return _load_json("rules.json")


def load_guided() -> dict:
    return _load_json("guided.json")


def detect_language(text: str) -> str:
    """Prefer Hindi if Devanagari characters are present."""
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    return "en"


def score_to_risk(score: float, flag_count: int) -> str:
    if flag_count == 0:
        return "cant_tell"
    if score >= 50:
        return "high"
    if score >= 20:
        return "careful"
    if score < 0:
        return "looks_okay"
    return "looks_okay"


def find_spans(text: str, pattern: str) -> list[list[int]]:
    """Return all case-insensitive [start, end] spans for pattern in text."""
    spans: list[list[int]] = []
    for match in re.finditer(re.escape(pattern), text, flags=re.IGNORECASE):
        spans.append([match.start(), match.end()])
    return spans


def analyze_text(text: str, language: str | None = None) -> dict:
    """Match message text against rules.json and return the PRD response shape."""
    rules = load_rules()
    lang = language or detect_language(text)
    if lang not in ("en", "hi"):
        lang = "en"

    flags: list[dict] = []
    score = 0.0
    matched_ids: set[str] = set()
    could_not_verify: list[str] = []

    for rule in rules:
        best_span: list[int] | None = None
        for pattern in rule.get("patterns", []):
            spans = find_spans(text, pattern)
            if spans:
                # Prefer the earliest match for highlighting
                candidate = spans[0]
                if best_span is None or candidate[0] < best_span[0]:
                    best_span = candidate

        if best_span is not None:
            weight = float(rule.get("weight", 0))
            score += weight
            matched_ids.add(rule["id"])
            reason = rule.get("reason", {})
            flags.append(
                {
                    "id": rule["id"],
                    "reason": reason.get(lang) or reason.get("en", ""),
                    "span": best_span,
                }
            )

            if rule["id"] == "sebi_claim":
                msg = (
                    "SEBI registration number not found in demo data"
                    if lang == "en"
                    else "डेमो डेटा में सेबी पंजीकरण संख्या नहीं मिली"
                )
                could_not_verify.append(msg)

    # Only count positive-weight flags toward "could not tell"
    positive_flags = [f for f in flags if next(
        (r["weight"] for r in rules if r["id"] == f["id"]), 0
    ) > 0]
    risk_level = score_to_risk(score, len(positive_flags))

    # If only educational (negative) rules matched, treat as looks_okay
    if flags and not positive_flags:
        risk_level = "looks_okay"

    return {
        "risk_level": risk_level,
        "language": lang,
        "flags": flags,
        "could_not_verify": could_not_verify,
        "next_steps": NEXT_STEPS[risk_level][lang],
        "disclaimer": DISCLAIMER[lang],
        "score": score,
    }


def analyze_guided(answers: list[dict], language: str = "en") -> dict:
    """
    Score guided yes/no answers.

    Expected answers shape: [{"id": "q_...", "answer": true|false}, ...]
    or a plain list of booleans aligned with guided.json order.
    """
    guided = load_guided()
    questions = guided.get("questions", [])
    lang = language if language in ("en", "hi") else "en"

    score = 0.0
    flags: list[dict] = []

    # Normalize answers into id -> bool map
    answer_map: dict[str, bool] = {}
    if answers and isinstance(answers[0], dict):
        for item in answers:
            qid = item.get("id")
            if qid is not None:
                answer_map[qid] = bool(item.get("answer"))
    else:
        for i, q in enumerate(questions):
            if i < len(answers):
                answer_map[q["id"]] = bool(answers[i])

    for q in questions:
        if answer_map.get(q["id"]):
            weight = float(q.get("weight_yes", 0))
            score += weight
            flags.append(
                {
                    "id": q["id"],
                    "reason": q["text"].get(lang) or q["text"].get("en", ""),
                    "span": [0, 0],
                }
            )

    risk_level = score_to_risk(score, len(flags))

    return {
        "risk_level": risk_level,
        "language": lang,
        "flags": flags,
        "could_not_verify": [],
        "next_steps": NEXT_STEPS[risk_level][lang],
        "disclaimer": DISCLAIMER[lang],
        "score": score,
    }
