# Sangyan Shield
### SANGYAN Investor Resilience Hackathon

## Project Summary
Sangyan Shield is a hybrid intelligence tool designed to protect Indian retail investors from sophisticated financial scams. By analyzing text messages, screenshots, and URLs, it detects phishing attempts, fake SEBI registrations, and illegal "guaranteed returns" schemes. With a seamless user experience prioritizing non-technical users, it serves as a critical first line of defense against financial fraud.

## Key Features
- **PWA WhatsApp Zero-Copy-Paste Flow**: Users can share suspicious messages or screenshots directly from WhatsApp into Sangyan Shield via the native Android/iOS Web Share Target API—no manual copying and pasting required.
- **Bilingual Support**: Fully supports both Hindi and English, ensuring accessibility for a vast demographic of Indian retail investors.
- **Offline Capabilities**: Core components, including the offline SEBI registry fallback and deterministic rule engine, ensure the app remains functional even in low-connectivity areas or if SEBI's servers go down.

## Architecture
Sangyan Shield leverages a **Hybrid Engine** for maximum accuracy:
- **Deterministic Rules**: Instantly flags well-known patterns (e.g., asking for OTPs, personal bank transfers, urgent pressure).
- **TF-IDF & Logistic Regression**: A machine learning classifier trained on financial scam datasets to identify subtle, evolving scam languages and provide a scam probability score.
- **Real-time SEBI Web Scraper**: Dynamically queries the official SEBI Recognised Intermediaries portal to verify claimed SEBI registration numbers, with a curated JSON dataset fallback for speed and resilience.
- **Tesseract OCR**: Extracts text from screenshots of chat bubbles or SMS messages with advanced Pillow-based preprocessing optimized for mobile screenshots.

## Setup Instructions
To run Sangyan Shield locally for development and testing:

### Backend (Flask)
1. Navigate to the `backend` directory: `cd backend`
2. Install Python dependencies: `pip install -r requirements.txt`
3. Ensure you have the Tesseract binary installed on your OS (and in your PATH).
4. Start the Flask server: `python app.py` (Runs on `http://localhost:5000`)

### Frontend (React + Vite)
1. Navigate to the `frontend` directory: `cd frontend`
2. Install Node.js dependencies: `npm install`
3. Start the development server: `npm run dev` (Runs on `http://localhost:5173`)

## Demo Instructions (Testing WhatsApp PWA Share)
To test the Web Share Target functionality from a mobile device (like WhatsApp sharing):
1. Expose your local frontend server to the internet using a tunneling service like **localtunnel** or **ngrok**:
   ```bash
   npx localtunnel --port 5173
   # OR
   ngrok http 5173
   ```
2. Open the generated HTTPS URL on your mobile browser (Chrome/Safari).
3. "Install" or "Add to Home Screen" to install the PWA.
4. Open WhatsApp, select any text message, tap "Share", and select "Sangyan Shield" from the native share menu. The text will be seamlessly handed off to the app for instant analysis!

---
*Built for the SANGYAN Investor Resilience Hackathon.*
