"""SEBI Intermediary Registry verification — real-time with offline fallback.

Performs live lookups against the SEBI Recognised Intermediaries search
portal.  If the SEBI website is unreachable or slow (>1.5 s), the module
automatically falls back to a curated local JSON dataset so the user
experience never hangs.

Results are cached with ``functools.lru_cache`` to avoid repeated
network calls for the same registration number.
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

DATA_FILE = Path(__file__).resolve().parent / "data" / "sebi_intermediaries.json"

# Network timeout for the SEBI portal (seconds).
_SEBI_TIMEOUT = 1.5

# SEBI AJAX endpoint used by the "Recognised Intermediaries" search form.
_SEBI_SEARCH_URL = (
    "https://www.sebi.gov.in/sebiweb/ajax/other/getrecognisedintm.jsp"
)

_SEBI_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": (
        "https://www.sebi.gov.in/sebiweb/other/"
        "OtherAction.do?doRecognised=yes"
    ),
    "Accept": "text/html, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}


# ---------------------------------------------------------------------------
# Offline (fallback) registry — loaded once at import time
# ---------------------------------------------------------------------------
_registry: dict[str, dict[str, Any]] = {}


def _load_registry() -> None:
    """Load the local SEBI intermediaries JSON into a fast lookup dict."""
    global _registry
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            entries = json.load(f)
        _registry = {entry["registration_number"]: entry for entry in entries}
        log.info(
            "SEBI offline registry loaded: %d intermediaries from %s",
            len(_registry),
            DATA_FILE,
        )
    except FileNotFoundError:
        log.warning(
            "SEBI data file not found at %s — offline fallback disabled",
            DATA_FILE,
        )
    except (json.JSONDecodeError, KeyError) as exc:
        log.error("Failed to parse SEBI data file: %s", exc)


_load_registry()


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------
# Standard SEBI registration prefixes:
#   INA  – Investment Adviser
#   INH  – Research Analyst
#   INB  – Stock Broker
#   INP  – Portfolio Manager
#   INR  – Registrar & Transfer Agent
#   INZ  – Stock Broker (alternate series)
#   INM  – Mutual Fund / AMC
#   IND  – Depository Participant
_SEBI_PATTERN = re.compile(
    r"\b(IN[AHBPRZMD]\d{6,12})\b",
    re.IGNORECASE,
)


def extract_sebi_number(text: str) -> str | None:
    """
    Extract the first SEBI-style registration number from *text*.

    Returns the uppercased registration number, or None if none found.
    Gracefully handles None, non-string, or malformed inputs.
    """
    if not text or not isinstance(text, str):
        return None
    try:
        match = _SEBI_PATTERN.search(text)
        if match:
            return match.group(1).upper()
    except (TypeError, re.error) as exc:
        log.warning("SEBI extraction failed on input: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Real-time verification — scrape the SEBI portal
# ---------------------------------------------------------------------------
def _parse_sebi_html(html: str, reg_number: str) -> dict[str, str] | None:
    """Parse the SEBI AJAX response HTML and extract intermediary details.

    The portal returns card-style ``div.card-view`` blocks, each containing
    a ``div.title > span`` and ``div.value > span`` pair.  We extract the
    first matching result whose Registration No. matches *reg_number*.

    Returns a dict with ``status``, ``name``, ``type``, and ``validity``
    keys if found, or ``None`` if the number is not present in the HTML.
    """
    # Quick-check: the portal returns this exact string when nothing matches.
    if "No record(s) available" in html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Each result is wrapped in a div.fixed-table-body.card-table
    cards = soup.find_all("div", class_="fixed-table-body")
    if not cards:
        return None

    for card in cards:
        fields: dict[str, str] = {}
        card_views = card.find_all("div", class_="card-view")
        for cv in card_views:
            title_tag = cv.find("div", class_="title")
            value_tag = cv.find("div", class_="value")
            if title_tag and value_tag:
                title_span = title_tag.find("span")
                value_span = value_tag.find("span")
                if title_span and value_span:
                    key = title_span.get_text(strip=True)
                    val = value_span.get_text(strip=True)
                    fields[key] = val

        # Match on registration number (case-insensitive)
        found_reg = fields.get("Registration No.", "").upper().strip()
        if found_reg == reg_number.upper().strip():
            name = fields.get("Name", fields.get("Trade Name", ""))
            intm_type = fields.get("Type", "")
            validity = fields.get("Validity", "")
            return {
                "status": "verified",
                "name": name,
                "type": intm_type,
                "validity": validity,
                "source": "sebi_live",
            }

    return None


@lru_cache(maxsize=256)
def verify_sebi_realtime(reg_number: str) -> dict[str, str]:
    """Query the live SEBI intermediary search portal for *reg_number*.

    Parameters
    ----------
    reg_number : str
        A SEBI registration string such as ``"INA000012345"`` or
        ``"INZ000172433"``.

    Returns
    -------
    dict
        ``{"status": "verified", "name": "...", "type": "...",
           "validity": "...", "source": "sebi_live"}``
        if the number is found on the SEBI website, otherwise
        ``{"status": "not_found", "source": "sebi_live"}``.

    Raises no exceptions — network errors are caught and logged so the
    caller can decide to fall back to the offline dataset.
    """
    if not reg_number or not isinstance(reg_number, str):
        return {"status": "not_found", "source": "sebi_live"}

    reg_number = reg_number.upper().strip()

    try:
        resp = requests.post(
            _SEBI_SEARCH_URL,
            data={"intmId": "-1", "search": "", "regNo": reg_number},
            headers=_SEBI_HEADERS,
            timeout=_SEBI_TIMEOUT,
        )
        resp.raise_for_status()

        result = _parse_sebi_html(resp.text, reg_number)
        if result:
            log.info(
                "SEBI live lookup VERIFIED: %s → %s",
                reg_number,
                result.get("name", ""),
            )
            return result

        log.info("SEBI live lookup: %s NOT FOUND on portal", reg_number)
        return {"status": "not_found", "source": "sebi_live"}

    except requests.Timeout:
        log.warning(
            "SEBI live lookup timed out (>%.1fs) for %s",
            _SEBI_TIMEOUT,
            reg_number,
        )
        raise  # Let the caller handle fallback

    except requests.RequestException as exc:
        log.warning("SEBI live lookup failed for %s: %s", reg_number, exc)
        raise  # Let the caller handle fallback


# ---------------------------------------------------------------------------
# Offline (fallback) verification
# ---------------------------------------------------------------------------
def _verify_offline(reg_number: str) -> dict[str, str]:
    """Look up *reg_number* in the local JSON dataset.

    Returns a dict with ``status`` = ``"verified"`` or ``"not_found"``
    and ``source`` = ``"offline_cache"``.
    """
    if not reg_number or not isinstance(reg_number, str):
        return {"status": "not_found", "source": "offline_cache"}

    reg_number = reg_number.upper().strip()
    entry = _registry.get(reg_number)

    if entry:
        return {
            "status": "verified",
            "name": entry.get("name", ""),
            "type": entry.get("type", ""),
            "validity": entry.get("validity", ""),
            "source": "offline_cache",
        }

    return {"status": "not_found", "source": "offline_cache"}


# ---------------------------------------------------------------------------
# Public API — real-time with automatic fallback
# ---------------------------------------------------------------------------
def verify_sebi_registration(reg_number: str) -> dict[str, str]:
    """Verify a SEBI registration number — live first, offline fallback.

    Strategy:
        1. Attempt a real-time lookup on the SEBI portal (≤ 1.5 s timeout).
        2. If the portal is unreachable, slow, or returns an error,
           fall back to the local ``sebi_intermediaries.json`` dataset.
        3. Results from the live path are LRU-cached (up to 256 entries)
           so repeated queries for the same number hit no network.

    The return dict always contains at least ``{"status": "..."}`` and is
    fully backward-compatible with callers that only check ``status``.
    """
    if not reg_number or not isinstance(reg_number, str):
        return {"status": "not_found"}

    reg_number = reg_number.upper().strip()

    # ── Try live lookup first ─────────────────────────────────────────
    try:
        result = verify_sebi_realtime(reg_number)
        return result
    except Exception:
        # Network failure — fall through to offline
        log.info(
            "Falling back to offline registry for %s", reg_number,
        )

    # ── Offline fallback ──────────────────────────────────────────────
    return _verify_offline(reg_number)
