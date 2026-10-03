"""
Sangyan Shield — Engine Unit Tests.

Tests the hybrid (deterministic rules + ML) scam-detection engine
against the PRD schema, guardrails, and expected risk-level behaviour.

Run:
    pytest test_engine.py -v
"""

from __future__ import annotations

import pytest

from engine import (
    analyze_guided,
    analyze_text,
    detect_language,
    find_spans,
    ml_predict,
    score_to_risk,
)
from registry import extract_sebi_number, verify_sebi_registration

# ---------------------------------------------------------------------------
# Required output keys and their expected types (PRD schema)
# ---------------------------------------------------------------------------
REQUIRED_KEYS = {
    "risk_level": str,
    "language": str,
    "flags": list,
    "could_not_verify": list,
    "next_steps": list,
    "disclaimer": str,
    "score": (int, float),
    "ml_scam_probability": (int, float, type(None)),
}

VALID_RISK_LEVELS = {"high", "careful", "looks_okay", "cant_tell"}

EN_DISCLAIMER = "This is a risk indicator, not a legal finding."
HI_DISCLAIMER = "यह केवल जोखिम संकेत है, कानूनी निर्णय नहीं।"


# ═══════════════════════════════════════════════════════════════════════════
# 1. HIGH-RISK SCAM DETECTION
# ═══════════════════════════════════════════════════════════════════════════
class TestHighRiskScam:
    """Verify that high-pressure scam messages with multiple red flags
    are correctly classified as 'high' risk with the right rule IDs."""

    def test_high_risk_english_scam(self):
        """English scam with guaranteed returns + OTP request + urgency."""
        text = (
            "Guaranteed returns of 30% monthly! Share OTP now to activate "
            "your account. Act now — today only! Transfer to my UPI."
        )
        result = analyze_text(text)

        assert result["risk_level"] == "high"
        flag_ids = {f["id"] for f in result["flags"]}
        assert "guaranteed_returns" in flag_ids
        assert "otp_request" in flag_ids
        assert "urgent_pressure" in flag_ids

    def test_high_risk_hindi_scam(self):
        """Hindi scam combining OTP pressure + guaranteed returns."""
        text = (
            "गारंटीड रिटर्न मासिक 20%! ओटीपी भेजो, आज ही जल्दी करो। "
            "मेरे यूपीआई पर भेजो।"
        )
        result = analyze_text(text)

        assert result["risk_level"] == "high"
        flag_ids = {f["id"] for f in result["flags"]}
        assert "guaranteed_returns" in flag_ids
        assert "otp_request" in flag_ids

    def test_high_risk_has_multiple_flags(self):
        """High-risk messages must produce at least 2 flags."""
        text = "Guaranteed returns! Send OTP immediately. Pay now to my account."
        result = analyze_text(text)

        assert result["risk_level"] == "high"
        assert len(result["flags"]) >= 2

    def test_flag_spans_are_valid_indices(self):
        """Each flag's span must be [start, end] pointing into the text."""
        text = "Share OTP now. Guaranteed returns. Act now."
        result = analyze_text(text)

        for flag in result["flags"]:
            span = flag["span"]
            assert isinstance(span, list), f"span should be a list, got {type(span)}"
            assert len(span) == 2, f"span should have 2 elements, got {len(span)}"
            start, end = span
            assert 0 <= start < end <= len(text), (
                f"Invalid span [{start}, {end}] for text of length {len(text)}"
            )
            # The highlighted substring should be non-empty
            highlighted = text[start:end]
            assert len(highlighted) > 0


