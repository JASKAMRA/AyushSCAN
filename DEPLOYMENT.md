# AyushScan Deployment

Recommended quick deployment: Railway with Docker, Brevo email API, and a persistent volume for SQLite.

## Required Inputs

- `GOOGLE_API_KEY`: Gemini API key.
- `SECRET_KEY`: generate with `python -c "import secrets; print(secrets.token_hex(32))"`.
- `BREVO_API_KEY`: Brevo transactional email API key.
- `BREVO_SENDER_EMAIL`: verified sender email in Brevo.
- `BREVO_SENDER_NAME`: usually `AyushScan`.
- `CONTACT_EMAIL`: email address that receives contact form messages.

## Railway Setup

1. Push this `AyushSCAN` folder to GitHub.
2. Create a Railway project from the GitHub repo.
3. Railway should detect and use `Dockerfile`.
4. Add a volume mounted at:

```text
/data
```

5. Add these variables:

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
```

6. Deploy.
7. Open `/api/status` on the deployed URL and check:

```json
{
  "email_configured": true,
  "email_provider": "brevo",
  "database_path": "/data/users.db",
  "tesseract_python_package_installed": true,
  "pdf_renderer_installed": true,
  "products_loaded": 2439
}
```

`products_loaded` should be much higher than `0`; any positive value confirms the CSV loaded.

## SQLite Notes

The local `users.db` is intentionally not shipped in Docker. The deployed app creates a fresh SQLite database at `/data/users.db`. It survives redeploys only if the `/data` Railway volume is attached.

Use Postgres later only if you need multi-instance scaling, high traffic, or stronger production reliability.

## OCR Accuracy

The app returns `ocr_quality` for every scan:

- `high`: usable for automated analysis with manual review.
- `medium`: usable, but user should confirm medicine names, quantities, and prices.
- `low` or `failed`: ask for a clearer image/PDF.

A real percentage accuracy needs labeled test bills with expected text. Without that dataset, do not claim an exact OCR percentage.
