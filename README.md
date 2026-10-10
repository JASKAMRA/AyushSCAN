<h1 align="center">AyushScan</h1>

<p align="center"><i>AI-powered medical bill analyzer and health assistant for Bharat</i></p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Flask-WebApp-orange?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Gemini-AI-green?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/OCR-Tesseract%20%2B%20EasyOCR-purple?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Jan%20Aushadhi-Price%20Engine-teal?style=for-the-badge"/>
</p>

---

## What is AyushScan?

**AyushScan** is a healthcare web application that lets patients upload medical bills (images or PDFs), automatically detect overpriced medicines against the Jan Aushadhi reference dataset, and get help from an AI assistant that replies in English, Hindi, or Hinglish. The app's own interface is localized into English and Hindi. It is designed specifically for India's healthcare landscape — with personalized government scheme recommendations based on the user's state, caste category, and income level.

---

## Features

### Bill Scanning & OCR
- Upload medical bills as images (JPG, PNG, TIFF, WebP, BMP) or PDFs
- **Multi-pass OCR**: Tesseract runs several PSM/OEM configurations per image, plus EasyOCR as an additional pass if installed (it's an optional dependency); every candidate is scored and the best-scoring one is kept
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
- **Gemini fallback cascade**: on quota or timeout errors, retries across the configured `GEMINI_MODEL` (default `gemini-2.0-flash`) then `gemini-2.5-flash → gemini-2.0-flash-lite → gemini-flash-latest`, with exponential backoff on quota errors

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

### Multilingual AI Chatbot — Ayu
- Auto-detects English, Hindi, and Hinglish from the user's message (independent of the site's own UI language — see Localization below)
- Responds natively in the detected language — no post-translation
- Hindi responses use `temperature=0.1` for accuracy and consistency; language instructions are injected at top and bottom of every prompt
- Prompted to be warm and concise by default, use bullet points for multi-item answers, and say so explicitly when it's uncertain rather than guessing
- Remembers recent scan history and the last few chat exchanges for context
- **Voice assistant**: microphone input (Web Speech API STT) and spoken responses (TTS) in English and Hindi
  - Language selector: Auto / English / Hindi
  - Multi-strategy Hindi voice detection: exact `hi-IN` → `hi*` prefix → name hints (Lekha, Kalpana, Hemant, etc.)
  - Shows which voice was selected or instructions to install a Hindi voice on Windows

### Localization
- The app's own interface (navigation, forms, buttons, flash messages, error pages, CSV/PDF export labels) is translated into English and Hindi via Flask-Babel
- Language is chosen at signup/login or via the language switcher, stored per-account, and persisted across sessions
- This is separate from the chatbot's per-message language auto-detection above — switching the site language does not force the chatbot's reply language, and vice versa

### Hospital Search
- Live search for nearby hospitals via Overpass API (OpenStreetMap)
- Sorted by distance; optional Ayushman Bharat empanelment filter

### User Dashboard
- Scan history (last 50 scans), total estimated savings, chat message count
- Profile management: name, username, state, caste category, annual income
- Updating these profile fields improves scheme personalisation for future scans

### Authentication & Security
- Signup/login with Werkzeug password hashing (pbkdf2/scrypt)
- Forgot-password OTP flow: 15-minute expiry, Brevo transactional email API delivery
- **CSRF protection** (Flask-WTF) on every state-changing route — forms and JS `fetch` calls alike
- **Rate limiting**: login (10 attempts/min per email), OTP requests (5/5 min per email), bill scans (15/min per user) — tracked in-process, so this holds as long as the app runs as a single process
- **File upload validation**: extension allowlist (JPG/PNG/GIF/BMP/TIFF/WebP/PDF), 16 MB size limit, sanitized filenames; files that fail to decode as a real image/PDF are rejected
- Session cookies: `HttpOnly`, `SameSite=Lax`
- Security response headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`
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
├── Dockerfile              # Railway/container deployment with Tesseract installed
├── DEPLOYMENT.md           # Fast Railway deployment checklist
├── .env                    # Environment variables (never commit this)
├── .env.example            # Documents every env var the app reads, with placeholders
├── Procfile                # Alternate Procfile-style start command (gunicorn)
├── .python-version         # Pinned Python version for deployment
├── babel.cfg               # Flask-Babel string-extraction config
├── translations/           # Compiled English/Hindi UI translation catalogs
│   ├── en/LC_MESSAGES/
│   └── hi/LC_MESSAGES/
├── static/
│   ├── images/
│   ├── scripts/            # dashboard.js, login.js, signup.js, form-utils.js, forgot-password.js
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

# Create and activate a virtual environment (Python 3.13 is what this project is built/tested against)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Copy the env template and fill in real values (see Environment Variables below)
cp .env.example .env

# Start the Flask development server
python app.py
```

