"""Human-readable explanation generator for Sangyan Shield verdicts.

Translates the raw output of the hybrid detection engine into a clear,
bilingual (English / Hindi) explanation that a non-technical user can
understand.  The output is a dict ready for JSON serialisation so the
React frontend can render it directly.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Bilingual phrase templates — keyed by rule-id / signal type
# ---------------------------------------------------------------------------
# Each entry maps a rule ID to a *fragment* that can be composed into a
# natural-language sentence.  The fragments are written so they read well
# when joined with commas / "and" / "तथा".
_RULE_FRAGMENTS: dict[str, dict[str, str]] = {
    "guaranteed_returns": {
        "en": "it promises guaranteed or fixed returns, which is illegal in the stock market",
        "hi": "इसमें गारंटीड या पक्के रिटर्न का वादा किया गया है, जो शेयर बाजार में अवैध है",
    },
    "otp_request": {
        "en": "it asks for your OTP or One-Time Password — no genuine bank, broker, or SEBI official will ever do this",
        "hi": "इसमें आपका OTP या वन-टाइम पासवर्ड माँगा जा रहा है — कोई भी असली बैंक, ब्रोकर या सेबी अधिकारी ऐसा नहीं करता",
    },
    "urgent_pressure": {
        "en": "it creates a false sense of urgency to pressure you into acting immediately",
        "hi": "इसमें जल्दबाज़ी और दबाव बनाया जा रहा है ताकि आप बिना सोचे-समझे कदम उठाएँ",
    },
    "unknown_links": {
        "en": "it contains unknown or shortened links that could lead to phishing pages",
        "hi": "इसमें अनजान या छोटे लिंक हैं जो फिशिंग पेज पर ले जा सकते हैं",
    },
    "personal_bank_transfer": {
        "en": "it asks you to transfer money to a personal bank or UPI account instead of a registered entity",
        "hi": "इसमें किसी व्यक्तिगत बैंक या UPI खाते में पैसे भेजने को कहा जा रहा है, न कि किसी पंजीकृत संस्था को",
    },
    "sebi_claim": {
        "en": "it claims to be SEBI-registered, which anyone can falsely state",
        "hi": "इसमें सेबी-रजिस्टर्ड होने का दावा किया गया है, जो कोई भी झूठा कर सकता है",
    },
    "fake_sebi_number": {
        "en": "it uses a SEBI registration number that does NOT exist in the official SEBI registry",
        "hi": "इसमें दी गई सेबी पंजीकरण संख्या आधिकारिक सेबी रजिस्ट्री में मौजूद नहीं है",
    },
    "educational_content": {
        "en": "it contains educational disclaimers such as 'not financial advice' or warnings about risk",
        "hi": "इसमें शैक्षिक अस्वीकरण हैं जैसे 'वित्तीय सलाह नहीं' या जोखिम की चेतावनी",
    },
}

# Risk-level headlines
_RISK_HEADLINES: dict[str, dict[str, str]] = {
    "high": {
        "en": "🚨 High Risk — This looks like a scam.",
        "hi": "🚨 उच्च जोखिम — यह एक घोटाला लगता है।",
    },
    "careful": {
        "en": "⚠️ Be Careful — There are some warning signs.",
        "hi": "⚠️ सावधान रहें — कुछ चेतावनी के संकेत हैं।",
    },
    "looks_okay": {
        "en": "✅ Looks Okay — No major red flags found.",
        "hi": "✅ ठीक लगता है — कोई बड़ा खतरा नहीं दिखा।",
    },
    "cant_tell": {
        "en": "🤔 Can't Tell — We didn't find enough information to judge.",
        "hi": "🤔 निर्णय नहीं ले पा रहे — जाँच के लिए पर्याप्त जानकारी नहीं मिली।",
    },
}

# Opening phrase for the explanation paragraph
_OPENING: dict[str, dict[str, str]] = {
    "high": {
        "en": "We flagged this as high risk because",
        "hi": "हमने इसे उच्च जोखिम के रूप में चिह्नित किया क्योंकि",
    },
    "careful": {
        "en": "We noticed some warning signs because",
        "hi": "हमने कुछ चेतावनी के संकेत देखे क्योंकि",
    },
    "looks_okay": {
        "en": "We did not find strong scam signals.",
        "hi": "हमें कोई मजबूत घोटाले के संकेत नहीं मिले।",
    },
    "cant_tell": {
        "en": "There wasn't enough content to make a clear assessment.",
        "hi": "स्पष्ट मूल्यांकन के लिए पर्याप्त सामग्री नहीं थी।",
    },
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _join_fragments(fragments: list[str], language: str) -> str:
    """Join a list of fragments with commas and a final 'and' / 'तथा'."""
    if not fragments:
        return ""
    if len(fragments) == 1:
        return fragments[0]
    joiner = " and " if language == "en" else " तथा "
    return ", ".join(fragments[:-1]) + joiner + fragments[-1]


def _build_sebi_note(registry_check: dict, language: str) -> str | None:
    """Return an extra note about the SEBI registry status, if relevant."""
    status = registry_check.get("status", "no_number_detected")
    reg_num = registry_check.get("extracted_number")

    if status == "verified" and reg_num:
        name = registry_check.get("name", "")
        if language == "en":
            note = (
                f"The SEBI registration number {reg_num} was found in the "
                f"official registry"
            )
            if name:
                note += f", belonging to {name}"
            note += ". This is a positive sign, but always cross-check on the SEBI website."
            return note
        else:
            note = (
                f"सेबी पंजीकरण संख्या {reg_num} आधिकारिक रजिस्ट्री में मिली"
            )
            if name:
                note += f", जो {name} की है"
            note += "। यह एक अच्छा संकेत है, लेकिन सेबी वेबसाइट पर भी जाँच करें।"
            return note

    if status == "not_found" and reg_num:
        if language == "en":
            return (
                f"The SEBI registration number {reg_num} was NOT found in "
                f"the official SEBI registry. This is a serious red flag."
            )
        else:
            return (
                f"सेबी पंजीकरण संख्या {reg_num} आधिकारिक सेबी रजिस्ट्री में "
                f"नहीं मिली। यह एक गंभीर खतरे का संकेत है।"
            )

    return None


def _build_ml_note(ml_pct: float | None, language: str) -> str | None:
    """Return an optional note about the ML model's confidence."""
    if ml_pct is None:
        return None

    if ml_pct >= 70:
        if language == "en":
            return (
                f"Our machine-learning model is {ml_pct}% confident that "
                f"this message is a scam."
            )
        else:
            return (
                f"हमारे मशीन-लर्निंग मॉडल को {ml_pct}% विश्वास है कि "
                f"यह संदेश एक घोटाला है।"
            )
    if ml_pct >= 40:
        if language == "en":
            return (
                f"Our machine-learning model gives this a {ml_pct}% scam "
                f"probability — not conclusive, but worth being cautious."
            )
        else:
            return (
                f"हमारे मशीन-लर्निंग मॉडल के अनुसार इसकी घोटाला "
                f"संभावना {ml_pct}% है — निर्णायक नहीं, लेकिन सतर्क रहें।"
            )
    # Low ML confidence — nothing worth mentioning
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_explanation(
    verdict_data: dict[str, Any],
    language: str = "en",
) -> dict[str, Any]:
    """Translate a raw hybrid-engine verdict into a human-readable explanation.

    Parameters
    ----------
    verdict_data : dict
        The dict returned by ``engine.analyze_text()`` or
        ``engine.analyze_guided()``.  Expected keys::

            risk_level            : str   – "high" | "careful" | "looks_okay" | "cant_tell"
            flags                 : list  – [{"id": str, "reason": str, "span": [int,int]}, ...]
            ml_scam_probability   : float | None  – 0-100 percentage
            registry_check        : dict  – {"extracted_number", "status", ...}
            next_steps            : list[str]
            disclaimer            : str
            could_not_verify      : list[str]
            score                 : float
            language              : str

    language : str, default "en"
        ``"en"`` for English, ``"hi"`` for Hindi.

    Returns
    -------
    dict
        A JSON-friendly dict the React frontend can render directly::

            {
                "headline":     str,
                "summary":      str,          # natural-language paragraph
                "bullet_points": [str, ...],  # key reasons as bullets
                "sebi_note":    str | None,
                "ml_note":      str | None,
                "next_steps":   [str, ...],
                "disclaimer":   str,
                "could_not_verify": [str, ...],
            }
    """
    lang = language if language in ("en", "hi") else "en"

    risk_level: str = verdict_data.get("risk_level", "cant_tell")
    flags: list[dict] = verdict_data.get("flags", [])
    ml_pct: float | None = verdict_data.get("ml_scam_probability")
    registry_check: dict = verdict_data.get(
        "registry_check",
        {"extracted_number": None, "status": "no_number_detected"},
    )
    next_steps: list[str] = verdict_data.get("next_steps", [])
    disclaimer: str = verdict_data.get("disclaimer", "")
    could_not_verify: list[str] = verdict_data.get("could_not_verify", [])

    # ── Headline ──────────────────────────────────────────────────────
    headline = _RISK_HEADLINES.get(risk_level, _RISK_HEADLINES["cant_tell"])[lang]

    # ── Collect per-flag fragments and bullet points ──────────────────
    fragments: list[str] = []
    bullet_points: list[str] = []

    # Track which rule IDs we've already processed to avoid duplicates
    seen_ids: set[str] = set()

    for flag in flags:
        fid: str = flag.get("id", "")
        if fid in seen_ids:
            continue
        seen_ids.add(fid)

        # Use our curated fragment if available; fall back to the
        # engine-provided reason for any custom / future rules.
        template = _RULE_FRAGMENTS.get(fid)
        if template:
            fragments.append(template[lang])
        else:
            # Fallback: use the reason text from the engine itself
            reason = flag.get("reason", "")
            if reason:
                fragments.append(reason)

        # Bullet point always uses the richer engine reason
        reason_text = flag.get("reason", "")
        if reason_text:
            bullet_points.append(reason_text)

    # ── Build the summary paragraph ──────────────────────────────────
    opening = _OPENING.get(risk_level, _OPENING["cant_tell"])[lang]

    if risk_level in ("high", "careful") and fragments:
        joined = _join_fragments(fragments, lang)
        if lang == "en":
            summary = f"{opening} {joined}."
        else:
            summary = f"{opening} {joined}।"
    else:
        summary = opening

    # ── SEBI and ML notes ─────────────────────────────────────────────
    sebi_note = _build_sebi_note(registry_check, lang)
    ml_note = _build_ml_note(ml_pct, lang)

    # Append SEBI / ML context to bullet points as well for completeness
    if sebi_note:
        bullet_points.append(sebi_note)
    if ml_note:
        bullet_points.append(ml_note)

    # ── Could-not-verify warnings ─────────────────────────────────────
    if could_not_verify:
        for item in could_not_verify:
            bullet_points.append(item)

    return {
        "headline": headline,
        "summary": summary,
        "bullet_points": bullet_points,
        "sebi_note": sebi_note,
        "ml_note": ml_note,
        "next_steps": next_steps,
        "disclaimer": disclaimer,
        "could_not_verify": could_not_verify,
    }
