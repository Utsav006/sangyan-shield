"""Sangyan Shield Flask API."""

import logging

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from engine import analyze_guided, analyze_text, load_guided

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# Rate limiter — uses remote IP by default (memory storage for dev,
# swap to Redis URI via RATELIMIT_STORAGE_URI env var in production).
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "60 per hour"],
    storage_uri="memory://",
)


# ---------------------------------------------------------------------------
# Error handlers — guarantee clean JSON on *any* unhandled exception
# ---------------------------------------------------------------------------
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Resource not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    log.exception("Unhandled server error")
    return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "sangyan-shield"})


@app.get("/api/guided/questions")
def guided_questions():
    """Return the six guided-mode questions for the frontend wizard."""
    try:
        lang = request.args.get("lang", "en")
        if lang not in ("en", "hi"):
            lang = "en"
        guided = load_guided()
        questions = []
        for q in guided.get("questions", []):
            questions.append(
                {
                    "id": q["id"],
                    "icon": q.get("icon", ""),
                    "text": q["text"].get(lang) or q["text"].get("en", ""),
                }
            )
        return jsonify({"language": lang, "questions": questions})
    except Exception:
        log.exception("Failed to load guided questions")
        return jsonify({"error": "Could not load guided questions"}), 500


@app.post("/api/analyze")
@limiter.limit("10 per minute")
def analyze():
    try:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Invalid or missing JSON body"}), 400

        text = (data.get("text") or "").strip()
        if not text:
            return jsonify({"error": "text is required"}), 400

        language = data.get("language")
        result = analyze_text(text, language=language)
        return jsonify(result)
    except Exception:
        log.exception("Error during text analysis")
        return jsonify({"error": "Analysis failed due to a server error"}), 500


@app.post("/api/guided")
@limiter.limit("10 per minute")
def guided():
    try:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Invalid or missing JSON body"}), 400

        answers = data.get("answers")
        if answers is None:
            return jsonify({"error": "answers array is required"}), 400
        if not isinstance(answers, list):
            return jsonify({"error": "answers must be an array"}), 400

        language = data.get("language", "en")
        result = analyze_guided(answers, language=language)
        return jsonify(result)
    except Exception:
        log.exception("Error during guided analysis")
        return jsonify({"error": "Guided analysis failed due to a server error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
