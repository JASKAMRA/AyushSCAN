# AyushScan

AyushScan is a Flask web application for scanning medical bills, extracting likely bill items with OCR, comparing medicine prices against a Jan Aushadhi reference CSV, and giving users a dashboard, chatbot, and nearby healthcare search.

The app is currently a single Flask project. Flask serves the backend routes, Jinja templates, static CSS/JS, authentication, OCR flow, dashboard pages, and APIs together.

## Current Features

### Bill Upload and OCR

- Upload image bills and PDFs.
- Uses Tesseract through `pytesseract` for OCR.
- Uses `pypdf` and `pypdfium2` for PDF text extraction and scanned PDF fallback rendering.
- Runs multiple Tesseract configurations and image preprocessing variants, then selects the best-scoring OCR text.
- Returns an `ocr_quality` estimate for each scan:
  - `high`: likely usable for automated analysis with review.
  - `medium`: usable, but medicine names, quantities, and prices should be checked.
  - `low` / `failed`: user should upload a clearer image/PDF.
- EasyOCR is optional and is not installed in the default deployment because it makes the app heavier.

### Bill Analysis

- Extracts likely medicine and bill line items from OCR text.
- Uses Gemini when `GOOGLE_API_KEY` is configured.
- Falls back to rule-based parsing when Gemini is unavailable.
- Compares detected medicine-like items with `products.csv`.
- Shows estimated savings and confidence tiers.
- Requires user review of quantities/prices before final analysis.

The app should not be treated as a medical, legal, or billing authority. OCR and AI extraction can be wrong, especially on blurred, handwritten, cropped, or low-light bills.

### Chatbot

- Chatbot page for billing, medicine price, hospital, and Ayushman Bharat style questions.
- Uses Gemini when configured.
- Falls back to a limited local response mode if Gemini is unavailable.
- Supports English/Hindi/Hinglish style handling through prompt and language-detection logic.

### Hospital Search

- Uses browser geolocation and OpenStreetMap Overpass API.
- Searches nearby hospitals, clinics, and healthcare entries.
- Sorts results by distance.
- Shows a possible Ayushman/PM-JAY indicator based only on OpenStreetMap tags.
- This is not an official empanelment database. Users must verify PM-JAY status with official government/PM-JAY sources or with the hospital.
- Public Overpass API availability may vary, so hospital search can occasionally fail or return incomplete data.

### User Accounts

- Signup/login with hashed passwords.
- Forgot-password OTP flow through Brevo Transactional Email API.
- Dashboard stores scan history, estimated savings, chat count, and profile fields.
- SQLite is used by default.

### Reporting

- Export scan results as CSV or PDF when report generation dependencies are available.

## Tech Stack

- Python 3.13
- Flask
- SQLite
- Tesseract OCR
- Gemini API through `google-genai`
- Brevo Transactional Email API
- Railway deployment using Docker

## Project Structure

```text
AyushSCAN/
├── app.py
├── products.csv
├── requirements.txt
├── Dockerfile
├── DEPLOYMENT.md
├── .env.example
├── .gitignore
├── babel.cfg
├── Procfile
├── static/
├── templates/
├── translations/
└── migrations/
```

`users.db`, `.env`, uploads, and Python bytecode are intentionally not committed.

## Local Setup

Create a virtual environment:

```bash
python -m venv venv
```

Activate it.

Windows:

```bash
venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy the environment template:

```bash
cp .env.example .env
```

On Windows, if Tesseract is installed at the default path, use:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

On Railway/Linux, use:

```env
TESSERACT_CMD=tesseract
```

Run locally:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Required Environment Variables

```env
SECRET_KEY=
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-2.0-flash

BREVO_API_KEY=
BREVO_SENDER_EMAIL=
BREVO_SENDER_NAME=AyushScan
CONTACT_EMAIL=
EMAIL_REPLY_TO=

DATABASE_PATH=/data/users.db
TESSERACT_CMD=tesseract
TESSERACT_LANG=eng
PDF_OCR_MAX_PAGES=12
PDF_OCR_SCALE=3.5
FLASK_DEBUG=0
```

Notes:

- `SECRET_KEY` can be generated with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

- `GOOGLE_API_KEY` comes from Google AI Studio.
- `BREVO_API_KEY` and `BREVO_SENDER_EMAIL` come from Brevo Transactional Email.
- `BREVO_SENDER_EMAIL` must be a verified sender in Brevo.
- `DATABASE_PATH=/data/users.db` is for Railway with a persistent `/data` volume.

## Deployment

The current recommended deployment is Railway with Docker.

1. Push the project to GitHub.
2. Create a Railway project from the GitHub repo.
3. Let Railway build with the included `Dockerfile`.
4. Add a Railway volume mounted at:

```text
/data
```

5. Set:

```env
DATABASE_PATH=/data/users.db
```

The deployed SQLite database is created fresh at `/data/users.db`. It survives redeploys only if the Railway volume remains attached.

Do not commit or deploy a local `users.db`.

## Health Checks

After deployment, open:

```text
https://your-railway-domain/api/status
```

Expected healthy values include:

```json
{
  "database_path": "/data/users.db",
  "email_configured": true,
  "email_provider": "brevo",
  "gemini_ping": "ok",
  "google_api_key_format_ok": true,
  "pdf_renderer_installed": true,
  "products_loaded": 2439,
  "tesseract_path": "tesseract",
  "tesseract_python_package_installed": true
}
```

For email config only:

```text
https://your-railway-domain/api/email-status
```

This confirms whether Brevo variables are present, but actual delivery still depends on Brevo sender verification and account status.

## Database Notes

SQLite is acceptable for demo and low-traffic usage. Keep Railway mounted to `/data` so redeploys do not erase users and scan history.

Consider Postgres later if the app needs high traffic, multiple app instances, stronger backups, or concurrent write reliability.

## OCR Accuracy

The app cannot claim a fixed OCR accuracy percentage without a labeled test dataset. OCR quality depends heavily on:

- image clarity
- lighting
- angle/skew
- handwriting vs printed text
- PDF text layer quality
- medicine spelling and layout

Use the returned `ocr_quality` field and manual review step before trusting extracted quantities or prices.

## Known Limitations

- OCR and Gemini extraction can make mistakes.
- EasyOCR is optional and not included in the default Docker image.
- Hospital search depends on public OpenStreetMap/Overpass data, which can be incomplete or temporarily unavailable.
- Ayushman/PM-JAY hospital status is not officially verified by this app.
- In-process rate limiting resets when the app restarts and is not shared across multiple instances.
- SQLite is not intended for heavy multi-instance production workloads.

## Developers

- Akshita Sachdeva
- Jas Kamra
