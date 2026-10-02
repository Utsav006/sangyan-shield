"""Sangyan Shield Flask API."""

from flask import Flask, jsonify, request
from flask_cors import CORS

from engine import analyze_guided, analyze_text, load_guided

app = Flask(__name__)
CORS(app)


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "sangyan-shield"})


@app.get("/api/guided/questions")
def guided_questions():
    """Return the six guided-mode questions for the frontend wizard."""
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


@app.post("/api/analyze")
def analyze():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    language = data.get("language")
    result = analyze_text(text, language=language)
    return jsonify(result)


@app.post("/api/guided")
def guided():
    data = request.get_json(silent=True) or {}
    answers = data.get("answers")
    if answers is None:
        return jsonify({"error": "answers array is required"}), 400
    if not isinstance(answers, list):
        return jsonify({"error": "answers must be an array"}), 400

    language = data.get("language", "en")
    result = analyze_guided(answers, language=language)
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
