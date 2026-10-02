"""Hybrid scam-risk engine: deterministic rules + ML classification."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import joblib
import numpy as np

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"

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


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------
def _load_json(name: str) -> Any:
    try:
        with open(BASE_DIR / name, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        log.error("Data file not found: %s", name)
        raise RuntimeError(f"Missing data file: {name}")
    except json.JSONDecodeError as exc:
        log.error("Invalid JSON in %s: %s", name, exc)
        raise RuntimeError(f"Corrupt data file: {name}")


def load_rules() -> list[dict]:
    return _load_json("rules.json")


def load_guided() -> dict:
    return _load_json("guided.json")


# ---------------------------------------------------------------------------
# ML model — loaded once at import time
# ---------------------------------------------------------------------------
_ml_vectorizer = None
_ml_classifier = None
_ml_available = False

def _load_ml_model() -> None:
    """Load the TF-IDF vectorizer and classifier from disk (once)."""
    global _ml_vectorizer, _ml_classifier, _ml_available

    vec_path = MODELS_DIR / "vectorizer.pkl"
    clf_path = MODELS_DIR / "classifier.pkl"

    if not vec_path.exists() or not clf_path.exists():
        log.warning(
            "ML model files not found in %s — running in rules-only mode. "
            "Run `python train_ml.py` to generate them.",
            MODELS_DIR,
        )
        return

    try:
        _ml_vectorizer = joblib.load(vec_path)
        _ml_classifier = joblib.load(clf_path)
        _ml_available = True
        log.info("ML model loaded successfully from %s", MODELS_DIR)
    except Exception:
        log.exception("Failed to load ML model — falling back to rules-only mode")


# Load on module import so the model is ready when Flask starts
_load_ml_model()


def ml_predict(text: str) -> float | None:
    """
    Return the ML model's scam probability (0.0–1.0) for the given text.
    Returns None if the ML model is unavailable.
    """
    if not _ml_available:
        return None

    try:
        X = _ml_vectorizer.transform([text])
        proba = _ml_classifier.predict_proba(X)[0]
        # proba columns: [genuine, scam] — we want the scam probability
        scam_index = list(_ml_classifier.classes_).index(1)
        return float(proba[scam_index])
    except Exception:
        log.exception("ML prediction failed for input text")
        return None


# ---------------------------------------------------------------------------
# Language & scoring helpers
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Hybrid risk level: combine rule score + ML probability
# ---------------------------------------------------------------------------
def _hybrid_risk(
    rule_score: float,
    positive_flag_count: int,
    ml_prob: float | None,
) -> str:
    """
    Determine the final risk level by blending the rule engine score
    with the ML scam probability.

    Strategy:
    - Rule engine provides explainable, high-precision signals.
    - ML model provides broad coverage and catches zero-day patterns.
    - If ML says > 70% scam but rules found nothing, escalate to "careful".
    - If both agree on high risk, keep "high".
    """
    # Start with the rule-based risk level
    rule_risk = score_to_risk(rule_score, positive_flag_count)

    if ml_prob is None:
        # ML unavailable — fall back to pure rule engine
        return rule_risk

    # ML boost: if the ML is highly confident it's a scam…
    if ml_prob >= 0.70 and rule_risk in ("cant_tell", "looks_okay"):
        # Rules found nothing but ML is suspicious — escalate
        return "careful"

    if ml_prob >= 0.85 and rule_risk == "careful":
        # Both signals align toward danger — escalate to high
        return "high"

    # ML dampen: if ML says it's safe but rules flagged something
    # We trust the rules (they are explainable) — no downgrade.

    return rule_risk


# ---------------------------------------------------------------------------
# Main analysis: Hybrid Engine
# ---------------------------------------------------------------------------
def analyze_text(text: str, language: str | None = None) -> dict:
    """
    Hybrid analysis: deterministic rules + ML classification.

    1. Run rule matching for explainable flags and spans.
    2. Run ML model for scam probability.
    3. Blend both signals into a final risk level.
    """
    try:
        rules = load_rules()
    except RuntimeError:
        log.exception("Could not load rules for text analysis")
        raise

    lang = language or detect_language(text)
    if lang not in ("en", "hi"):
        lang = "en"

    flags: list[dict] = []
    score = 0.0
    matched_ids: set[str] = set()
    could_not_verify: list[str] = []

    for rule in rules:
        try:
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
        except Exception:
            log.warning("Skipping malformed rule: %s", rule.get("id", "unknown"))
            continue

    # Only count positive-weight flags toward "could not tell"
    positive_flags = [f for f in flags if next(
        (r["weight"] for r in rules if r["id"] == f["id"]), 0
    ) > 0]

    # ── ML classification ──────────────────────────────────────────────
    ml_prob = ml_predict(text)

    # ── Hybrid blending ────────────────────────────────────────────────
    risk_level = _hybrid_risk(score, len(positive_flags), ml_prob)

    # If ONLY educational (negative-weight) rules matched, the rule engine
    # has explicitly identified safe content — override unconditionally.
    # The ML model must not escalate known-safe educational patterns.
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
        "ml_scam_probability": round(ml_prob * 100, 1) if ml_prob is not None else None,
    }


def analyze_guided(answers: list[dict], language: str = "en") -> dict:
    """
    Score guided yes/no answers.

    Expected answers shape: [{"id": "q_...", "answer": true|false}, ...]
    or a plain list of booleans aligned with guided.json order.
    """
    try:
        guided = load_guided()
    except RuntimeError:
        log.exception("Could not load guided questions for analysis")
        raise

    questions = guided.get("questions", [])
    lang = language if language in ("en", "hi") else "en"

    score = 0.0
    flags: list[dict] = []

    # Normalize answers into id -> bool map
    answer_map: dict[str, bool] = {}
    try:
        if answers and isinstance(answers[0], dict):
            for item in answers:
                qid = item.get("id")
                if qid is not None:
                    answer_map[qid] = bool(item.get("answer"))
        else:
            for i, q in enumerate(questions):
                if i < len(answers):
                    answer_map[q["id"]] = bool(answers[i])
    except (TypeError, AttributeError) as exc:
        log.warning("Malformed answers payload: %s", exc)
        raise ValueError("Invalid answers format") from exc

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
        "ml_scam_probability": None,
    }