# ═══════════════════════════════════════════════════════════════════════════
# 2. EDUCATIONAL MESSAGE (NEGATIVE WEIGHT)
# ═══════════════════════════════════════════════════════════════════════════
class TestEducationalMessage:
    """Educational/informational messages with negative-weight rule
    patterns must NOT trigger a false alarm."""

    def test_pure_educational_returns_looks_okay(self):
        """A message that only matches the educational rule should be safe."""
        text = (
            "This video is for educational purposes only. It is not "
            "financial advice. Markets can go down and there is always "
            "risk of loss. Do your own research before investing."
        )
        result = analyze_text(text)

        assert result["risk_level"] == "looks_okay"
        flag_ids = {f["id"] for f in result["flags"]}
        assert "educational_content" in flag_ids
        # Score should be negative (from -15 weight educational rule)
        assert result["score"] < 0

    def test_educational_overrides_ml(self):
        """Even if ML thinks it's suspicious, the educational override
        must keep the result as 'looks_okay' when ONLY educational
        rules matched. (Bug #3 fix verification.)"""
        text = "Not financial advice. Risk of loss. Do your own research."
        result = analyze_text(text)

        # Must be looks_okay regardless of ml_scam_probability
        assert result["risk_level"] == "looks_okay"

    def test_mixed_scam_plus_educational(self):
        """If a message has BOTH scam flags AND educational flags,
        the scam flags should still dominate."""
        text = (
            "Guaranteed returns of 30% monthly. Not financial advice. "
            "Send OTP now to activate."
        )
        result = analyze_text(text)

        # Should NOT be looks_okay since positive-weight flags matched
        assert result["risk_level"] in ("high", "careful")


# ═══════════════════════════════════════════════════════════════════════════
# 3. VAGUE / SHORT / NO-SIGNAL MESSAGES → "cant_tell"
# ═══════════════════════════════════════════════════════════════════════════
class TestVagueMessages:
    """The engine should return 'cant_tell' when the text has zero
    meaningful pattern matches, regardless of ML."""

    def test_vague_greeting(self):
        text = "Hello, call me"
        result = analyze_text(text)
        assert result["risk_level"] in ("cant_tell", "careful"), (
            f"Expected cant_tell or careful, got {result['risk_level']}"
        )
        # With zero rule matches, flags should be empty
        if result["risk_level"] == "cant_tell":
            assert len(result["flags"]) == 0

    def test_single_word(self):
        result = analyze_text("Hi")
        assert result["risk_level"] in ("cant_tell", "careful")

    def test_generic_sentence(self):
        result = analyze_text("The weather is nice today in Mumbai.")
        assert result["risk_level"] in ("cant_tell", "careful")

    def test_empty_after_strip_rejected_by_api(self):
        """Whitespace-only text should still go through the engine
        (the API layer rejects it, but the engine itself should handle it)."""
        result = analyze_text("   just some random words   ")
        # No scam flags → cant_tell (or careful if ML is confident)
        assert result["risk_level"] in VALID_RISK_LEVELS


# ═══════════════════════════════════════════════════════════════════════════
# 4. STRICT JSON SCHEMA VALIDATION
# ═══════════════════════════════════════════════════════════════════════════
class TestStrictJsonSchema:
    """Assert that every required key exists in the output dict and
    has the correct data type, for both analyze_text and analyze_guided."""

    def _validate_schema(self, result: dict, context: str):
        """Shared schema validation helper."""
        for key, expected_type in REQUIRED_KEYS.items():
            assert key in result, f"Missing key '{key}' in {context}"
            if isinstance(expected_type, tuple):
                assert isinstance(result[key], expected_type), (
                    f"Key '{key}' should be {expected_type}, "
                    f"got {type(result[key])} in {context}"
                )
            else:
                assert isinstance(result[key], expected_type), (
                    f"Key '{key}' should be {expected_type.__name__}, "
                    f"got {type(result[key]).__name__} in {context}"
                )

    def _validate_flags(self, flags: list, context: str):
        """Each flag must have id, reason, span."""
        for i, flag in enumerate(flags):
            assert "id" in flag, f"Flag {i} missing 'id' in {context}"
            assert "reason" in flag, f"Flag {i} missing 'reason' in {context}"
            assert "span" in flag, f"Flag {i} missing 'span' in {context}"
            assert isinstance(flag["id"], str)
            assert isinstance(flag["reason"], str)
            assert isinstance(flag["span"], list)
            assert len(flag["span"]) == 2
            assert all(isinstance(x, int) for x in flag["span"])

    def test_analyze_text_schema(self):
        result = analyze_text("Guaranteed returns! Share OTP now!")
        self._validate_schema(result, "analyze_text")
        self._validate_flags(result["flags"], "analyze_text")

    def test_analyze_text_schema_no_flags(self):
        """Schema must be valid even when no rules match."""
        result = analyze_text("The weather is pleasant today.")
        self._validate_schema(result, "analyze_text (no flags)")
        assert result["flags"] == []

    def test_analyze_guided_schema(self):
        answers = [
            {"id": "q_unknown_sender", "answer": True},
            {"id": "q_guaranteed_profit", "answer": True},
            {"id": "q_send_money_today", "answer": False},
            {"id": "q_otp_or_pin", "answer": True},
            {"id": "q_personal_account", "answer": False},
            {"id": "q_secret_group", "answer": True},
        ]
        result = analyze_guided(answers)
        self._validate_schema(result, "analyze_guided")
        self._validate_flags(result["flags"], "analyze_guided")
        # Guided mode should always return ml_scam_probability as None
        assert result["ml_scam_probability"] is None

    def test_risk_level_is_valid_enum(self):
        """risk_level must be one of the 4 allowed values."""
        for text in [
            "Guaranteed returns share OTP act now transfer to my account SEBI approved",
            "Hello friend",
            "Not financial advice, risk of loss",
        ]:
            result = analyze_text(text)
            assert result["risk_level"] in VALID_RISK_LEVELS, (
                f"Invalid risk_level '{result['risk_level']}'"
            )

    def test_next_steps_is_non_empty(self):
        """next_steps should always have at least 1 actionable item."""
        result = analyze_text("Some text to check")
        assert len(result["next_steps"]) >= 1

    def test_ml_probability_range(self):
        """When present, ml_scam_probability must be between 0 and 100."""
        result = analyze_text("Guaranteed returns. Send OTP now.")
        prob = result["ml_scam_probability"]
        if prob is not None:
            assert 0.0 <= prob <= 100.0, f"ml_scam_probability={prob} out of range"


