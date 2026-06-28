<h1 align="center">AyushScan</h1>

<p align="center"><i>AI-powered medical bill analyzer and health assistant for Bharat</i></p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Flask-WebApp-orange?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Gemini-AI-green?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/OCR-Tesseract%20%2B%20EasyOCR-purple?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Jan%20Aushadhi-Price%20Engine-teal?style=for-the-badge"/>
</p>

---

## Demo Video

<p align="center">
  <a href="https://youtu.be/pqgdbEKCr8Y" target="_blank">
    <img src="https://img.youtube.com/vi/pqgdbEKCr8Y/0.jpg" alt="AyushScan Demo" width="60%" />
  </a><br>
  <i>Click the image to view the demo</i>
</p>

---

## What is AyushScan?

**AyushScan** is a production-grade healthcare web application that lets patients upload medical bills (images or PDFs), automatically detect overpriced medicines against the Jan Aushadhi reference dataset, and receive AI-guided health assistance in English, Hindi, or Hinglish. It is designed specifically for India's healthcare landscape — with personalized government scheme recommendations based on the user's state, caste category, and income level.

---

## Features

### Bill Scanning & OCR
- Upload medical bills as images (JPG, PNG, TIFF, WebP, BMP) or PDFs
- **Dual OCR engine**: Tesseract (multi-PSM/OEM configurations) + EasyOCR running in parallel; results are merged by confidence
- **Fast path for printed documents**: light preprocessing (autocontrast, contrast ×1.5, sharpen ×1.2) with a quality score short-circuit — skips the heavy handwriting pipeline when the bill is clearly printed
- **Handwritten OCR pipeline**: deskew, denoise, multi-scale processing, binarization, combined confidence scoring
- **PDF support**: text-layer extraction (pypdfium2) with image OCR fallback for scanned PDFs

### AI Bill Analysis
- Gemini AI extracts and structures every line item: medicine name, quantity, pack size, unit price, line total
- Classifies items into categories: medicines, lab tests, consultations, procedures, room charges, GST, miscellaneous
- Compares each item against the Jan Aushadhi CSV price database
- Calculates overbilling per item and total estimated savings
- Shows Jan Aushadhi generic equivalent note per overpriced item
- **Confidence tiering**: High / Medium / Low — items with insufficient evidence are clearly labelled, not silently wrong
- **Gemini fallback cascade**: if quota is hit, retries across `gemini-1.5-flash → gemini-1.5-flash-8b → gemini-2.0-flash-lite → gemini-2.0-flash` with exponential backoff

### Jan Aushadhi Savings Engine
- Matches brand-name medicines from your bill to generic equivalents from the Jan Aushadhi dataset
- Shows per-item savings potential with normalized per-tablet pricing
- Displays a total savings banner on the result page
- Links to the official Jan Aushadhi store locator

### Personalized Government Scheme Recommendations
- After each scan, suggests government schemes relevant to the detected treatment
- Personalized by the user's **state** (10 states supported), **caste category** (General / SC / ST / EWS), and **annual income**
- Includes PM-JAY / Ayushman Bharat with working eligibility check link, state-specific health schemes, and caste/income-based welfare schemes
- Gemini powers the primary suggestion; a rule-based engine handles fallback

### Multilingual AI Chatbot — Lia
- Auto-detects English, Hindi, and Hinglish from the user's message
- Responds natively in the detected language — no post-translation
- Hindi responses use `temperature=0.1` for accuracy and consistency; language instructions are injected at top and bottom of every prompt
- Remembers recent scan history and previous chat context
- **Voice assistant**: microphone input (Web Speech API STT) and spoken responses (TTS) in English and Hindi
  - Language selector: Auto / English / Hindi
  - Multi-strategy Hindi voice detection: exact `hi-IN` → `hi*` prefix → name hints (Lekha, Kalpana, Hemant, etc.)
  - Shows which voice was selected or instructions to install a Hindi voice on Windows

### Hospital Search
- Live search for nearby hospitals via Overpass API (OpenStreetMap)
- Sorted by distance; optional Ayushman Bharat empanelment filter

