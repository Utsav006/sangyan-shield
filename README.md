<p align="center">
  <img src="https://img.shields.io/badge/SANGYAN-Hackathon%202026-blueviolet?style=for-the-badge" alt="SANGYAN Hackathon 2026" />
  <img src="https://img.shields.io/badge/License-Non--Commercial-orange?style=for-the-badge" alt="Non-Commercial" />
  <img src="https://img.shields.io/badge/Privacy-Zero%20Data%20Stored-brightgreen?style=for-the-badge" alt="Zero Data Stored" />
</p>

<h1 align="center">🛡️ Sangyan Shield</h1>
<h3 align="center"><em>"For the moment you can't copy-paste."</em></h3>

<p align="center">
  A bilingual (Hindi + English) scam-detection assistant that helps retail investors in India's Tier-2 and Tier-3 cities identify investment fraud — <strong>before</strong> they send money.
</p>

---

## 📋 Table of Contents

- [The Problem & Target User](#-the-problem--target-user)
- [Core Features](#-core-features)
- [The Technology — Hybrid Engine](#-the-technology--hybrid-engine)
- [Architecture Overview](#-architecture-overview)
- [Guardrail Compliance](#-guardrail-compliance-critical)
- [Local Setup Instructions](#-local-setup-instructions)
- [Project Structure](#-project-structure)
- [API Reference](#-api-reference)
- [Roadmap & Limitations](#-roadmap--limitations)
- [Team](#-team)

---

## 🎯 The Problem & Target User

> **"Ramesh is a 52-year-old shopkeeper in Rewa, Madhya Pradesh.** He recently got a smartphone and started using WhatsApp. One day, he receives a message in Hindi promising *guaranteed 20% monthly returns* from a *SEBI-registered advisor*. The message asks him to transfer ₹10,000 to a personal UPI ID. Ramesh doesn't know what SEBI is. He can't Google in English. He's about to send the money."

**Sangyan Shield exists for Ramesh.**

India's investment fraud landscape disproportionately affects retail investors in smaller cities — people who:

- 🏘️ **Lack access** to financial literacy resources in their language
- 📱 **Receive scams** via WhatsApp/SMS tip-groups they didn't sign up for
- ⌨️ **Can't type easily** on smartphones — many are first-generation internet users
- 🤝 **Trust authority claims** ("SEBI approved", "Government scheme") at face value

These aren't edge cases — they are the **primary targets** of investment scammers.

---

## ✨ Core Features

### 1. 📩 Message Check
Paste any suspicious WhatsApp, SMS, or Telegram message. The hybrid engine scans it in **real time**, highlights the exact scam phrases with colour-coded spans, and explains *why* each phrase is dangerous — in the user's own language.

### 2. 🧭 Guided Mode (No-Typing Interface)
Can't copy-paste? Can't type in English? **No problem.**  
Guided Mode presents **6 simple Yes/No questions** with large tap targets (e.g., *"Did they promise guaranteed profits?"*). Each question can be **read aloud** in Hindi or English using the built-in Web Speech API. Zero typing required.

### 3. 🔊 Bilingual Voice Output (Hindi + English)
Every verdict screen has a **"Hear this result"** button. The app reads the risk level, the reasons, and the next steps aloud — using `hi-IN` or `en-IN` speech synthesis. Designed for users who may struggle to read on small screens.

### 4. ✅ Recovery Checklist
Already sent money? The **Recovery Path** provides a calm, step-by-step action plan:
1. Call your bank/UPI fraud helpline immediately
2. Do not send more money (even if they promise a "refund")
3. Save all screenshots — chats, UPI IDs, phone numbers
4. File a complaint on [cybercrime.gov.in](https://cybercrime.gov.in)
5. Dial **1930** (India's cyber fraud helpline)
6. Tell a trusted family member — you don't have to handle this alone

### 5. 🤖 AI Confidence Score
When the ML model is active, the verdict screen displays an **AI Confidence badge** (e.g., *AI Confidence: 87%*) — giving users a transparent, at-a-glance signal of how confident the system is that the message is a scam.

---

## ⚙️ The Technology — Hybrid Engine

Sangyan Shield uses a **two-layer hybrid architecture** that combines the best of deterministic rules and machine learning:

```
┌──────────────────────────────────────────────────────┐
│                  USER INPUT (text)                    │
└──────────────┬───────────────────────┬───────────────┘
               │                       │
       ┌───────▼────────┐     ┌────────▼─────────┐
       │  RULE ENGINE   │     │    ML MODEL      │
       │  (Deterministic)│     │  (scikit-learn)  │
       │                │     │                  │
       │ • Pattern match │     │ • TF-IDF vectors │
       │ • Weighted score│     │ • Logistic Reg.  │
       │ • Exact spans   │     │ • Scam probability│
       │ • Explainability│     │ • Zero-day detect │
       └───────┬────────┘     └────────┬─────────┘
               │                       │
       ┌───────▼───────────────────────▼───────────┐
       │           HYBRID BLENDING LAYER           │
       │                                           │
       │  Rules provide explainability & precision  │
       │  ML provides coverage & zero-day detection │
       │  Rules are NEVER downgraded by ML          │
       └─────────────────┬─────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │    RISK VERDICT     │
              │  high / careful /   │
              │  looks_okay /       │
              │  cant_tell          │
              └─────────────────────┘
```

### Layer 1 — Rule Engine (Deterministic)

A curated set of **7 pattern-matching rules** in [`rules.json`](backend/rules.json), each with:
- **Bilingual patterns** (English + Hindi) — e.g., `"guaranteed returns"`, `"गारंटी रिटर्न"`
- **Weighted severity** — from `-15` (educational content, safe signal) to `+45` (OTP request, critical danger)
- **Explainable reasons** — every flag comes with a human-readable sentence in the user's language
- **Exact text spans** — the UI highlights the *precise* words that triggered the flag

This layer is **100% explainable**. A judge, regulator, or user can always trace *exactly* why a verdict was given.

### Layer 2 — ML Model (Zero-Day Detection)

A lightweight **TF-IDF + Logistic Regression** classifier trained on curated scam/genuine examples via [`train_ml.py`](backend/train_ml.py):

| Component | Detail |
|---|---|
| Vectorizer | `TfidfVectorizer` — 3,000 features, unigrams + bigrams |
| Classifier | `LogisticRegression` — balanced class weights, L-BFGS solver |
| Output | Scam probability `0.0–1.0` surfaced as **AI Confidence Score** |
| Size | ~50 KB total (vectorizer + classifier `.pkl` files) |
| Runs | **Entirely local** — no API calls, no cloud, no data leaves the device |

### Hybrid Blending Strategy

The blending layer in [`engine.py`](backend/engine.py) follows strict principles:

- **Rules are never downgraded by ML.** If rules flag danger, ML cannot override.
- **ML escalates silently.** If ML detects ≥70% scam probability but rules found nothing → escalate to `"careful"`.
- **Both agree = maximum confidence.** If rules say `"careful"` and ML says ≥85% → escalate to `"high"`.
- **Educational content is sacred.** If only negative-weight (safe) rules matched, the verdict stays `"looks_okay"` regardless of ML.

### Frontend — React + Vite PWA

| Stack | Version |
|---|---|
| React | 19.x |
| Vite | 8.x |
| React Router | 7.x |
| Speech | Web Speech API (`SpeechSynthesisUtterance`) |
| i18n | Custom context-based, JSON language packs |
| Linting | oxlint |

---

## 🏗️ Architecture Overview

```
sangyan-shield/
├── backend/                 # Python / Flask API
│   ├── app.py               # Flask server — routes, rate limiting, CORS
│   ├── engine.py            # Hybrid engine — rules + ML blending
│   ├── train_ml.py          # ML training script (TF-IDF + LogReg)
│   ├── rules.json           # 7 deterministic scam-detection rules
│   ├── guided.json          # 6 guided-mode questions (Hindi + English)
│   ├── registry_demo.json   # Demo SEBI registry data (placeholder)
│   ├── models/              # Serialized ML artifacts (vectorizer + classifier)
│   └── requirements.txt     # Python dependencies (pinned)
│
├── frontend/                # React + Vite SPA
│   ├── src/
│   │   ├── components/
│   │   │   ├── Home.jsx         # Landing — 3 entry points
│   │   │   ├── MessageInput.jsx # Paste-and-check interface
│   │   │   ├── GuidedMode.jsx   # No-typing 6-question wizard
│   │   │   ├── Verdict.jsx      # Risk verdict + voice + AI badge
│   │   │   └── Recovery.jsx     # Post-scam recovery checklist
│   │   ├── i18n/
│   │   │   └── en.json          # English language pack
│   │   ├── LanguageContext.jsx  # i18n context provider
│   │   ├── App.jsx              # Router + layout
│   │   └── App.css              # Full design system
│   ├── .env.example             # Environment template
│   └── package.json
│
└── README.md
```

---

## 🔒 Guardrail Compliance (CRITICAL)

Sangyan Shield was designed from day one to strictly comply with every hackathon guardrail:

| Guardrail | How We Comply |
|---|---|
| **🔐 Zero Data Stored** | No database. No log files with user content. No cookies. No analytics. All analysis is **stateless** — the input is processed in-memory and the response is returned. Nothing is persisted. |
| **📵 No OTP/SMS Access** | The app **never** requests SMS permissions, contacts, or phone access. Users manually paste text into the input field. Privacy by Design, not by afterthought. |
| **🚫 No Financial Advice** | Sangyan Shield **never** says "invest here" or "sell this stock". Every verdict includes the disclaimer: *"This is a risk indicator, not a legal finding."* We detect scams — we don't recommend trades. |
| **🏛️ Non-Commercial** | No ads. No premium tier. No data monetization. No user accounts. The app is fully open-source and built exclusively for this hackathon. |
| **⚖️ No SEBI Regulation Violation** | We do not provide investment advisory services. We do not access market data or APIs. We only flag patterns commonly associated with fraud. |
| **🌐 Runs 100% Locally** | The ML model runs on-device via `scikit-learn`. No cloud API calls (no OpenAI, no Google Cloud). The user's data never leaves their machine. |

---

## 🚀 Local Setup Instructions

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |
| Git | Any |

### 1. Clone the Repository

```bash
git clone https://github.com/Utsav006/sangyan-shield.git
cd sangyan-shield
```

### 2. Backend Setup (Flask + ML)

```bash
# Create and activate a virtual environment
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Train the ML model (generates vectorizer.pkl + classifier.pkl)
python train_ml.py

# Start the Flask server (runs on port 5000)
python app.py
```

You should see:
```
ML model loaded successfully from ...\backend\models
 * Running on http://0.0.0.0:5000
```

### 3. Frontend Setup (React + Vite)

Open a **new terminal**:

```bash
cd frontend

# Copy the environment template
cp .env.example .env

# Install dependencies
npm install

# Start the dev server (runs on port 5173)
npm run dev
```

### 4. Open in Browser

Navigate to **`http://localhost:5173`** — Sangyan Shield is ready.

### Quick Smoke Test (API)

```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Guaranteed 20% monthly returns. Send money to my UPI now. SEBI registered."}'
```

Expected response:
```json
{
  "risk_level": "high",
  "flags": [
    {"id": "guaranteed_returns", "reason": "Promising fixed or guaranteed returns..."},
    {"id": "personal_bank_transfer", "reason": "Asking you to send money..."},
    {"id": "sebi_claim", "reason": "Anyone can claim to be SEBI registered..."}
  ],
  "ml_scam_probability": 94.2,
  "next_steps": ["Do not send money", "..."],
  "disclaimer": "This is a risk indicator, not a legal finding."
}
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check — returns `{"status": "ok"}` |
| `GET` | `/api/guided/questions?lang=en` | Fetch guided-mode questions (supports `en`, `hi`) |
| `POST` | `/api/analyze` | Analyze free-text input — body: `{"text": "...", "language": "en"}` |
| `POST` | `/api/guided` | Analyze guided answers — body: `{"answers": [...], "language": "en"}` |

**Rate Limits:** 10 requests/minute per endpoint, 60/hour, 200/day (configurable).

---

## 🗺️ Roadmap & Limitations

### ⚠️ Honest Limitations (Hackathon Scope)

- **SEBI registry check uses demo data.** The `registry_demo.json` file is currently a placeholder. In production, this would query the official [SEBI intermediary search](https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doRecognisedFpi=yes&intmId=13).
- **ML model is trained on a curated seed dataset** (~45 examples). Accuracy will improve significantly with a larger, community-contributed corpus.
- **OCR module is scaffolded** (`ocr.py`) but not yet wired into the API. Users currently paste text manually rather than uploading screenshot images.
- **Speech synthesis quality** depends on the device's available voices — some older Android devices may not have Hindi TTS installed.

### 🔮 Future Plans

| Phase | Feature |
|---|---|
| **v1.1** | 📷 Screenshot OCR — upload a WhatsApp screenshot instead of pasting text (via `pytesseract`) |
| **v1.2** | 💬 WhatsApp Share Target — "Share to Sangyan Shield" from WhatsApp's share menu |
| **v1.3** | 🌐 Community Reporting — anonymous, privacy-preserving crowdsourced scam pattern database |
| **v1.4** | 🏛️ Live SEBI Registry — real-time verification against the SEBI intermediary database |
| **v2.0** | 📱 Offline PWA — full offline support with cached ML model for areas with poor connectivity |
| **v2.1** | 🗣️ Voice Input — speak the scam message instead of typing (Speech-to-Text → analysis) |

---

## 👥 Team

**Team UV** — Built for the SANGYAN Investor Resilience Hackathon 2026.

---

<p align="center">
  <strong>🛡️ Sangyan Shield</strong> — Because no one should lose their savings to a forwarded message.
</p>
