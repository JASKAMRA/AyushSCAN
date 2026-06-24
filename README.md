<h1 align="center">📊 AyushScan</h1>

<p align="center"><i>AI-powered medical bill analyzer and health assistant for Bharat</i></p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Flask-WebApp-orange?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Gemini-AI-green?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/OCR-Tesseract-purple?style=for-the-badge"/>
</p>

---

## 🎥 Demo Video

<p align="center">
  <a href="https://youtu.be/pqgdbEKCr8Y" target="_blank">
    <img src="https://img.youtube.com/vi/pqgdbEKCr8Y/0.jpg" alt="AyushScan Demo" width="60%" />
  </a><br>
  <i>Click the image to view the demo (Unlisted)</i>
</p>

---

## 🚀 What is AyushScan?

**AyushScan** is a smart healthcare web app that lets users upload medical bills (images or PDFs), analyze them for overpricing against the Jan Aushadhi/Janaushadhi reference dataset, and get AI-backed guidance on medical queries. Designed especially for India's healthcare needs, it supports English, Hindi, and Hinglish and provides transparent, accessible medical expense tracking.

---

## 🌟 Key Features

| Feature | Description |
|--------|-------------|
| 📄 Bill Scanner | Uploads images or PDFs; extracts text via multi-strategy Tesseract OCR and PDF parsing; flags overpriced medicines against the Janaushadhi reference dataset |
| 🤖 Gemini Bill Analysis | Gemini AI structures bill line items, infers pack sizes, and determines comparison basis (tablet/strip/pack/line total) with confidence scoring |
| 💬 AI Chatbot — Lia | Context-aware Gemini chatbot; answers in English, Hindi, or Hinglish (auto-detected); supports a price-lookup mode against the Jan Aushadhi dataset; remembers recent scan and chat history |
| 🗺️ Nearby Hospitals | Live hospital search via the Overpass API (OpenStreetMap); sorts by distance; optionally filters for Ayushman Bharat–empanelled hospitals |
| 🏥 PM-JAY / Ayushman Bharat | Bill scans automatically generate a Gemini-powered PM-JAY coverage note for the detected treatment |
| 🌐 Multi-language UI | Interface labels switch between English, Hindi, and Hinglish; preference is saved per user |
| 🧾 User Dashboard | Displays scan history, estimated total savings, chat message count, and profile info |
| 🔐 Auth System | Signup/login with Werkzeug password hashing (pbkdf2/scrypt); forgot-password OTP flow with real SMTP email delivery |
| 📧 OTP Email | OTP is sent via Gmail SMTP; falls back to server log if email is not configured |
| 📞 Contact Form | About page includes a contact form that emails submissions to the project address |

---

## ✅ What's Working Now

| Feature | Status |
|--------|--------|
| 🔒 Password Hashing | ✅ Implemented (Werkzeug pbkdf2/scrypt) |
| 🗺️ Live Hospital Search | ✅ Implemented via Overpass API (OpenStreetMap) |
| 🏥 Ayushman Bharat Filter | ✅ Implemented (hospital filter + bill PM-JAY note) |
| 📧 OTP via Email | ✅ Implemented (Gmail SMTP) |
| 🤖 AI Bill Structuring | ✅ Gemini extracts line items from OCR text |
| 📄 PDF Bill Support | ✅ Text-layer extraction + OCR via pypdfium2 |
| 🌐 Multi-language Support | ✅ English / Hindi / Hinglish |
| 💬 Context-aware Chatbot | ✅ Uses recent scan history and chat history |

---

## 🚧 Room for Improvement

| Planned Feature | Current Status |
|----------------|----------------|
| 🎤 Voice Chat in Chatbot | Planned for future |
| 🗺️ Official Ayushman Bharat Hospital List | Currently inferred from OpenStreetMap tags; official empanelment data not integrated |
| 🔁 OTP Expiry / Rate Limiting | OTPs are session-scoped but not time-expired; rate limiting not yet added |
| 📱 Mobile-optimised UI | Functional on mobile but not fully responsive |

---

## Project Structure

```
AyushSCAN/
├── app.py                  # Main Flask app — routes, OCR, bill analysis, chatbot, auth
├── products.csv            # Janaushadhi reference dataset
├── requirements.txt
├── .env                    # Environment variables (not committed)
├── migrations/             # SQL migration scripts
├── static/
│   ├── images/
│   ├── scripts/            # JS for dashboard, login, signup
│   └── styles/             # CSS per page
└── templates/              # Jinja2 HTML templates
```

---

## 👤 Developers

→ Akshita Sachdeva

→ Jas Kamra

---

## 🛠️ How to Run Locally

```bash
# Clone the repository
git clone https://github.com/JASKAMRA/AyushSCAN
cd AyushSCAN

# (Optional) Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt

# Start the Flask app
python app.py

# Open in browser
http://127.0.0.1:5000
```

> **OCR dependency:** Tesseract must be installed separately.
> - Windows: [https://github.com/tesseract-ocr/tesseract/releases](https://github.com/tesseract-ocr/tesseract/releases)
> - Ubuntu: `sudo apt install tesseract-ocr`
>
> The app defaults to `C:\Program Files\Tesseract-OCR\tesseract.exe` on Windows. Override with `TESSERACT_CMD` in `.env`.

---

## 🔐 Environment Variables (`.env`)

Create a `.env` file at the project root (same level as `app.py`).

```env
# Required for AI chatbot, bill structure extraction, and PM-JAY notes
GOOGLE_API_KEY=your_gemini_api_key_here

# Required for OTP email and contact form
EMAIL_ADDRESS=your_gmail_address@gmail.com
EMAIL_PASSWORD=your_gmail_app_password

# Optional overrides
SECRET_KEY=change-this-in-production
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
TESSERACT_LANG=eng
GEMINI_MODEL=models/gemini-1.5-flash-latest
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
PDF_OCR_MAX_PAGES=12
PDF_OCR_SCALE=3.5
```

- Get your **Gemini API key** from [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)
- For Gmail, use an **App Password** (not your account password): [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
- The app works without `GOOGLE_API_KEY` — bill scanning and price lookup still function, but Gemini-powered features fall back gracefully.

### ⚠️ Important Notes

- Your `.env` file is excluded from version control via `.gitignore`.
- **Never upload `.env` to GitHub** — keep your keys safe.

---