### User Dashboard
- Scan history (last 50 scans), total estimated savings, chat message count
- Profile management: name, username, state, caste category, annual income
- Updating these profile fields improves scheme personalisation for future scans

### Authentication & Security
- Signup/login with Werkzeug password hashing (pbkdf2/scrypt)
- Forgot-password OTP flow: 15-minute expiry, Gmail SMTP delivery
- **CSRF protection** on all state-changing routes
- **Rate limiting**: login (10/min), forgot password (5/5 min), bill scan (per-user), contact form
- **File upload validation**: extension allowlist + MIME sniffing; 16 MB limit
- Secure session cookies: `HttpOnly`, `SameSite=Lax`
- All user inputs sanitized and length-capped before storage or logging

### Reporting
- Export scan results as **CSV** or **PDF** (ReportLab)
- Results page is fully mobile-responsive with horizontal scroll on wide tables

---

## Project Structure

```
AyushSCAN/
├── app.py                  # Main Flask app — routes, OCR, AI analysis, auth, chatbot
├── products.csv            # Jan Aushadhi reference dataset (generic medicine prices)
├── requirements.txt
├── .env                    # Environment variables (never commit this)
├── static/
│   ├── images/
│   ├── scripts/            # dashboard.js, login.js, signup.js
│   └── styles/             # dashboard.css, result.css, per-page CSS
└── templates/              # Jinja2 HTML templates
    ├── dashboard.html
    ├── result.html
    ├── chatbot.html
    └── ...
```

---

## How to Run Locally

```bash
# Clone the repository
git clone https://github.com/JASKAMRA/AyushSCAN
cd AyushSCAN

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Start the Flask development server
python app.py
```

Open your browser at `http://127.0.0.1:5000`

### Tesseract OCR (required)

Tesseract must be installed separately — it is not a Python package.

- **Windows**: download the installer from [github.com/tesseract-ocr/tesseract/releases](https://github.com/tesseract-ocr/tesseract/releases)
- **Ubuntu / Debian**: `sudo apt install tesseract-ocr`
- **macOS**: `brew install tesseract`

The app defaults to `C:\Program Files\Tesseract-OCR\tesseract.exe` on Windows. Override with `TESSERACT_CMD` in `.env`.

---

## Environment Variables (`.env`)

Create a `.env` file at the project root (same folder as `app.py`).

```env
# Gemini AI — bill structuring, chatbot, scheme recommendations
# Get your key from https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=your_gemini_api_key_here

# Email — OTP delivery and contact form
EMAIL_ADDRESS=your_gmail@gmail.com
EMAIL_PASSWORD=your_gmail_app_password   # Use an App Password, not your account password

# Optional overrides (defaults shown)
SECRET_KEY=change-this-in-production
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
TESSERACT_LANG=eng
GEMINI_MODEL=gemini-1.5-flash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
PDF_OCR_MAX_PAGES=12
PDF_OCR_SCALE=3.5
```

**Getting a Gemini API key**
Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey), sign in with a Google account, and click **Create API key**. The key will start with `AIza`. Paste it as the value of `GOOGLE_API_KEY`.

**Getting a Gmail App Password**
Enable 2-Step Verification on your Google account, then go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) and generate an app password for "Mail". Use that 16-character password as `EMAIL_PASSWORD`.

> **Note:** The app works without a Gemini API key — OCR, price lookup, and rule-based analysis still function. Gemini-powered features (structured extraction, chatbot, scheme suggestions) will use the rule-based fallback.

> **Security:** Your `.env` file is excluded from version control by `.gitignore`. Never commit it to GitHub.

---

## API Status

Visit `/api/status` to check the health of all integrations:

```json
{
  "google_api_key_present": true,
  "google_api_key_format_ok": true,
  "gemini_model": "gemini-1.5-flash",
  "jan_aushadhi_products_loaded": 1547,
  "tesseract_available": true,
  "easyocr_available": true
}
```

If `google_api_key_format_ok` is `false`, check that `GOOGLE_API_KEY` is set correctly in your `.env`.

---

## Developers

→ Akshita Sachdeva

→ Jas Kamra