# ═══════════════════════════════════════════════════════════════════════════
# 5. GUARDRAIL — DISCLAIMER ALWAYS PRESENT
# ═══════════════════════════════════════════════════════════════════════════
class TestGuardrailDisclaimer:
    """The legal disclaimer must ALWAYS be present in every response."""

    def test_disclaimer_english_high_risk(self):
        result = analyze_text("Guaranteed returns. Share OTP now. Act now!")
        assert result["disclaimer"] == EN_DISCLAIMER

    def test_disclaimer_english_safe(self):
        result = analyze_text("Hello, how are you?")
        assert result["disclaimer"] == EN_DISCLAIMER

    def test_disclaimer_hindi(self):
        result = analyze_text("गारंटीड रिटर्न ओटीपी भेजो", language="hi")
        assert result["disclaimer"] == HI_DISCLAIMER

    def test_disclaimer_guided_mode(self):
        result = analyze_guided(
            [{"id": "q_unknown_sender", "answer": False}], language="en"
        )
        assert result["disclaimer"] == EN_DISCLAIMER

    def test_disclaimer_is_never_empty(self):
        """Disclaimer must never be an empty string or None."""
        for text in ["Test", "OTP share now", "not financial advice"]:
            result = analyze_text(text)
            assert result["disclaimer"]  # truthy — non-empty string
            assert isinstance(result["disclaimer"], str)

    def test_no_financial_advice_in_next_steps(self):
        """next_steps must NOT contain buy/sell/hold advice or
        stock recommendations — only protective guidance."""
        forbidden_words = {"buy", "sell", "hold", "invest in", "recommended stock"}
        result = analyze_text("Guaranteed returns! Share OTP!")
        for step in result["next_steps"]:
            step_lower = step.lower()
            for word in forbidden_words:
                assert word not in step_lower, (
                    f"next_steps contains financial advice: '{step}'"
                )


# ═══════════════════════════════════════════════════════════════════════════
# 6. HELPER FUNCTION UNIT TESTS
# ═══════════════════════════════════════════════════════════════════════════
class TestHelpers:
    """Unit tests for individual helper functions."""

    def test_detect_language_english(self):
        assert detect_language("Hello world") == "en"

    def test_detect_language_hindi(self):
        assert detect_language("ओटीपी भेजो अभी") == "hi"

    def test_detect_language_mixed(self):
        """Hindi wins when Devanagari is present, even if mixed."""
        assert detect_language("Send money अभी भेजो") == "hi"

    def test_find_spans_basic(self):
        spans = find_spans("Share OTP now to unlock account", "otp")
        assert len(spans) == 1
        assert spans[0] == [6, 9]

    def test_find_spans_case_insensitive(self):
        spans = find_spans("share OTP with us", "otp")
        assert len(spans) == 1

    def test_find_spans_no_match(self):
        spans = find_spans("Hello world", "otp")
        assert spans == []

    def test_score_to_risk_high(self):
        assert score_to_risk(50, 3) == "high"
        assert score_to_risk(100, 5) == "high"

    def test_score_to_risk_careful(self):
        assert score_to_risk(20, 1) == "careful"
        assert score_to_risk(49, 2) == "careful"

    def test_score_to_risk_looks_okay(self):
        assert score_to_risk(-15, 1) == "looks_okay"

    def test_score_to_risk_cant_tell(self):
        assert score_to_risk(0, 0) == "cant_tell"
        assert score_to_risk(100, 0) == "cant_tell"


