"""Sangyan Shield — OCR module for screenshot text extraction.

Extracts text from user-uploaded screenshots of WhatsApp / SMS messages
using Tesseract OCR with Pillow-based preprocessing.  The extracted text
is cleaned and returned as a plain string ready for ``engine.analyze_text``.

Dependencies (already in requirements.txt):
    - Pillow   (pillow==12.3.0)
    - pytesseract (pytesseract==0.3.13)
    - Tesseract binary must be installed on the host OS.

Usage:
    from ocr import extract_text

    with open("screenshot.png", "rb") as f:
        text = extract_text(f)
"""

from __future__ import annotations

import logging
import re
import shutil
from io import BytesIO
from typing import BinaryIO

from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError

import pytesseract

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Bilingual: English + Hindi (Devanagari).  Tesseract language packs
# ``eng`` and ``hin`` must be installed on the host.
_TESSERACT_LANG = "eng+hin"

# Tesseract Page Segmentation Mode:
#   6 = Assume a single uniform block of text.
# This works best for cropped chat bubbles and full-screen screenshots.
_TESSERACT_PSM = 6

# Custom Tesseract config string.
_TESSERACT_CONFIG = f"--psm {_TESSERACT_PSM} --oem 3"

# If the shortest side of the image is below this threshold (in px),
# the image is upscaled so Tesseract gets enough pixel density.
_MIN_DIMENSION = 1000

# Binary threshold value (0–255).  Pixels above this become white,
# below become black.  Tuned for typical WhatsApp light-mode screenshots.
_THRESHOLD = 180

# Maximum image dimension (in px) to cap memory usage.  Images larger
# than this are downscaled proportionally before processing.
_MAX_DIMENSION = 4000

# Allowed PIL image formats.  Reject anything exotic early.
_ALLOWED_FORMATS = {"PNG", "JPEG", "JPG", "BMP", "WEBP", "TIFF", "GIF"}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class OCRError(Exception):
    """Raised when OCR extraction fails for a known, handleable reason."""


class TesseractNotFoundError(OCRError):
    """Raised when the Tesseract binary is not installed or not on PATH."""


class InvalidImageError(OCRError):
    """Raised when the input is not a valid / supported image."""


# ---------------------------------------------------------------------------
# Tesseract availability check (run once at import time)
# ---------------------------------------------------------------------------
_tesseract_available: bool = False


def _check_tesseract() -> None:
    """Verify that the ``tesseract`` binary is reachable."""
    global _tesseract_available

    # pytesseract.pytesseract.tesseract_cmd may have been set manually.
    cmd = pytesseract.pytesseract.tesseract_cmd
    if cmd != "tesseract" and shutil.which(cmd):
        _tesseract_available = True
        log.info("Tesseract found at custom path: %s", cmd)
        return

    if shutil.which("tesseract"):
        _tesseract_available = True
        log.info("Tesseract found on system PATH")
        return

    log.warning(
        "Tesseract binary not found — OCR will be unavailable.  "
        "Install Tesseract and ensure it is on PATH, or set "
        "pytesseract.pytesseract.tesseract_cmd to the full path."
    )


_check_tesseract()


# ---------------------------------------------------------------------------
# Image preprocessing pipeline
# ---------------------------------------------------------------------------
def _preprocess(img: Image.Image) -> Image.Image:
    """Apply a preprocessing pipeline optimised for mobile screenshots.

    Steps:
        1. Convert to RGB (strip alpha / palette).
        2. Convert to grayscale (``L`` mode).
        3. Down-scale if larger than ``_MAX_DIMENSION`` (memory guard).
        4. Up-scale if smaller than ``_MIN_DIMENSION`` (legibility).
        5. Apply a slight median filter to reduce JPEG artefacts / noise.
        6. Apply binary (fixed) thresholding for sharp black-on-white text.
        7. Add a thin white border so Tesseract doesn't clip edge text.

    Returns a preprocessed ``Image.Image`` in ``"L"`` (grayscale) mode.
    """
    # 1. Normalise colour mode ------------------------------------------------
    if img.mode == "RGBA":
        # Composite onto white background so transparency becomes white.
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])  # alpha channel
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # 2. Grayscale ------------------------------------------------------------
    img = ImageOps.grayscale(img)

    # 3. Down-scale if too large (memory / speed guard) -----------------------
    max_side = max(img.size)
    if max_side > _MAX_DIMENSION:
        scale = _MAX_DIMENSION / max_side
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)
        log.debug("Downscaled image to %s", new_size)

    # 4. Up-scale if too small (Tesseract needs decent resolution) ------------
    min_side = min(img.size)
    if min_side < _MIN_DIMENSION:
        scale = _MIN_DIMENSION / min_side
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)
        log.debug("Upscaled image to %s", new_size)

    # 5. Denoise — light median filter (3×3) to smooth JPEG noise ------------
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # 6. Binary threshold — convert to crisp black-on-white ------------------
    img = img.point(lambda px: 255 if px > _THRESHOLD else 0, mode="L")

    # 7. Add white border (10 px each side) so edge text isn't clipped -------
    img = ImageOps.expand(img, border=10, fill=255)

    return img