Open your browser at `http://127.0.0.1:5000`

The English and Hindi UI translations are already compiled into `translations/`. If you edit any translatable string in `app.py` or `templates/`, re-extract and recompile with `pybabel extract -F babel.cfg -o messages.pot .`, `pybabel update -i messages.pot -d translations`, then `pybabel compile -d translations`.

### Tesseract OCR (required)

Tesseract must be installed separately — it is not a Python package.

- **Windows**: download the installer from [github.com/tesseract-ocr/tesseract/releases](https://github.com/tesseract-ocr/tesseract/releases)
- **Ubuntu / Debian**: `sudo apt install tesseract-ocr`
- **macOS**: `brew install tesseract`

The app defaults to `C:\Program Files\Tesseract-OCR\tesseract.exe` on Windows. Override with `TESSERACT_CMD` in `.env`.

---

## Deployment

The recommended deployment is **Railway + Docker + Brevo + SQLite on a persistent volume**.

Railway uses the included `Dockerfile`, which installs Tesseract and starts the Flask app with Gunicorn. Create a Railway volume mounted at:

```text
/data
```

Then set:

```env
DATABASE_PATH=/data/users.db
```

The local `users.db` file is intentionally not committed or deployed. The production database is created fresh at `/data/users.db` and survives redeploys as long as the Railway volume remains attached.

See `DEPLOYMENT.md` for the exact step-by-step checklist.

---

## Environment Variables (`.env`)

Create a `.env` file at the project root (same folder as `app.py`).

```env
# Gemini AI — bill structuring, chatbot, scheme recommendations
# Get your key from https://aistudio.google.com/apikey
GOOGLE_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash

# Flask session-signing secret (generate with: python -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=your_random_secret_key

# Email — OTP delivery and contact form through Brevo API
BREVO_API_KEY=your_brevo_api_key
BREVO_SENDER_EMAIL=verified_sender@example.com
BREVO_SENDER_NAME=AyushScan
CONTACT_EMAIL=your_contact_receiver@example.com
EMAIL_REPLY_TO=

# SQLite database path. Use /data/users.db on Railway with a mounted /data volume.
DATABASE_PATH=/data/users.db

# Optional overrides (defaults shown)
TESSERACT_CMD=tesseract
TESSERACT_LANG=eng
PDF_OCR_MAX_PAGES=12
PDF_OCR_SCALE=3.5
```

A filled-in template with comments for every variable is in `.env.example`.

**Getting a Gemini API key**
Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey), sign in with a Google account, and click **Create API key**. Depending on when the key was issued it will start with either `AIza` (older "Standard" keys) or `AQ.` (current "Auth" keys) — the app accepts both. Paste it as the value of `GOOGLE_API_KEY`.

**Getting Brevo email credentials**
Create a Brevo account, enable transactional email, create an API key, and add a verified sender email. Use that API key as `BREVO_API_KEY` and the verified sender as `BREVO_SENDER_EMAIL`.

> **Note:** The app works without a Gemini API key — OCR, price lookup, and rule-based analysis still function. Gemini-powered features (structured extraction, chatbot, scheme suggestions) fall back to a rule-based engine.

> **Security:** `.env` is excluded from version control by `.gitignore` — never commit it. If `SECRET_KEY` is left unset, the app logs a warning and falls back to an insecure development default; always set a real one before deploying.

---

## API Status

Visit `/api/status` to check the health of the Gemini and email integrations:

```json
{
  "google_api_key_set": true,
  "google_api_key_format_ok": true,
  "google_api_key_hint": "AQ.Ab8…",
  "gemini_model": "gemini-2.0-flash",
  "gemini_ping": "ok",
  "email_configured": true,
  "email_provider": "brevo",
  "database_path": "/data/users.db",
  "tesseract_path": "tesseract",
  "tesseract_python_package_installed": true,
  "pdf_renderer_installed": true,
  "easyocr_installed": false,
  "products_loaded": 2439
}
```

If `google_api_key_format_ok` is `false`, check that `GOOGLE_API_KEY` is set and starts with `AIza` or `AQ.`. If `gemini_ping` isn't `"ok"`, it contains the exact error from the last live call to Gemini.

---

## Developers

→ Akshita Sachdeva

→ Jas Kamra
