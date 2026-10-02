<p align="center">
  <img src="frontend/public/favicon.svg" width="80" alt="Sangyan Shield Logo" />
</p>

<h1 align="center">Sangyan Shield 🛡️</h1>

<p align="center">
  <strong><em>"For the moment you can't copy-paste."</em></strong>
</p>

<p align="center">
  Built for the <strong>SANGYAN Investor Resilience Hackathon</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/PWA-Enabled-5A0FC8?logo=pwa&logoColor=white" alt="PWA" />
  <img src="https://img.shields.io/badge/scikit--learn-ML-F7931E?logo=scikit-learn&logoColor=white" alt="scikit-learn" />
  <img src="https://img.shields.io/badge/License-Hackathon_Submission-green" alt="License" />
</p>

---

## 🎯 The Problem

Financial access in India has outrun financial confidence.

> **240 million** new demat accounts were opened in the last 4 years. Many belong to first-time investors in Tier-2 and Tier-3 cities — people who arrived at the stock market via WhatsApp forwards, not finance textbooks.

Scammers exploit this gap. They run fake "SEBI-registered" tip groups, promise guaranteed returns, demand urgent UPI transfers, and share phishing links — all via the same WhatsApp that Ramesh uses to talk to his family.

### Meet Ramesh 👤

> **Ramesh, 55, lives in Raipur.** He recently opened a demat account after his nephew showed him how. Last Tuesday, he was added to a WhatsApp group called _"SEBI Certified Premium Stock Tips 💰"_ that promises 20% monthly returns. The group admin shared a SEBI registration number — `INA000099999` — to prove legitimacy. Ramesh is about to send ₹25,000 via GPay.

**Sangyan Shield exists so Ramesh can check before he sends.**

He forwards that WhatsApp message to our app. In under 2 seconds, he gets a clear, spoken-aloud verdict in Hindi: _"उच्च जोखिम — संभवतः घोटाला"_ (High risk — likely a scam). The fake SEBI number is flagged in red. Ramesh keeps his money.

---

## ✨ Killer Features

### 📲 WhatsApp Share Target Integration `NEW`

Our tagline is _"For the moment you can't copy-paste"_ — and we mean it literally.

As a **Progressive Web App (PWA)**, Sangyan Shield registers itself in the native OS share menu. Users can:

1. Long-press any WhatsApp message
2. Tap **Share → Sangyan Shield**
3. Get an instant scam verdict — **zero typing, zero copy-paste**

The shared text auto-populates and **auto-submits** within 600ms. The user goes from WhatsApp to a verdict in one tap.

---

### 🏦 Live SEBI Registry Verification `NEW`

Scammers love quoting fake SEBI registration numbers. We catch them.

- **Regex extraction** automatically detects SEBI-format numbers (`INA`, `INH`, `INB`, `INP`, `INR`, `INZ`, `INM`, `IND` prefixes) anywhere in the message
- **Simulated live lookup** verifies the number against a curated SEBI intermediary database
- If the number is **not found** → a 🚨 **"FAKE SEBI NUMBER DETECTED"** badge appears with a critical +50 risk score penalty
- If verified → a ✅ green badge shows the entity name and type

This turns a common social engineering attack vector into an instant red flag.

---

### 🤖 Hybrid Detection Engine

We don't rely on a single model. Our engine blends **two independent signals**:

| Layer | Purpose | How |
|-------|---------|-----|
| **Rule Engine** | Explainability | 7 deterministic rules with regex pattern matching across English + Hindi, weighted scoring, and span highlighting |
| **ML Model** | Coverage | TF-IDF + Logistic Regression classifier trained on Indian financial scam corpus, outputting a 0–100% **AI Confidence Score** |

The **hybrid blender** ensures:
- Rules catch known patterns with explainable reasons
- ML catches zero-day scams that rules haven't seen
- If ML says >70% scam but rules found nothing → escalate to "Be careful"
- If both agree → escalate to "High risk"

Neither system can downgrade the other's high-confidence detection.

---

### 🗣️ Bharat-First UX

Designed for the 500 million Indians who think in Hindi but receive scams in English:

- **🔤 Hindi ↔ English toggle** — every label, flag, and next-step is fully translated
- **🔊 Voice synthesis** — "Hear this result" button reads the entire verdict aloud in `hi-IN` or `en-IN`
- **✅ Guided Mode** — 6 yes/no questions for high-pressure phone call situations where the user can't type. No literacy barrier
- **📱 Mobile-first** — 480px max-width, 48px tap targets, high-contrast UI with WCAG-friendly colors

---

### 🩹 Recovery Path

For users who have already sent money — because prevention alone isn't enough:

1. Call your bank fraud helpline immediately
2. Stop all further payments
3. Save screenshots of chats, UPI IDs, and phone numbers
4. File a complaint on **cybercrime.gov.in**
5. Dial **1930** (India cyber fraud helpline)
6. Tell a trusted family member — you don't have to handle this alone