# ═══════════════════════════════════════════════════════════════════════════
# 7. LANGUAGE HANDLING
# ═══════════════════════════════════════════════════════════════════════════
class TestLanguageHandling:
    """Verify bilingual support works correctly."""

    def test_explicit_language_en(self):
        result = analyze_text("Guaranteed returns", language="en")
        assert result["language"] == "en"

    def test_explicit_language_hi(self):
        result = analyze_text("Guaranteed returns", language="hi")
        assert result["language"] == "hi"

    def test_invalid_language_falls_back_to_en(self):
        result = analyze_text("Guaranteed returns", language="fr")
        assert result["language"] == "en"

    def test_auto_detect_hindi(self):
        result = analyze_text("ओटीपी भेजो अभी")
        assert result["language"] == "hi"

    def test_auto_detect_english(self):
        result = analyze_text("Share OTP now")
        assert result["language"] == "en"


# ═══════════════════════════════════════════════════════════════════════════
# 8. EDGE CASES & ROBUSTNESS (Hackathon QA Audit)
# ═══════════════════════════════════════════════════════════════════════════
class TestEdgeCasesAndRobustness:
    """Critical edge-case tests added during the pre-submission QA audit.
    These cover empty inputs, SEBI regex edge cases, ML fallback, and
    hybrid scoring guarantees."""

    # ── Empty / null input handling ────────────────────────────────────
    def test_empty_input(self):
        """Engine must handle empty strings safely without crashing.
        Should return a valid 'cant_tell' response with full schema."""
        result = analyze_text("")

        assert result["risk_level"] == "cant_tell"
        assert result["flags"] == []
        assert result["score"] == 0
        assert result["ml_scam_probability"] is None
        assert result["disclaimer"] == EN_DISCLAIMER
        assert len(result["next_steps"]) >= 1
        # Verify full schema
        for key in REQUIRED_KEYS:
            assert key in result, f"Missing key '{key}' in empty input response"

    def test_none_input(self):
        """Engine must not crash on None input."""
        result = analyze_text(None)

        assert result["risk_level"] == "cant_tell"
        assert result["flags"] == []
        assert isinstance(result["disclaimer"], str)
        assert len(result["disclaimer"]) > 0

    def test_whitespace_only_input(self):
        """Whitespace-only strings should be treated as empty."""
        result = analyze_text("   \t\n  ")

        assert result["risk_level"] == "cant_tell"
        assert result["flags"] == []
        assert result["score"] == 0

    # ── SEBI extraction edge cases ────────────────────────────────────
    def test_sebi_extraction_fake(self):
        """Pass a message with 'INA999999999' — a number that matches the
        SEBI format but is NOT in the registry. Assert registry_check.status
        is 'not_found'."""
        text = "Invest with us! SEBI registered INA999999999. Guaranteed profit!"
        result = analyze_text(text)

        assert result["registry_check"]["extracted_number"] == "INA999999999"
        assert result["registry_check"]["status"] == "not_found"
        # Should also flag it as a fake SEBI number
        flag_ids = {f["id"] for f in result["flags"]}
        assert "fake_sebi_number" in flag_ids

    def test_sebi_extraction_valid(self):
        """Pass a message with a valid demo SEBI number (INA000012345)
        and assert that the registry lookup returns 'verified'."""
        text = "We are SEBI registered under INA000012345 for investment advisory."
        result = analyze_text(text)

        assert result["registry_check"]["extracted_number"] == "INA000012345"
        assert result["registry_check"]["status"] == "verified"
        # Should NOT flag it as fake
        flag_ids = {f["id"] for f in result["flags"]}
        assert "fake_sebi_number" not in flag_ids

    def test_sebi_extraction_no_number(self):
        """If no SEBI number is in the text, registry_check should be
        'no_number_detected'."""
        result = analyze_text("Hello, just a normal message.")
        assert result["registry_check"]["status"] == "no_number_detected"
        assert result["registry_check"]["extracted_number"] is None

    def test_sebi_extraction_emojis(self):
        """Emojis and special characters must not crash the SEBI regex."""
        text = "🚀🔥 Invest now!! 💰 Get rich 🤑 INA999999999 🎉"
        result = analyze_text(text)

        assert result["registry_check"]["extracted_number"] == "INA999999999"
        assert result["registry_check"]["status"] == "not_found"

    def test_sebi_extraction_none_input(self):
        """extract_sebi_number must handle None without crashing."""
        assert extract_sebi_number(None) is None

    def test_sebi_extraction_empty_string(self):
        """extract_sebi_number must handle empty string."""
        assert extract_sebi_number("") is None

    def test_sebi_extraction_numeric_input(self):
        """extract_sebi_number must handle non-string input."""
        assert extract_sebi_number(12345) is None

    def test_sebi_verification_none_input(self):
        """verify_sebi_registration must handle None without crashing."""
        result = verify_sebi_registration(None)
        assert result["status"] == "not_found"

    def test_sebi_verification_empty_string(self):
        """verify_sebi_registration must handle empty string."""
        result = verify_sebi_registration("")
        assert result["status"] == "not_found"

    # ── Hybrid scoring guarantees ─────────────────────────────────────
    def test_hybrid_scoring(self):
        """Ensure ml_scam_probability exists in the output dictionary
        and, when present, is a float between 0 and 100."""
        result = analyze_text("Guaranteed returns! Send OTP immediately!")

        assert "ml_scam_probability" in result
        prob = result["ml_scam_probability"]
        # prob can be None if ML model is not loaded — that's valid
        if prob is not None:
            assert isinstance(prob, (int, float)), (
                f"ml_scam_probability should be numeric, got {type(prob)}"
            )
            assert 0.0 <= prob <= 100.0, (
                f"ml_scam_probability={prob} is outside [0, 100]"
            )

    def test_hybrid_scoring_with_benign_text(self):
        """Even for benign text, ml_scam_probability must be a valid
        numeric or None."""
        result = analyze_text("The stock market closed higher today.")
        prob = result["ml_scam_probability"]
        if prob is not None:
            assert isinstance(prob, (int, float))
            assert 0.0 <= prob <= 100.0

    def test_registry_check_in_output_schema(self):
        """registry_check must always be present in analyze_text output."""
        result = analyze_text("Some message to analyze")
        assert "registry_check" in result
        assert "status" in result["registry_check"]

    # ── ML fallback behaviour ─────────────────────────────────────────
    def test_ml_predict_returns_float_or_none(self):
        """ml_predict must return a float in [0,1] or None — never crash."""
        prob = ml_predict("Guaranteed returns! Act now!")
        if prob is not None:
            assert isinstance(prob, float)
            assert 0.0 <= prob <= 1.0

    def test_ml_predict_empty_string(self):
        """ml_predict must not crash on empty string."""
        prob = ml_predict("")
        # None (model unavailable) or a float — either is acceptable
        assert prob is None or isinstance(prob, float)

    # ── Unicode / special character resilience ────────────────────────
    def test_unicode_input(self):
        """Engine must not crash on heavy Unicode content."""
        text = "مرحبا كيف حالك 你好世界 🔥🚀💰"
        result = analyze_text(text)
        assert result["risk_level"] in VALID_RISK_LEVELS
        assert isinstance(result["disclaimer"], str)

    def test_very_long_input(self):
        """Engine must handle large inputs without crashing."""
        text = "Guaranteed returns! " * 500
        result = analyze_text(text)
        assert result["risk_level"] in VALID_RISK_LEVELS
        assert len(result["flags"]) >= 1

    def test_newlines_and_tabs(self):
        """Newlines and tabs in input must not break anything."""
        text = "Guaranteed\treturns\n\nShare OTP\nnow"
        result = analyze_text(text)
        assert result["risk_level"] in VALID_RISK_LEVELS
