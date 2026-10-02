"""Simulated SEBI Intermediary Registry verification.

Since SEBI does not expose a public API, this module loads a curated JSON
dataset and performs a lookup to simulate a real-time registry check.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

DATA_FILE = Path(__file__).resolve().parent / "data" / "sebi_intermediaries.json"

# ---------------------------------------------------------------------------
# In-memory registry (loaded once at import time)
# ---------------------------------------------------------------------------
_registry: dict[str, dict[str, Any]] = {}


def _load_registry() -> None:
    """Load the SEBI intermediaries JSON into a fast lookup dict."""
    global _registry
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            entries = json.load(f)
        _registry = {entry["registration_number"]: entry for entry in entries}
        log.info(
            "SEBI registry loaded: %d intermediaries from %s",
            len(_registry),
            DATA_FILE,
        )
    except FileNotFoundError:
        log.warning("SEBI data file not found at %s — registry checks disabled", DATA_FILE)
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
    """
    match = _SEBI_PATTERN.search(text)
    if match:
        return match.group(1).upper()
    return None


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
def verify_sebi_registration(reg_number: str) -> dict[str, str]:
    """
    Look up *reg_number* in the loaded SEBI intermediary dataset.

    Returns:
        {"status": "verified", "name": "<entity name>", "type": "...", ...}
        or
        {"status": "not_found"}
    """
    reg_number = reg_number.upper().strip()
    entry = _registry.get(reg_number)

    if entry:
        return {
            "status": "verified",
            "name": entry.get("name", ""),
            "type": entry.get("type", ""),
            "validity": entry.get("validity", ""),
        }

    return {"status": "not_found"}