---

## 🔒 Strict Guardrail Compliance

This is critical for the hackathon and for real users. Sangyan Shield adheres to strict ethical guardrails:

| Guardrail | Implementation |
|-----------|---------------|
| **Zero PII stored** | No user messages are saved, logged, or transmitted beyond the analysis request |
| **No OTP / SMS access** | We never request, read, or intercept OTPs or SMS messages |
| **Images deleted instantly** | OCR-processed images are never persisted to disk |
| **Non-commercial** | No ads, no premium tier, no monetization of any kind |
| **No financial advice** | We provide risk indicators only — every verdict carries the disclaimer: _"This is a risk indicator, not a legal finding"_ |
| **No stock tips** | Sangyan Shield will never recommend buying, selling, or holding any security |
| **Offline-capable** | Service worker caches the app shell for use in low-connectivity areas |

---

## 🚀 Local Setup & Testing

### Prerequisites

- **Python** 3.10+
- **Node.js** 18+
- **npm** 9+

### 1. Clone the repository

```bash
git clone https://github.com/Utsav006/sangyan-shield.git
cd sangyan-shield
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
python train_ml.py           # Generate ML model artifacts
python app.py                # Start Flask on http://localhost:5000
```

### 3. Frontend setup (new terminal)

```bash
cd frontend
npm install
npm run dev                  # Start Vite dev server on http://localhost:5173
```

### 4. Run tests

```bash
cd backend
pytest test_engine.py -v     # Unit tests for the hybrid engine
```

> **Tip:** The frontend proxies API calls to `http://localhost:5000`. Make sure the backend is running first.

---

## 🏗️ Tech Stack

### Frontend
| Technology | Version | Purpose |
|-----------|---------|---------|
| React | 19 | Component UI |
| React Router | 7 | Client-side routing |
| Vite | 8 | Build tooling & HMR |
| vite-plugin-pwa | 1.3 | PWA manifest, service worker, Web Share Target |
| Web Speech API | Native | Voice synthesis for verdicts |

### Backend
| Technology | Version | Purpose |
|-----------|---------|---------|
| Flask | 3.x | REST API server |
| Flask-CORS | 6.x | Cross-origin for frontend |
| Flask-Limiter | 4.x | Rate limiting (10 req/min per endpoint) |
| scikit-learn | 1.7 | TF-IDF + Logistic Regression classifier |
| Joblib | 1.5 | Model serialization |
| Pillow + Tesseract | — | OCR for screenshot analysis |
| Regex Rule Engine | Custom | 7 weighted rules, bilingual pattern matching |

### Data & Models
| File | Purpose |
|------|---------|
| `backend/rules.json` | 7 deterministic scam-detection rules with Hindi + English patterns |
| `backend/data/sebi_intermediaries.json` | Simulated SEBI registry (13 entries, 8 prefix types) |
| `backend/models/vectorizer.pkl` | TF-IDF vectorizer (generated by `train_ml.py`) |
| `backend/models/classifier.pkl` | Logistic Regression classifier (generated by `train_ml.py`) |

---

## 📁 Project Structure

```
sangyan-shield/
├── backend/
│   ├── app.py                  # Flask API server
│   ├── engine.py               # Hybrid detection engine (rules + ML)
│   ├── registry.py             # SEBI number extraction & verification
│   ├── train_ml.py             # ML model training script
│   ├── test_engine.py          # Unit tests (pytest)
│   ├── rules.json              # Deterministic rule definitions
│   ├── guided.json             # Guided mode question config
│   ├── data/
│   │   └── sebi_intermediaries.json  # Simulated SEBI registry
│   └── models/
│       ├── vectorizer.pkl      # TF-IDF vectorizer
│       └── classifier.pkl      # Trained classifier
├── frontend/
│   ├── vite.config.js          # Vite + PWA config with share_target
│   ├── index.html              # Entry point
│   ├── public/
│   │   └── favicon.svg         # App icon
│   └── src/
│       ├── App.jsx             # Router & layout shell
│       ├── App.css             # Full design system
│       ├── LanguageContext.jsx  # i18n provider
│       ├── i18n/
│       │   ├── en.json         # English translations
│       │   └── hi.json         # Hindi translations
│       └── components/
│           ├── Home.jsx        # Landing page + share tip
│           ├── MessageInput.jsx # Text input + share target handler
│           ├── GuidedMode.jsx  # Yes/No question wizard
│           ├── Verdict.jsx     # Result page + SEBI badge
│           └── Recovery.jsx    # Post-scam recovery checklist
└── README.md
```

---

## 👥 Team UV

Built with ❤️ for Bharat's retail investors.

> _"Sangyan" (संज्ञान) means awareness — because the best defence against a scam is knowing it's one._

---

<p align="center">
  <strong>Sangyan Shield</strong> — Check before you send. 🛡️
</p>
