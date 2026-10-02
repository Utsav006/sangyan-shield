"""
Train a lightweight TF-IDF + Logistic Regression scam classifier.

Run once to generate model artifacts:
    python train_ml.py

Outputs:
    backend/models/vectorizer.pkl
    backend/models/classifier.pkl
"""

from __future__ import annotations

import os
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

# ---------------------------------------------------------------------------
# Training data — 1 = scam, 0 = genuine
# ---------------------------------------------------------------------------
SCAM_TEXTS = [
    # Guaranteed / unrealistic returns
    "Join our VIP trading group — guaranteed 500% returns in 30 days!",
    "SEBI certified advisor with 100% guaranteed profit. No loss. DM now.",
    "Earn Rs 50,000 daily from home. Zero investment. WhatsApp 98765XXXXX.",
    "Get 10x returns on crypto — join our exclusive signal group today!",
    "Guaranteed monthly income of ₹1 lakh. Join our stock trading course.",

    # OTP / credential pressure
    "Your bank account has been blocked. Share OTP immediately to unblock.",
    "SBI alert: Your KYC is expired. Share your Aadhaar and OTP to renew.",
    "RBI has flagged your account. Verify now by sharing your PIN and OTP.",
    "Urgent: Your UPI account will be deactivated. Send OTP to verify.",
    "Your ATM card is blocked. Call this number and share OTP to reactivate.",

    # Fake authority / SEBI
    "This is SEBI registered advisor INZ000XXXXX. Invest now for safe returns.",
    "Government approved scheme — double your money in 45 days. Limited slots.",
    "PM Yojana special offer — invest ₹5000 get ₹50000. Hurry, last date today!",

    # Urgency / pressure tactics
    "LAST CHANCE! Send ₹10,000 now to claim your lottery prize of ₹50 lakh.",
    "Act NOW or lose this opportunity forever. Only 3 seats left in our group.",
    "Your cousin is in police custody. Transfer ₹25,000 immediately for bail.",
    "You have won a lucky draw! Pay ₹2,000 processing fee to claim your prize.",

    # WhatsApp / link scams
    "Click this link to get free ₹500 cashback: bit.ly/freecash-offer",
    "Forward this message to 10 people to activate your new WhatsApp features.",
    "Exclusive Telegram group for insider stock tips — join now: t.me/profitking",

    # Hindi scam messages
    "गारंटीड रिटर्न — 30 दिनों में 500% मुनाफ़ा। अभी जॉइन करें।",
    "आपका बैंक अकाउंट ब्लॉक हो गया है। तुरंत OTP भेजें।",
    "सरकार की नई योजना — ₹5000 लगाएँ, ₹50000 पाएँ। सीमित सीटें।",
]

GENUINE_TEXTS = [
    # Educational / informational
    "Mutual fund investments are subject to market risks. Read scheme documents carefully.",
    "SEBI has issued new guidelines for margin trading effective from next quarter.",
    "The RBI has kept the repo rate unchanged at 6.5% in its latest policy meeting.",
    "Here are 5 tips to start your SIP journey: diversify, stay consistent, and review annually.",
    "Understanding the difference between debt and equity mutual funds for beginners.",

    # Official bank communications
    "Your fixed deposit of ₹1,00,000 has matured. Visit your branch to renew.",
    "Your credit card statement for September is ready. Log in to view details.",
    "Monthly account summary: 3 debits, 5 credits. Available balance: ₹45,230.",
    "Your SIP of ₹5,000 in HDFC Balanced Advantage Fund has been processed.",
    "Reminder: Your EMI of ₹8,500 is due on October 5th.",

    # Genuine financial news
    "Sensex closes 200 points higher today driven by IT and banking stocks.",
    "Gold prices fall by ₹500 per 10 grams amid global market correction.",
    "Budget 2026 proposes increased tax rebate for income up to ₹12 lakh.",
    "India's GDP growth for Q2 stands at 7.1%, exceeding market expectations.",
    "NIFTY 50 index composition to be reviewed next month by NSE.",

    # General conversation about finance
    "I recently started investing in index funds through Zerodha. The process was smooth.",
    "Can you recommend a good book on personal finance for Indian investors?",
    "My financial advisor suggested I increase my emergency fund to 6 months of expenses.",
    "The new tax regime seems beneficial if you don't have many deductions to claim.",
    "I'm planning to open a PPF account for long-term savings. Any advice?",

    # Hindi genuine messages
    "म्यूचुअल फंड निवेश बाज़ार जोखिमों के अधीन है। कृपया दस्तावेज़ ध्यान से पढ़ें।",
    "आपकी SIP ₹5,000 की प्रोसेस हो गई है। धन्यवाद।",
    "बजट 2026 में ₹12 लाख तक की आय पर टैक्स छूट बढ़ाई गई है।",
]

# ---------------------------------------------------------------------------
# Build labelled arrays
# ---------------------------------------------------------------------------
texts = SCAM_TEXTS + GENUINE_TEXTS
labels = np.array([1] * len(SCAM_TEXTS) + [0] * len(GENUINE_TEXTS))

print(f"Dataset: {len(SCAM_TEXTS)} scam + {len(GENUINE_TEXTS)} genuine = {len(texts)} total")

# ---------------------------------------------------------------------------
# TF-IDF Vectorizer
# ---------------------------------------------------------------------------
vectorizer = TfidfVectorizer(
    max_features=3000,
    ngram_range=(1, 2),           # unigrams + bigrams
    sublinear_tf=True,
    strip_accents="unicode",
    stop_words="english",
    min_df=1,
)

X = vectorizer.fit_transform(texts)
print(f"Vocabulary size: {len(vectorizer.vocabulary_)}")

# ---------------------------------------------------------------------------
# Logistic Regression classifier
# ---------------------------------------------------------------------------
clf = LogisticRegression(
    C=1.0,
    max_iter=1000,
    solver="lbfgs",
    class_weight="balanced",      # handle any class imbalance
    random_state=42,
)

clf.fit(X, labels)

# Quick cross-validation sanity check
scores = cross_val_score(clf, X, labels, cv=min(5, len(texts)), scoring="accuracy")
print(f"Cross-val accuracy: {scores.mean():.2%} (+/- {scores.std():.2%})")

# ---------------------------------------------------------------------------
# Save artifacts
# ---------------------------------------------------------------------------
MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

vectorizer_path = MODEL_DIR / "vectorizer.pkl"
classifier_path = MODEL_DIR / "classifier.pkl"

joblib.dump(vectorizer, vectorizer_path)
joblib.dump(clf, classifier_path)

print(f"\nSaved:")
print(f"  Vectorizer -> {vectorizer_path}")
print(f"  Classifier -> {classifier_path}")
print(f"  Vectorizer size: {os.path.getsize(vectorizer_path) / 1024:.1f} KB")
print(f"  Classifier size: {os.path.getsize(classifier_path) / 1024:.1f} KB")
print("\nDone! The hybrid engine will load these on startup.")