# ---------------------------------------------------------------------------
# Post-processing: clean up raw Tesseract output
# ---------------------------------------------------------------------------
def _clean_text(raw: str) -> str:
    """Sanitise raw Tesseract output into a usable string.

    - Strip leading/trailing whitespace.
    - Collapse runs of whitespace (but preserve single newlines as they
      often represent separate chat bubbles).
    - Remove the Unicode replacement character and other control chars.
    - Remove isolated single-character "noise" lines (common OCR artefact).
    """
    if not raw:
        return ""

    # Remove control characters except newline and tab.
    text = re.sub(r"[^\S\n\t]+", " ", raw)

    # Collapse multiple blank lines into a single newline.
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove the Unicode replacement character (U+FFFD).
    text = text.replace("\ufffd", "")

    # Remove lines that are just a single non-alphanumeric character
    # (common OCR artefact: random "|", "~", etc.).
    text = re.sub(r"(?m)^\s*[^\w\s]\s*$", "", text)

    # Final trim.
    text = text.strip()

    return text


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def extract_text(image_stream: BinaryIO | bytes) -> str:
    """Extract text from a screenshot image.

    Parameters
    ----------
    image_stream:
        An open binary file stream (e.g. ``request.files['image']``) or
        raw ``bytes`` of the image.  The image is **never persisted to
        disk** — all processing happens in memory.

    Returns
    -------
    str
        The cleaned, extracted text.  May be an empty string if the image
        contains no recognisable text.

    Raises
    ------
    TesseractNotFoundError
        If the Tesseract binary is not installed or not on PATH.
    InvalidImageError
        If *image_stream* is not a valid or supported image format.
    OCRError
        For any other OCR-related failure.
    """
    # ── Guard: Tesseract availability ──────────────────────────────────
    if not _tesseract_available:
        raise TesseractNotFoundError(
            "Tesseract is not installed or not on PATH.  "
            "Install it from https://github.com/tesseract-ocr/tesseract "
            "and ensure the binary is accessible."
        )

    # ── Load the image into PIL ────────────────────────────────────────
    try:
        if isinstance(image_stream, bytes):
            image_stream = BytesIO(image_stream)
        elif hasattr(image_stream, "read"):
            # Wrap in BytesIO so PIL.Image.open can seek.
            data = image_stream.read()
            if not data:
                raise InvalidImageError("Received an empty image stream.")
            image_stream = BytesIO(data)
        else:
            raise InvalidImageError(
                f"Unsupported input type: {type(image_stream).__name__}.  "
                "Expected a file-like stream or bytes."
            )

        img = Image.open(image_stream)

        # Validate format early.
        fmt = (img.format or "").upper()
        if fmt and fmt not in _ALLOWED_FORMATS:
            raise InvalidImageError(
                f"Unsupported image format: '{fmt}'.  "
                f"Allowed formats: {', '.join(sorted(_ALLOWED_FORMATS))}."
            )

        # Force-load the pixel data so any truncation errors surface now
        # rather than during preprocessing.
        img.load()

    except UnidentifiedImageError as exc:
        raise InvalidImageError(
            "The uploaded file is not a valid image or is corrupted."
        ) from exc
    except InvalidImageError:
        raise
    except Exception as exc:
        raise InvalidImageError(
            f"Failed to open image: {exc}"
        ) from exc

    # ── Preprocess ─────────────────────────────────────────────────────
    try:
        processed = _preprocess(img)
    except Exception as exc:
        log.exception("Image preprocessing failed")
        raise OCRError(f"Image preprocessing failed: {exc}") from exc
    finally:
        # Close the original image immediately — we only need the
        # preprocessed copy from here on.
        img.close()

    # ── Run Tesseract OCR ──────────────────────────────────────────────
    try:
        raw_text: str = pytesseract.image_to_string(
            processed,
            lang=_TESSERACT_LANG,
            config=_TESSERACT_CONFIG,
        )
    except pytesseract.TesseractNotFoundError as exc:
        # pytesseract raises its own error if the binary disappears
        # between our check and the actual call.
        raise TesseractNotFoundError(
            "Tesseract binary became unavailable during OCR execution."
        ) from exc
    except pytesseract.TesseractError as exc:
        log.exception("Tesseract returned an error")
        raise OCRError(f"Tesseract OCR failed: {exc}") from exc
    except Exception as exc:
        log.exception("Unexpected error during OCR")
        raise OCRError(f"Unexpected OCR error: {exc}") from exc
    finally:
        processed.close()

    # ── Clean up and return ────────────────────────────────────────────
    cleaned = _clean_text(raw_text)
    log.info(
        "OCR extracted %d characters (%d lines) from image",
        len(cleaned),
        cleaned.count("\n") + 1 if cleaned else 0,
    )
    return cleaned
