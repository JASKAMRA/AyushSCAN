import csv
import io
import json
import logging
import os
import random
import re
import smtplib
import sqlite3
import ssl
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, Response, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import pypdfium2 as pdfium
except ImportError:
    pdfium = None

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError
except ImportError:
    Image = None

    class UnidentifiedImageError(Exception):
        pass

try:
    from rapidfuzz import fuzz
except ImportError:
    from difflib import SequenceMatcher

    class _FuzzFallback:
        @staticmethod
        def token_set_ratio(a, b):
            return int(SequenceMatcher(None, a, b).ratio() * 100)

        @staticmethod
        def partial_ratio(a, b):
            return int(SequenceMatcher(None, a, b).ratio() * 100)

        @staticmethod
        def ratio(a, b):
            return int(SequenceMatcher(None, a, b).ratio() * 100)

    fuzz = _FuzzFallback()

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    import easyocr as _easyocr_module
    _easyocr_cache: dict = {}
except ImportError:
    _easyocr_module = None
    _easyocr_cache: dict = {}

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors as _rl_colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    _reportlab_available = True
except ImportError:
    _reportlab_available = False


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "users.db"
CSV_FILE = BASE_DIR / "products.csv"
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

# ── Simple in-process rate limiter ────────────────────────────────────────────
_rate_limit_store: dict = {}

def check_rate_limit(key: str, max_requests: int = 5, window_sec: int = 60) -> bool:
    """Return True if the request is allowed, False if rate-limited."""
    now = time.time()
    hits = [t for t in _rate_limit_store.get(key, []) if now - t < window_sec]
    if len(hits) >= max_requests:
        return False
    _rate_limit_store[key] = hits + [now]
    return True

# ── Allowed upload extensions ─────────────────────────────────────────────────
_ALLOWED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".pdf"})

if genai and os.getenv("GOOGLE_API_KEY"):
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

tesseract_path = os.getenv("TESSERACT_CMD")
if pytesseract and tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
elif pytesseract and os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


TRANSLATIONS = {
    "english": {
        "dashboard": "Dashboard",
        "scanner": "Scanner",
        "profile": "Profile",
        "history": "Scan History",
        "hospitals": "Hospitals Nearby",
        "ai_assistant": "AI Assistant",
        "total_scans": "Total Scans",
        "recent_scans": "Recent Scans",
        "chat_count": "Chat Messages",
        "savings": "Estimated Savings",
        "active": "Active",
        "loading": "Loading...",
    },
    "hindi": {
        "dashboard": "डैशबोर्ड",
        "scanner": "स्कैनर",
        "profile": "प्रोफाइल",
        "history": "स्कैन इतिहास",
        "hospitals": "नज़दीकी अस्पताल",
        "ai_assistant": "एआई सहायक",
        "total_scans": "कुल स्कैन",
        "recent_scans": "हाल के स्कैन",
        "chat_count": "चैट संदेश",
        "savings": "अनुमानित बचत",
        "active": "सक्रिय",
        "loading": "लोड हो रहा है...",
    },
    "hinglish": {
        "dashboard": "Dashboard",
        "scanner": "Scanner",
        "profile": "Profile",
        "history": "Scan History",
        "hospitals": "Nearby Hospitals",
        "ai_assistant": "AI Sahayak",
        "total_scans": "Total Scans",
        "recent_scans": "Recent Scans",
        "chat_count": "Chat Messages",
        "savings": "Estimated Savings",
        "active": "Active",
        "loading": "Loading...",
    },
}

HINGLISH_HINTS = {
    "dawa", "dawai", "bimari", "aspataal", "hospital", "kitna", "hai", "kya",
    "bill", "mahanga", "sasta", "madad", "doctor", "ilaaj", "yojana"
}
AYUSHMAN_HINTS = ("ayushman", "pmjay", "janaushadhi", "government", "govt", "public", "trust")


def get_db_connection():
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def column_exists(conn, table, column):
    return any(row["name"] == column for row in conn.execute(f"PRAGMA table_info({table})"))


def init_db():
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                preferred_language TEXT DEFAULT 'english',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                text TEXT,
                flagged TEXT DEFAULT '{}',
                report TEXT DEFAULT '{}',
                illness TEXT,
                covered TEXT,
                savings REAL DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS otp_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                otp TEXT NOT NULL,
                purpose TEXT DEFAULT 'forgot_password',
                used INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(email, otp, purpose)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                language TEXT DEFAULT 'english',
                mode TEXT DEFAULT 'gemini',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        migrations = {
            "users": {
                "preferred_language": "ALTER TABLE users ADD COLUMN preferred_language TEXT DEFAULT 'english'",
                "created_at": "ALTER TABLE users ADD COLUMN created_at DATETIME",
                "state": "ALTER TABLE users ADD COLUMN state TEXT",
                "caste_category": "ALTER TABLE users ADD COLUMN caste_category TEXT DEFAULT 'general'",
                "annual_income": "ALTER TABLE users ADD COLUMN annual_income TEXT DEFAULT 'not_specified'",
            },
            "scans": {
                "illness": "ALTER TABLE scans ADD COLUMN illness TEXT",
                "covered": "ALTER TABLE scans ADD COLUMN covered TEXT",
                "report": "ALTER TABLE scans ADD COLUMN report TEXT DEFAULT '{}'",
                "savings": "ALTER TABLE scans ADD COLUMN savings REAL DEFAULT 0",
            },
            "otp_tokens": {
                "purpose": "ALTER TABLE otp_tokens ADD COLUMN purpose TEXT DEFAULT 'forgot_password'",
                "used": "ALTER TABLE otp_tokens ADD COLUMN used INTEGER DEFAULT 0",
            },
        }
        for table, columns in migrations.items():
            for column, statement in columns.items():
                if not column_exists(conn, table, column):
                    conn.execute(statement)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_user_timestamp ON scans(user_id, timestamp DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_user_timestamp ON chat_history(user_id, timestamp DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_otp_email_purpose ON otp_tokens(email, purpose, used)")
        conn.commit()


def t(key):
    language = session.get("language", "english")
    return TRANSLATIONS.get(language, TRANSLATIONS["english"]).get(key, key)


@app.context_processor
def inject_language():
    return {
        "lang": session.get("language", "english"),
        "tr": TRANSLATIONS.get(session.get("language", "english"), TRANSLATIONS["english"]),
        "t": t,
    }


def detect_language(text: str) -> str:
    """Detect message language; respects the user's stored preference for roman-script input."""
    if re.search(r"[\u0900-\u097F]", text or ""):
        return "hindi"
    preferred = session.get("language", "english")
    words = set(re.findall(r"[a-zA-Z]+", (text or "").lower()))
    if words & HINGLISH_HINTS:
        return "hinglish"
    # If the user has chosen Hindi/Hinglish, keep it \u2014 they may type in Roman script.
    if preferred in ("hindi", "hinglish") and words:
        return preferred
    return preferred if preferred in TRANSLATIONS else "english"


def translate_reply(text, language):
    if language == "hindi":
        return text
    if language == "hinglish":
        return text.replace("medicine", "dawai").replace("hospital", "hospital").replace("bill", "bill")
    return text


def preprocess(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s./-]", " ", text)
    for word in ["ip", "bp", "usp", "tablet", "tablets", "tab", "capsule", "capsules", "cap", "syrup", "injection"]:
        text = re.sub(rf"\b{word}\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_mg(text):
    match = re.search(r"(\d+(?:\.\d+)?)\s*mg", (text or "").lower())
    return float(match.group(1)) if match else None


def extract_dosage_form(text):
    match = re.search(
        r"\b(tablets?|capsules?|injections?|suspensions?|syrups?|creams?|gels?|ointments?|drops?|vials?)\b",
        (text or "").lower(),
    )
    if not match:
        return ""
    form = match.group(1)
    return {
        "tablet": "tablets", "capsule": "capsules", "injection": "injections",
        "suspension": "suspensions", "syrup": "syrups", "cream": "creams",
        "gel": "gels", "ointment": "ointments", "drop": "drops", "vial": "vials",
    }.get(form, form)


def extract_primary_name(text):
    without_item_number = re.sub(r"^\s*\d+[.)-]?\s+", "", text or "")
    match = re.search(r"[a-zA-Z][a-zA-Z-]{2,}", without_item_number)
    return match.group(0).lower() if match else ""


def extract_price_info(line):
    rupee_values = re.findall(r"(?:rs\.?|inr|₹)\s*(\d+(?:\.\d{1,2})?)", line, flags=re.I)
    if rupee_values:
        return float(rupee_values[-1]), "detected_price"

    amount_match = re.search(r"(\d+(?:\.\d{1,2})?)\s*$", line or "")
    if not amount_match:
        return None, "not_found"

    amount = float(amount_match.group(1))
    prefix = line[:amount_match.start()].rstrip()
    quantity_match = re.search(r"(?:^|\s)(\d{1,3})\s*$", prefix)
    if quantity_match:
        quantity = int(quantity_match.group(1))
        if 0 < quantity <= 100:
            return round(amount / quantity, 2), "calculated_unit_price"
    return amount, "detected_price"


def extract_billing_info(line):
    text = line or ""
    explicit_quantity = re.search(r"\bqty\.?\s*[:=-]?\s*(\d{1,3})\b", text, flags=re.I)

    # Remove strengths and pack sizes before looking for quantity and total.
    pricing_text = re.sub(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|kg|ml|l|iu|units?)\b", " ", text, flags=re.I)
    pricing_text = re.sub(r"\b\d+\s*['’]s\b", " ", pricing_text, flags=re.I)
    pricing_text = re.sub(r"^\s*\d+[.)-]\s*", "", pricing_text)

    numeric_matches = list(re.finditer(r"(?<![\d.])(\d+(?:\.\d{1,2})?)(?![\d.])", pricing_text))
    if not numeric_matches:
        return None, "not_found", 1, None

    total_match = numeric_matches[-1]
    line_total = float(total_match.group(1))
    quantity = int(explicit_quantity.group(1)) if explicit_quantity else 1

    if not explicit_quantity:
        before_total = pricing_text[:total_match.start()]
        standalone_integers = re.findall(r"(?<![\d.])(\d{1,3})(?![\d.])", before_total)
        if standalone_integers:
            candidate_quantity = int(standalone_integers[0])
            if 0 < candidate_quantity <= 100:
                quantity = candidate_quantity

    unit_price = round(line_total / quantity, 2) if quantity > 1 else line_total
    price_type = "calculated_unit_price" if quantity > 1 else "detected_price"
    return unit_price, price_type, quantity, line_total


def is_price_continuation_line(line):
    cleaned = re.sub(r"\b(?:qty|quantity|rs|inr|amount|total|price|rate)\b", " ", line or "", flags=re.I)
    cleaned = re.sub(r"[\d\s.,:₹â‚¹xX*=-]", "", cleaned)
    return not cleaned.strip() and bool(re.search(r"\d", line or ""))


def load_products():
    products = []
    if not CSV_FILE.exists():
        return products
    with open(CSV_FILE, newline="", encoding="utf-8") as csvfile:
        for row in csv.DictReader(csvfile):
            try:
                mrp = float(row.get("MRP", 0) or 0)
            except ValueError:
                mrp = 0
            generic = row.get("Generic Name", "").strip()
            brand = row.get("Brand Name", "").strip()
            category = row.get("Category") or row.get("Group Name", "")
            avg = row.get("Average Price") or row.get("Avg Price") or mrp
            market = row.get("Market Price") or row.get("MRP") or mrp
            products.append({
                "generic": generic,
                "brand": brand,
                "category": category,
                "unit": row.get("Unit Size", ""),
                "mrp": mrp,
                "average_price": float(avg or mrp),
                "market_price": float(market or mrp),
                "search": preprocess(" ".join([generic, brand, category, row.get("Unit Size", "")])),
                "name_search": preprocess(" ".join([generic, brand])),
                "primary_name": extract_primary_name(generic),
                "dosage_form": extract_dosage_form(generic),
                "is_combination": bool(re.search(r"\s(?:and|\+)\s|,", generic, flags=re.I)),
                "mg": extract_mg(generic),
            })
    return products


PRODUCTS = load_products()

# ── Phase 5: bill-entry category keywords ────────────────────────────────────
_CATEGORY_KEYWORDS = {
    "lab_test": {
        "cbc", "hemogram", "lft", "kft", "rft", "urine", "culture", "biopsy",
        "ecg", "eeg", "mri", "ct scan", "x-ray", "xray", "ultrasound", "usg",
        "blood test", "pathology", "lab", "serum", "thyroid", "tsh", "hba1c",
        "glucose", "cholesterol", "lipid", "creatinine", "bilirubin", "albumin",
        "haemoglobin", "hemoglobin", "platelet", "wbc", "rbc",
    },
    "consultation": {
        "consultation", "consulting", "opd charges", "ipd charges", "visit fee",
        "doctor fee", "physician fee", "specialist fee", "outpatient",
        "professional fee",
    },
    "room_charge": {
        "room rent", "bed charges", "ward charges", "icu charges", "nicu charges",
        "cabin charges", "nursing charges", "accommodation", "daily charges",
    },
    "procedure": {
        "surgery", "operation", "procedure", "dressing", "suture", "stitching",
        "physiotherapy", "therapy session", "dialysis", "endoscopy", "catheter",
        "iv administration", "nebulisation", "nebulization", "vaccination",
    },
    "gst": {"gst", "cgst", "sgst", "igst", "service tax"},
}


def categorize_entry_rule_based(text):
    text_lower = (text or "").lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return "medicine"


def find_best_product(line):
    stripped_line = preprocess_for_matching(line)
    line_mg = extract_mg(line)
    line_primary = extract_primary_name(line)
    line_form = extract_dosage_form(line)
    line_is_combination = bool(re.search(r"\s(?:and|\+)\s|,", line, flags=re.I))
    best_product = None
    best_score = 0
    for product in PRODUCTS:
        primary_score = fuzz.ratio(line_primary, product["primary_name"]) if line_primary else 0
        if line_primary and primary_score < 72:
            continue
        if line_mg and product["mg"] and abs(line_mg - product["mg"]) > 0.01:
            continue
        if line_form and product["dosage_form"] and line_form != product["dosage_form"]:
            continue
        token_score = fuzz.token_set_ratio(stripped_line, product["name_search"])
        ratio_score = fuzz.ratio(stripped_line, product["name_search"])
        score = (token_score * 0.45) + (ratio_score * 0.35) + (primary_score * 0.20)
        if product["is_combination"] and not line_is_combination:
            score -= 25
        if score > best_score:
            best_score = score
            best_product = product
    return (best_product, best_score) if best_score >= 62 else (None, best_score)


def find_medicine_price(query):
    product, score = find_best_product(query)
    if not product:
        return None
    return (
        f"{product['generic']} ({product['unit']}) is listed at Rs {product['mrp']:.2f} "
        f"in the Janaushadhi dataset. Category: {product['category'] or 'N/A'}."
    )


def fallback_chat_response(message, language="english", mode="gemini"):
    text = (message or "").lower()
    if mode == "price":
        return translate_reply("I could not find an exact medicine match. Try the generic name with strength, for example Paracetamol 500 mg.", language)
    if "ayushman" in text or "pmjay" in text:
        return "Ayushman Bharat PM-JAY coverage depends on the hospital empanelment and treatment package. Use the hospital filter to find likely empanelled hospitals nearby."
    if "bill" in text or "price" in text or "mrp" in text:
        return "Upload the bill in the scanner to compare detected prices with the Janaushadhi reference price. I can also explain individual charges here."
    if language == "hindi":
        return "मैं अभी सीमित मोड में जवाब दे रहा हूं। दवा, बिल, अस्पताल या आयुष्मान भारत से जुड़ा सवाल पूछें।"
    if language == "hinglish":
        return "Main abhi fallback mode me hoon. Aap dawa, bill, hospital ya Ayushman Bharat ke baare me pooch sakte hain."
    return "I am running in fallback mode right now. Ask about a medicine price, bill charge, hospital search, or Ayushman Bharat coverage."


def get_user_scan_context(user_id, limit=5):
    context_lines = []
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, flagged, report, illness, covered, savings, timestamp
            FROM scans
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        history = conn.execute(
            """
            SELECT user_message, bot_response
            FROM chat_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 6
            """,
            (user_id,),
        ).fetchall()
    for row in rows:
        try:
            flagged = json.loads(row["flagged"] or "{}")
        except json.JSONDecodeError:
            flagged = {}
        try:
            report = json.loads(row["report"] or "{}")
        except json.JSONDecodeError:
            report = {}
        if flagged:
            flagged_summary = "; ".join(
                f"{name}: overpaid Rs {data.get('extra', 0)} ({data.get('comparison_basis', 'unknown')} basis)"
                for name, data in list(flagged.items())[:5]
            )
            context_lines.append(f"Scan {row['id']} flagged items: {flagged_summary}")
        items = report.get("detected_items", [])[:5]
        if items:
            item_summary = "; ".join(
                f"{item.get('name')}: qty {item.get('quantity')}, paid {item.get('billed_display', item.get('line_total'))}"
                for item in items
            )
            context_lines.append(f"Scan {row['id']} detected medicines: {item_summary}")
        if row["illness"]:
            context_lines.append(f"Scan {row['id']} treatment context: {row['illness'][:200]}")
        if row["covered"]:
            context_lines.append(f"Scan {row['id']} PM-JAY note: {row['covered'][:200]}")
    chat_context = []
    for item in reversed(history):
        chat_context.append(f"User: {item['user_message'][:300]}")
        chat_context.append(f"Assistant: {item['bot_response'][:400]}")
    return {
        "scan_context": "\n".join(context_lines[:12]),
        "chat_context": "\n".join(chat_context[-8:]),
    }


def extract_gemini_text(response):
    if not response:
        return ""
    text = getattr(response, "text", None)
    if text:
        return text.strip()
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) if content else None
        if not parts:
            continue
        chunks = [getattr(part, "text", "") for part in parts if getattr(part, "text", None)]
        if chunks:
            return "\n".join(chunks).strip()
    return ""


_LANGUAGE_INSTRUCTIONS = {
    "english": (
        "CRITICAL RULE: Respond ONLY in clear, simple English. "
        "Do NOT use Hindi, Devanagari script, or Hinglish under any circumstances."
    ),
    "hindi": (
        "महत्वपूर्ण निर्देश: आपको पूरी तरह हिंदी में जवाब देना है। "
        "अंग्रेजी में जवाब देना सख्त मना है — यह नियम हर परिस्थिति में लागू होता है। "
        "केवल दवाओं के नाम और चिकित्सा शब्दों (जैसे Paracetamol, MRI) के लिए अंग्रेजी स्वीकार्य है। "
        "सरल और स्पष्ट हिंदी में जवाब दें। "
        "उदाहरण: 'आपकी दवाइयों की कीमत जन औषधि की तुलना में अधिक है।'"
    ),
    "hinglish": (
        "CRITICAL RULE: Respond ONLY in Hinglish — Roman/Latin script only (absolutely NO Devanagari). "
        "Use Hindi grammar structure with English technical words mixed in naturally. "
        "Do NOT reply in pure English. Do NOT use Devanagari script. "
        "Write like a young urban Indian would text: casual, clear, helpful. "
        "Example: 'Aapka bill thoda zyada lag raha hai — Jan Aushadhi reference se compare karte hain.'"
    ),
}


def ask_gemini(message: str, language: str, user_id: int = None) -> str:
    instruction = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["english"])
    context_block = ""
    if user_id:
        context = get_user_scan_context(user_id)
        if context["scan_context"]:
            context_block += f"\nRecent scan analysis for this user:\n{context['scan_context']}\n"
        if context["chat_context"]:
            context_block += f"\nRecent chat history:\n{context['chat_context']}\n"
    prompt = (
        f"{instruction}\n\n"
        "You are Lia, AyushScan's careful medical billing assistant. "
        "Do not diagnose. Explain bills, medicine pricing, Jan Aushadhi comparisons, "
        "PM-JAY/Ayushman Bharat coverage, OCR scan results, and healthcare navigation safely. "
        "If the user asks why a medicine was flagged, use the scan context when available. "
        "Do not invent scan results that are not in the context. "
        "If the user asks about a medicine price, refer to the Janaushadhi dataset. "
        "If you cannot find a match, say so and suggest the user try the generic name with strength. "
        "Do not reference scan numbers in your response. "
        f"{context_block}"
        f"\nUser: {message}\n\n"
        f"REMINDER — {instruction}"
    )
    # Lower temperature = more deterministic language compliance
    temperature = 0.1 if language in ("hindi", "hinglish") else 0.4
    gen_cfg = {"temperature": temperature, "max_output_tokens": 700}
    response = _gemini_generate_with_fallback(prompt, generation_config=gen_cfg)
    reply = extract_gemini_text(response)
    if not reply:
        raise RuntimeError("Gemini returned an empty response")
    return reply


def save_chat(user_id, message, reply, language, mode):
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO chat_history (user_id, user_message, bot_response, language, mode) VALUES (?, ?, ?, ?, ?)",
            (user_id, message, reply, language, mode),
        )
        conn.commit()


def is_password_valid(stored, candidate):
    if not stored:
        return False
    if stored.startswith(("pbkdf2:", "scrypt:")):
        return check_password_hash(stored, candidate)
    return stored == candidate


def upgrade_password_if_plaintext(conn, user_id, stored, candidate):
    if stored and not stored.startswith(("pbkdf2:", "scrypt:")) and stored == candidate:
        conn.execute("UPDATE users SET password = ? WHERE id = ?", (generate_password_hash(candidate), user_id))
        conn.commit()


def send_otp_email(email, otp, purpose="forgot_password"):
    sender = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    if not sender or not password:
        app.logger.warning("SMTP is not configured. OTP for %s is %s", email, otp)
        return False, "Email is not configured. OTP has been logged for local demo."

    msg = EmailMessage()
    msg["Subject"] = "Your AyushScan OTP"
    msg["From"] = sender
    msg["To"] = email
    msg.set_content(f"Your AyushScan OTP for {purpose.replace('_', ' ')} is {otp}. It is valid for this session.")

    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "465"))
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=20) as smtp:
            smtp.login(sender, password)
            smtp.send_message(msg)
        return True, "OTP sent to your email."
    except Exception as exc:
        app.logger.exception("OTP email failed")
        return False, f"Could not send OTP email: {exc}"


def clean_ocr_text(text):
    text = (text or "").replace("\x0c", " ")
    text = text.replace("₹", " Rs ").replace("â‚¹", " Rs ")
    text = text.replace("|", " ").replace("¦", " ")
    # Strip dot/dash leaders used in Indian bills: "Medicine .......... Rs 120" or "Medicine -------- 120"
    text = re.sub(r"[.\-_]{3,}", " ", text)
    text = re.sub(r"[^\S\r\n]+", " ", text)
    text = re.sub(r"\s*([,:;])\s*", r" \1 ", text)
    return "\n".join(normalize_ocr_line(line.strip()) for line in text.splitlines() if line.strip())


def normalize_ocr_line(line):
    line = re.sub(r"^[^a-zA-Z0-9]+", "", line or "")
    digit_map = str.maketrans({
        "O": "0", "o": "0", "E": "0", "e": "0", "@": "0",
        "I": "1", "i": "1", "l": "1", "S": "5", "s": "5",
        "B": "8", "b": "8",
    })

    def fix_strength(match):
        raw_number = match.group(1).translate(digit_map)
        unit = match.group(2).lower().replace("n", "m")
        return f"{raw_number}{unit}"

    return re.sub(
        r"\b([0-9OoEe@IlisSBb]{1,6})\s*(mg|ng|ml|mcg)\b",
        fix_strength,
        line,
        flags=re.I,
    )


def strip_trailing_numeric_columns(text):
    tokens = (text or "").split()
    while tokens:
        token = tokens[-1].lower().rstrip(".,")
        if re.fullmatch(r"(?:rs\.?|inr)?\d+(?:\.\d{1,2})?", token):
            tokens.pop()
            continue
        break
    return " ".join(tokens)


def preprocess_for_matching(text):
    return preprocess(strip_trailing_numeric_columns(text))


def ocr_quality_score(text):
    clean_text = text or ""
    alpha_num = len(re.findall(r"[a-z0-9]", clean_text.lower()))
    digit_count = len(re.findall(r"\d", clean_text))
    lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
    line_count = len(lines)
    receipt_rows = sum(
        1 for line in lines
        if re.search(r"[a-zA-Z]{3,}", line) and re.search(r"(?:rs\.?\s*)?\d+(?:\.\d{1,2})?\s*$", line, re.I)
    )
    fragmented_rows = sum(1 for line in lines if re.fullmatch(r"[\d.,]+", line))
    medicine_hint_count = len(
        re.findall(r"\b(?:tablet|tablets|tab|capsule|capsules|cap|mg|ml|syrup|injection)\b", clean_text.lower())
    )
    return alpha_num + (line_count * 10) + (medicine_hint_count * 20) + (receipt_rows * 60) + digit_count - (fragmented_rows * 20)


def preprocess_image_for_ocr(image, invert=False):
    working = image.convert("L")
    max_side = max(working.size)
    if max_side < 1800:
        scale = max(2, min(4, int(round(1800 / max_side))))
        working = working.resize((working.width * scale, working.height * scale), Image.LANCZOS)
    working = ImageOps.autocontrast(working)
    if invert:
        working = ImageOps.invert(working)
    working = working.filter(ImageFilter.SHARPEN)
    working = ImageEnhance.Contrast(working).enhance(1.8)
    working = ImageEnhance.Sharpness(working).enhance(1.4)
    return working


def threshold_image(image, invert=False, level=175):
    working = image.convert("L")
    if invert:
        working = ImageOps.invert(working)
    return working.point(lambda px: 255 if px >= level else 0)


def preprocess_image_for_print(image):
    """Light, clean preprocessing for printed/typed documents (receipts, bills, typed reports)."""
    if Image is None:
        return image
    working = image.convert("L")
    max_side = max(working.size)
    if max_side < 2000:
        scale = max(1.5, 2000 / max_side)
        working = working.resize(
            (int(working.width * scale), int(working.height * scale)), Image.LANCZOS
        )
    working = ImageOps.autocontrast(working, cutoff=1)
    working = ImageEnhance.Contrast(working).enhance(1.5)
    working = ImageEnhance.Sharpness(working).enhance(1.2)
    return working


def preprocess_image_for_handwriting(image):
    """Stronger preprocessing tuned for handwritten text."""
    if Image is None:
        return image
    working = image.convert("L")
    max_side = max(working.size)
    if max_side < 2200:
        scale = max(2, int(2200 / max_side))
        working = working.resize((working.width * scale, working.height * scale), Image.LANCZOS)
    working = ImageOps.autocontrast(working, cutoff=3)
    working = ImageEnhance.Contrast(working).enhance(2.8)
    working = ImageEnhance.Sharpness(working).enhance(2.2)
    working = working.filter(ImageFilter.EDGE_ENHANCE_MORE)
    return working


def deskew_image(image):
    if pytesseract is None or Image is None:
        return image
    try:
        osd = pytesseract.image_to_osd(image, config="--psm 0 -c min_characters_to_try=5")
        angle_match = re.search(r"Rotate:\s*(\d+)", osd)
        if angle_match:
            angle = int(angle_match.group(1))
            if angle in (90, 180, 270):
                return image.rotate(-angle, expand=True)
    except Exception:
        pass
    return image


def _ocr_with_easyocr(image):
    if _easyocr_module is None or Image is None:
        return ""
    try:
        import numpy as np
        key = ("en",)
        if key not in _easyocr_cache:
            _easyocr_cache[key] = _easyocr_module.Reader(list(key), gpu=False, verbose=False)
        reader = _easyocr_cache[key]
        np_image = np.array(image.convert("RGB"))
        results = reader.readtext(np_image, detail=0, paragraph=False)
        return clean_ocr_text("\n".join(str(r) for r in results))
    except Exception as exc:
        app.logger.warning("EasyOCR failed: %s", exc)
        return ""


def ocr_image_to_text(image):
    if Image is None:
        return ""

    lang = os.getenv("TESSERACT_LANG", "eng")
    candidates = []

    if pytesseract is not None:
        # ── Fast path: printed/typed document (receipts, computer-generated bills) ──
        print_img = preprocess_image_for_print(image)
        fast_configs = [
            f"--oem 3 --psm 6 -l {lang}",   # uniform text block
            f"--oem 3 --psm 4 -l {lang}",   # single column with varying text sizes
            f"--oem 3 --psm 3 -l {lang}",   # fully automatic (best for unknown layouts)
            f"--oem 1 --psm 6 -l {lang}",   # LSTM only
        ]
        for config in fast_configs:
            try:
                text = pytesseract.image_to_string(print_img, config=config)
            except Exception:
                continue
            cleaned = clean_ocr_text(text)
            if cleaned:
                candidates.append(cleaned)

        # If the fast path already gives a good result, skip the expensive pipeline
        fast_best = max(candidates, key=ocr_quality_score) if candidates else ""
        if ocr_quality_score(fast_best) > 120:
            # Also try the raw image in case preprocessing hurt (dark backgrounds etc.)
            for config in fast_configs[:2]:
                try:
                    text = pytesseract.image_to_string(image, config=config)
                except Exception:
                    continue
                cleaned = clean_ocr_text(text)
                if cleaned:
                    candidates.append(cleaned)
            if _easyocr_module is not None:
                easy = _ocr_with_easyocr(image)
                if easy:
                    candidates.append(easy)
            return max(candidates, key=ocr_quality_score)

        # ── Full pipeline: low-quality scan, photo, or handwritten document ─────────
        base     = preprocess_image_for_ocr(image, invert=False)
        hw       = preprocess_image_for_handwriting(image)
        deskewed = deskew_image(image)

        variants = [
            print_img,
            base,
            threshold_image(base, invert=False, level=175),
            threshold_image(base, invert=True,  level=175),
            image,
            hw,
            threshold_image(hw, invert=False, level=160),
        ]
        mean_brightness = ImageStat.Stat(base).mean[0]
        if mean_brightness < 140:
            variants.append(preprocess_image_for_ocr(image, invert=True))
        else:
            variants.append(ImageOps.invert(base))

        if deskewed is not image:
            deskew_base = preprocess_image_for_ocr(deskewed, invert=False)
            variants.extend([
                preprocess_image_for_print(deskewed),
                deskew_base,
                threshold_image(deskew_base, invert=False, level=175),
            ])

        configs = [
            f"--oem 3 --psm 6 -l {lang}",
            f"--oem 3 --psm 4 -l {lang}",
            f"--oem 3 --psm 3 -l {lang}",
            f"--oem 3 --psm 11 -l {lang}",
            f"--oem 1 --psm 6 -l {lang}",
            f"--oem 1 --psm 4 -l {lang}",
        ]

        for prepared in variants:
            for config in configs:
                try:
                    text = pytesseract.image_to_string(prepared, config=config)
                except Exception:
                    continue
                cleaned = clean_ocr_text(text)
                if cleaned:
                    candidates.append(cleaned)

    # ── EasyOCR always runs — handles handwriting and low-quality photos well ──
    if _easyocr_module is not None:
        easy = _ocr_with_easyocr(image)
        if easy:
            candidates.append(easy)

    if not candidates:
        return ""

    return max(candidates, key=ocr_quality_score)


def extract_pdf_text(file_path):
    extracted_text = ""
    if PdfReader is not None:
        try:
            reader = PdfReader(str(file_path))
            extracted_pages = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    extracted_pages.append(page_text)
            extracted_text = clean_ocr_text("\n".join(extracted_pages))
            if len(re.findall(r"[a-zA-Z]{3,}", extracted_text)) >= 3:
                return extracted_text, "pdf_text"
        except Exception as exc:
            app.logger.warning("PDF text extraction failed: %s", exc)

    if pdfium is not None and pytesseract is not None and Image is not None:
        try:
            document = pdfium.PdfDocument(str(file_path))
            page_texts = []
            max_pages = min(len(document), int(os.getenv("PDF_OCR_MAX_PAGES", "12")))
            render_scale = float(os.getenv("PDF_OCR_SCALE", "3.5"))
            for page_index in range(max_pages):
                page = document[page_index]
                bitmap = page.render(scale=render_scale, rotation=0)
                page_image = bitmap.to_pil()
                page_text = ocr_image_to_text(page_image)
                if page_text.strip():
                    page_texts.append(page_text)
                bitmap.close()
                page.close()
            document.close()
            rendered_text = clean_ocr_text("\n".join(page_texts))
            if rendered_text:
                return rendered_text, "pdf_ocr"
        except Exception as exc:
            app.logger.warning("PDFium rendering/OCR failed: %s", exc)

    # This fallback handles simple scan PDFs that contain a full-page image.
    if PdfReader is not None and pytesseract is not None and Image is not None:
        try:
            reader = PdfReader(str(file_path))
            image_texts = []
            for page in reader.pages[:int(os.getenv("PDF_OCR_MAX_PAGES", "12"))]:
                ranked_images = []
                for image_file in page.images:
                    pil_image = image_file.image
                    ranked_images.append((pil_image.width * pil_image.height, pil_image))
                for _, pil_image in sorted(ranked_images, key=lambda item: item[0], reverse=True)[:2]:
                    image_text = ocr_image_to_text(pil_image)
                    if image_text.strip():
                        image_texts.append(image_text)
            embedded_text = clean_ocr_text("\n".join(image_texts))
            if embedded_text:
                return embedded_text, "pdf_embedded_image_ocr"
        except Exception as exc:
            app.logger.warning("Embedded PDF image OCR failed: %s", exc)
    return "", "unavailable"


ALLOWED_COMPARISON_BASES = frozenset({"tablet", "strip", "pack", "line_total", "unknown"})
STRUCTURE_CONFIDENCE_THRESHOLD = 0.55
LOW_CONFIDENCE_THRESHOLD = 0.50   # was 0.6 — rule-based results were unfairly "low"
HIGH_CONFIDENCE_THRESHOLD = 0.75


_GEMINI_FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-flash-latest",
]


def get_gemini_model(model_name=None):
    if genai is None:
        raise RuntimeError("google-generativeai is not installed")
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY is not configured")
    name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    return genai.GenerativeModel(name)


def _gemini_generate_with_fallback(prompt, generation_config=None):
    """Try the configured model, cascade through fallbacks on quota/timeout errors."""
    primary = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    models_to_try = [primary] + [m for m in _GEMINI_FALLBACK_MODELS if m != primary]
    last_exc = None
    for attempt, model_name in enumerate(models_to_try):
        try:
            model = get_gemini_model(model_name)
            kwargs: dict = {}
            if generation_config:
                kwargs["generation_config"] = generation_config
            try:
                return model.generate_content(prompt, request_options={"timeout": 28}, **kwargs)
            except TypeError:
                return model.generate_content(prompt, **kwargs)
        except Exception as exc:
            last_exc = exc
            err = str(exc).lower()
            is_quota = any(k in err for k in ("429", "quota", "rate limit", "resource_exhausted"))
            is_timeout = any(k in err for k in ("timeout", "deadline exceeded", "timed out"))
            if is_quota:
                wait = min(2 ** attempt, 10)
                app.logger.warning("Quota on %s (attempt %d), backing off %ds. %s", model_name, attempt + 1, wait, exc)
                time.sleep(wait)
                continue
            if is_timeout:
                app.logger.warning("Timeout on %s, trying next model.", model_name)
                time.sleep(1)
                continue
            raise
    raise last_exc


def gemini_generate_json(prompt):
    generation_config = {"response_mime_type": "application/json"}
    response = _gemini_generate_with_fallback(prompt, generation_config=generation_config)
    if not response or not getattr(response, "text", None):
        return None
    return response.text.strip()


def parse_json_payload(text):
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"[\[{][\s\S]*[\]}]", cleaned)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def confidence_tier(confidence):
    if confidence is None:
        return "low"
    try:
        value = float(confidence)
    except (TypeError, ValueError):
        return "low"
    if value >= HIGH_CONFIDENCE_THRESHOLD:
        return "high"
    if value >= LOW_CONFIDENCE_THRESHOLD:
        return "medium"
    return "low"


def parse_csv_pack_size(unit_text):
    match = re.search(r"(\d+)", unit_text or "")
    return max(int(match.group(1)), 1) if match else 1


PACK_SIZE_BILL_PATTERNS = [
    (re.compile(r"strip\s+of\s+(\d+)", re.I), 1),
    (re.compile(r"pack\s+of\s+(\d+)", re.I), 1),
    (re.compile(r"\b(\d+)\s*x\s*(\d+)\b", re.I), 2),
    (re.compile(r"\(\s*(\d+)\s*(?:tablets?|tabs?|capsules?|caps?)\s*\)", re.I), 1),
    (re.compile(r"\b(\d+)\s*(?:tablets?|tabs?|capsules?|caps?)\b", re.I), 1),
]


def extract_pack_size(text):
    for pattern, group_index in PACK_SIZE_BILL_PATTERNS:
        match = pattern.search(text or "")
        if not match:
            continue
        try:
            size = int(match.group(group_index))
        except (TypeError, ValueError):
            continue
        if 1 <= size <= 1000:
            return {"pack_size": size, "source": "bill"}
    return {"pack_size": None, "source": "unknown"}


def gemini_infer_pack_size(bill_line, medicine_name, csv_pack_size):
    if genai is None or not os.getenv("GOOGLE_API_KEY"):
        return None
    try:
        prompt = f"""Infer the medicine pack size (number of tablets/capsules per strip or pack) from this bill line.
DO NOT calculate prices or totals.
Return ONLY valid JSON:
{{"pack_size": 10, "confidence": 0.85, "reasoning": "brief reason"}}

Use null for pack_size if unknown.
Bill line: {bill_line}
Medicine: {medicine_name}
Reference CSV pack size (fallback only): {csv_pack_size}
"""
        raw = gemini_generate_json(prompt)
        payload = parse_json_payload(raw)
        if not isinstance(payload, dict):
            return None
        pack_size = payload.get("pack_size")
        if pack_size is None:
            return None
        pack_size = int(pack_size)
        if not 1 <= pack_size <= 1000:
            return None
        return {
            "pack_size": pack_size,
            "source": "gemini",
            "confidence": max(0.0, min(float(payload.get("confidence", 0.7)), 1.0)),
            "reasoning": str(payload.get("reasoning", "")).strip(),
        }
    except Exception as exc:
        app.logger.warning("Gemini pack size inference unavailable: %s", exc)
        return None


def resolve_pack_size(bill_line, product):
    bill_pack = extract_pack_size(bill_line)
    if bill_pack["pack_size"]:
        return bill_pack
    csv_pack = parse_csv_pack_size(product.get("unit", ""))
    gemini_pack = gemini_infer_pack_size(bill_line, product.get("generic", ""), csv_pack)
    if gemini_pack and gemini_pack.get("pack_size"):
        return gemini_pack
    return {"pack_size": csv_pack, "source": "csv"}


def get_reference_prices(product, pack_info=None):
    csv_pack_size = parse_csv_pack_size(product.get("unit", ""))
    if pack_info and pack_info.get("pack_size"):
        bill_pack_size = int(pack_info["pack_size"])
        pack_source = pack_info.get("source", "csv")
    else:
        bill_pack_size = csv_pack_size
        pack_source = "csv"
    csv_mrp = float(product.get("mrp") or 0)
    per_tablet = round(csv_mrp / csv_pack_size, 6) if csv_pack_size else csv_mrp
    normalized_strip = round(per_tablet * bill_pack_size, 4)
    return {
        "csv_pack_size": csv_pack_size,
        "bill_pack_size": bill_pack_size,
        "pack_size": bill_pack_size,
        "pack_size_source": pack_source,
        "unit_label": product.get("unit", ""),
        "csv_mrp": csv_mrp,
        "per_tablet_price": per_tablet,
        "strip_price": normalized_strip,
        "tablet_price": per_tablet,
        "pack_price": normalized_strip,
        "normalized": bill_pack_size != csv_pack_size,
    }


def parse_gemini_json_response(text):
    payload = parse_json_payload(text)
    if not isinstance(payload, dict):
        return None
    basis = str(payload.get("comparison_basis", "")).lower().strip()
    if basis not in ALLOWED_COMPARISON_BASES:
        return None
    try:
        confidence = float(payload.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "comparison_basis": basis,
        "confidence": max(0.0, min(confidence, 1.0)),
        "reasoning": str(payload.get("reasoning", "")).strip(),
    }


def gemini_bill_structure_extraction(ocr_text):
    if genai is None or not os.getenv("GOOGLE_API_KEY"):
        return None
    try:
        prompt = f"""Extract medicine line items from this medical bill OCR text.
DO NOT calculate totals, savings, percentages, GST, or discounts.
Ignore dates, addresses, hospital names, phone numbers, patient names, and grand totals.
Return ONLY valid JSON:
{{
  "items": [
    {{"medicine": "Paracetamol 500mg", "quantity": 2, "amount": 120}}
  ],
  "confidence": 0.89
}}

Rules:
- Include only medicines/drugs with a price
- quantity defaults to 1 if missing
- amount is the line total in rupees
- confidence reflects how complete and reliable the extraction is

OCR Text:
{(ocr_text or "")[:8000]}
"""
        raw = gemini_generate_json(prompt)
        payload = parse_json_payload(raw)
        if not isinstance(payload, dict):
            return None
        items = payload.get("items")
        if not isinstance(items, list):
            return None
        cleaned_items = []
        for item in items:
            if not isinstance(item, dict):
                continue
            medicine = str(item.get("medicine", "")).strip()
            if len(medicine) < 3:
                continue
            try:
                quantity = int(item.get("quantity", 1) or 1)
            except (TypeError, ValueError):
                quantity = 1
            try:
                amount = float(item.get("amount"))
            except (TypeError, ValueError):
                continue
            if amount <= 0:
                continue
            cleaned_items.append({
                "medicine": medicine,
                "quantity": max(1, min(quantity, 1000)),
                "amount": round(amount, 2),
            })
        if not cleaned_items:
            return None
        try:
            confidence = float(payload.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        return {
            "items": cleaned_items,
            "confidence": max(0.0, min(confidence, 1.0)),
        }
    except Exception as exc:
        app.logger.warning("Gemini bill structure extraction unavailable: %s", exc)
        return None


def extract_rule_based_bill_lines(text):
    lines = clean_ocr_text(text).splitlines()
    bill_lines = []
    for index, raw_line in enumerate(lines):
        if not re.search(r"[a-zA-Z]{3,}", raw_line):
            continue
        combined_line = raw_line
        if extract_billing_info(raw_line)[3] is None:
            for next_line in lines[index + 1:index + 3]:
                if not is_price_continuation_line(next_line):
                    break
                combined_line = f"{combined_line} {next_line}"
        bill_lines.append({
            "raw_line": combined_line,
            "source": "rule_based",
            "structure_confidence": 0.55,
        })
    return bill_lines


def fallback_commercial_interpretation(unit_price, line_total, quantity, refs):
    qty = quantity or 1
    unit_price = unit_price if unit_price is not None else (line_total or 0)
    line_total = line_total if line_total is not None else unit_price
    per_unit = round(line_total / qty, 2) if qty > 1 else line_total
    candidates = [
        ("strip", refs["strip_price"], per_unit),
        ("tablet", refs["tablet_price"], round(line_total / qty, 4) if qty else line_total),
        ("pack", refs["pack_price"], per_unit),
        ("line_total", refs["strip_price"] * qty, line_total),
    ]
    best_basis = "strip"
    best_ratio = float("inf")
    for basis, expected, billed in candidates:
        if not expected:
            continue
        ratio = abs(billed - expected) / expected
        if ratio < best_ratio:
            best_ratio = ratio
            best_basis = basis
    return {
        "comparison_basis": best_basis,
        "confidence": 0.60,
        "reasoning": "Rule-based fallback: closest reference price match selected.",
    }


def gemini_commercial_interpretation(bill_line, quantity, line_total, unit_price, product, refs, ocr_text=""):
    fallback = fallback_commercial_interpretation(unit_price, line_total, quantity, refs)
    if genai is None or not os.getenv("GOOGLE_API_KEY"):
        return fallback
    try:
        prompt = f"""You interpret how a medical bill line item should be commercially compared against Jan Aushadhi reference pricing.

DO NOT calculate prices, percentages, savings, totals, or any numeric comparison results.
Return ONLY valid JSON with exactly these keys:
- comparison_basis: one of "tablet", "strip", "pack", "line_total", "unknown"
- confidence: number from 0 to 1
- reasoning: one short sentence explaining the commercial interpretation

Bill Line:
{bill_line}

OCR Context:
{(ocr_text or "")[:2000]}

Extracted Facts:
- Quantity: {quantity}
- Line Total: Rs {line_total}
- Unit Price: Rs {unit_price}

Reference Dataset:
- Medicine: {product['generic']}
- CSV Pack Size: {refs['unit_label']} ({refs['csv_pack_size']} units)
- Bill Pack Size Used: {refs['bill_pack_size']} ({refs['pack_size_source']})
- Jan Aushadhi CSV MRP: Rs {refs['csv_mrp']}
- Normalized Strip Price (for bill pack size): Rs {refs['strip_price']}
- Jan Aushadhi Tablet Price: Rs {refs['tablet_price']}

Choose comparison_basis based on what the billed amount most likely represents.
Use "unknown" only if the commercial unit cannot be determined reliably.
"""
        raw = gemini_generate_json(prompt)
        decision = parse_gemini_json_response(raw)
        if not decision:
            return fallback
        if decision["comparison_basis"] == "unknown":
            fb = fallback_commercial_interpretation(unit_price, line_total, quantity, refs)
            decision["comparison_basis"] = fb["comparison_basis"]
            decision["confidence"] = min(decision.get("confidence", 0.4), fb.get("confidence", 0.45))
            decision["reasoning"] = decision.get("reasoning") or fb.get("reasoning", "")
        return decision
    except Exception as exc:
        app.logger.warning("Gemini commercial interpretation unavailable: %s", exc)
        fallback["reasoning"] = f"AI interpretation unavailable ({exc}); using rule-based fallback."
        return fallback


def compute_commercial_pricing(decision, refs, quantity, line_total, unit_price):
    basis = decision.get("comparison_basis", "strip")
    qty = quantity or 1
    line_total = line_total if line_total is not None else (unit_price or 0)
    unit_price = unit_price if unit_price is not None else line_total
    per_qty_price = round(line_total / qty, 2) if qty > 1 else round(line_total, 2)

    if basis == "tablet":
        expected_price = refs["tablet_price"]
        billed_price = round(line_total / qty, 4) if qty else round(line_total, 4)
        expected_line_total = round(expected_price * qty, 2)
    elif basis == "pack":
        expected_price = refs["pack_price"]
        billed_price = per_qty_price
        expected_line_total = round(expected_price * qty, 2)
    elif basis == "line_total":
        expected_price = round(refs["strip_price"] * qty, 2)
        billed_price = round(line_total, 2)
        expected_line_total = expected_price
    else:
        basis = "strip"
        expected_price = refs["strip_price"]
        billed_price = per_qty_price
        expected_line_total = round(expected_price * qty, 2)

    difference = round(billed_price - expected_price, 2)
    overpricing_percentage = (
        round((difference / expected_price) * 100, 2)
        if expected_price and difference > 0
        else 0
    )
    total_difference = round(line_total - expected_line_total, 2)
    item_confidence = decision.get("confidence")
    tier = confidence_tier(item_confidence)

    return {
        "comparison_basis": basis,
        "ai_confidence": item_confidence,
        "confidence_tier": tier,
        "expected_price": expected_price,
        "billed_price": billed_price,
        "difference": difference,
        "overpricing_percentage": overpricing_percentage,
        "expected_line_total": expected_line_total,
        "total_difference": total_difference,
        "interpretation_reasoning": decision.get("reasoning", ""),
        "low_confidence_disclaimer": (
            "Estimated comparison based on limited bill information."
            if tier == "low"
            else ""
        ),
    }


def _pluralize_unit(unit, count):
    if count == 1:
        return unit
    if unit.endswith("s"):
        return unit
    return f"{unit}s"


def build_result_display_labels(quantity, comparison_basis, refs, line_total, pricing):
    qty = quantity or 1
    basis = comparison_basis or "strip"
    unit_names = {
        "tablet": "tablet",
        "strip": "strip",
        "pack": "pack",
        "line_total": "strip",
    }
    unit = unit_names.get(basis, "unit")
    unit_plural = _pluralize_unit(unit, qty)
    pack_label = refs.get("unit_label") or f"{refs['pack_size']}'s"
    pack_size = refs.get("bill_pack_size", refs.get("pack_size", 1))
    csv_pack_size = refs.get("csv_pack_size", pack_size)

    quantity_display = f"{qty} {unit_plural}"
    quantity_detail = f"Bill quantity interpreted as {qty} {_pluralize_unit(unit, qty)}"
    if refs.get("normalized"):
        quantity_detail += f" (bill pack: {pack_size}, Jan Aushadhi reference: {csv_pack_size})"
    elif pack_size > 1 and basis in {"strip", "pack", "line_total"}:
        quantity_detail += f" ({pack_label} per {unit})"
    elif basis == "tablet" and pack_size > 1:
        quantity_detail += f" (reference pack: {pack_label})"

    line_total_value = line_total if line_total is not None else pricing["billed_price"]
    if basis == "line_total":
        billed_display = f"Rs {line_total_value:.2f} (full line total for {quantity_display})"
        expected_display = f"Rs {pricing['expected_line_total']:.2f} expected for {quantity_display}"
    else:
        billed_display = (
            f"Rs {line_total_value:.2f} total - Rs {pricing['billed_price']:.2f} per {unit}"
        )
        expected_display = (
            f"Rs {pricing['expected_line_total']:.2f} for {quantity_display} "
            f"(Rs {pricing['expected_price']:.2f} per {unit})"
        )

    return {
        "quantity_display": quantity_display,
        "quantity_detail": quantity_detail,
        "pack_size_display": f"{pack_size} units" if refs.get("normalized") else pack_label,
        "billed_display": billed_display,
        "expected_display": expected_display,
        "comparison_label": f"Compared per {unit}",
    }


def process_bill_line(raw_line, ocr_text, structure_confidence=0.55, parse_source="rule_based"):
    product = None
    score = 0
    best_candidate = raw_line
    best_pricing = (None, "not_found", 1, None)
    candidate_lines = [raw_line]
    for candidate_line in candidate_lines:
        candidate_product, candidate_score = find_best_product(candidate_line)
        candidate_pricing = extract_billing_info(candidate_line)
        candidate_has_price = candidate_pricing[3] is not None
        if candidate_score > score or (candidate_product and candidate_score == score and candidate_has_price):
            product = candidate_product
            score = candidate_score
            best_candidate = candidate_line
            best_pricing = candidate_pricing
    if not product:
        return None

    billed, price_type, quantity, line_total = best_pricing
    pack_info = resolve_pack_size(best_candidate, product)
    refs = get_reference_prices(product, pack_info)
    decision = gemini_commercial_interpretation(
        best_candidate,
        quantity,
        line_total,
        billed,
        product,
        refs,
        ocr_text=ocr_text,
    )
    pricing = compute_commercial_pricing(decision, refs, quantity, line_total, billed)
    combined_confidence = min(
        float(structure_confidence or 0.55),
        float(pricing.get("ai_confidence") or 0.55),
    )
    pricing["combined_confidence"] = round(combined_confidence, 2)
    pricing["confidence_tier"] = confidence_tier(combined_confidence)
    if pricing["confidence_tier"] == "low":
        pricing["low_confidence_disclaimer"] = "Estimated comparison based on limited bill information."

    display = build_result_display_labels(quantity, pricing["comparison_basis"], refs, line_total, pricing)
    return {
        "product": product,
        "score": score,
        "quantity": quantity,
        "line_total": line_total,
        "billed": billed,
        "price_type": price_type,
        "best_candidate": best_candidate,
        "pack_info": pack_info,
        "refs": refs,
        "pricing": pricing,
        "display": display,
        "parse_source": parse_source,
        "structure_confidence": structure_confidence,
    }


def analyze_bill(text):
    cleaned = clean_ocr_text(text)
    structured = gemini_bill_structure_extraction(cleaned)
    parse_source = "rule_based"
    structure_confidence = 0.55
    bill_entries = []

    if structured and structured.get("confidence", 0) >= STRUCTURE_CONFIDENCE_THRESHOLD:
        parse_source = "gemini_structure"
        structure_confidence = structured["confidence"]
        for item in structured["items"]:
            medicine = item["medicine"]
            qty = item["quantity"]
            amount = item["amount"]
            raw_line = f"{medicine} Qty {qty} Rs {amount}"
            bill_entries.append({
                "raw_line": raw_line,
                "source": parse_source,
                "structure_confidence": structure_confidence,
            })
    else:
        bill_entries = extract_rule_based_bill_lines(cleaned)

    flagged = {}
    detected_items = []
    non_medicine_items = []
    duplicates = []
    seen = {}
    low_confidence_items = 0

    for entry in bill_entries:
        processed = process_bill_line(
            entry["raw_line"],
            cleaned,
            structure_confidence=entry.get("structure_confidence", structure_confidence),
            parse_source=entry.get("source", parse_source),
        )
        if not processed:
            raw = entry["raw_line"]
            cat = categorize_entry_rule_based(raw)
            if cat != "medicine":
                _, _, qty, line_total = extract_billing_info(raw)
                if line_total and line_total > 0:
                    non_medicine_items.append({
                        "name": raw[:100].strip(),
                        "category_type": cat,
                        "quantity": qty or 1,
                        "line_total": round(line_total, 2),
                    })
            continue

        product = processed["product"]
        pricing = processed["pricing"]
        display = processed["display"]
        quantity = processed["quantity"]
        line_total = processed["line_total"]
        billed = processed["billed"]
        price_type = processed["price_type"]
        score = processed["score"]
        pack_info = processed["pack_info"]
        refs = processed["refs"]

        key = product["generic"].lower()
        seen[key] = seen.get(key, 0) + 1
        if seen[key] == 2:
            duplicates.append(product["generic"])

        item = {
            "name": product["generic"],
            "category_type": "medicine",
            "brand": product["brand"] or "N/A",
            "category": product["category"] or "N/A",
            "unit": product["unit"],
            "quantity": quantity,
            "quantity_display": display["quantity_display"],
            "quantity_detail": display["quantity_detail"],
            "pack_size_display": display["pack_size_display"],
            "bill_pack_size": refs["bill_pack_size"],
            "csv_pack_size": refs["csv_pack_size"],
            "pack_size_source": refs["pack_size_source"],
            "price_normalized": refs.get("normalized", False),
            "billed_display": display["billed_display"],
            "expected_display": display["expected_display"],
            "comparison_label": display["comparison_label"],
            "line_total": line_total,
            "detected_price": billed,
            "expected_price": pricing["expected_price"],
            "expected_line_total": pricing["expected_line_total"],
            "billed_price": pricing["billed_price"],
            "unit_difference": pricing["difference"],
            "difference": pricing["total_difference"],
            "overpricing_percentage": pricing["overpricing_percentage"],
            "comparison_basis": pricing["comparison_basis"],
            "ai_confidence": pricing["ai_confidence"],
            "combined_confidence": pricing["combined_confidence"],
            "confidence_tier": pricing["confidence_tier"],
            "low_confidence_disclaimer": pricing.get("low_confidence_disclaimer", ""),
            "interpretation_reasoning": pricing["interpretation_reasoning"],
            "parse_source": processed["parse_source"],
            "match_score": score,
            "note": (
                f"Unit price calculated as Rs {line_total:.2f} / {quantity}"
                if price_type == "calculated_unit_price" and line_total is not None
                else "Compared using detected unit price"
            ),
            "jan_aushadhi_note": (
                f"{product['generic']} is available at Jan Aushadhi Kendras at "
                f"Rs {refs['per_tablet_price']:.2f} per unit (CSV MRP: Rs {refs['csv_mrp']:.2f})."
            ) if refs.get("per_tablet_price") and refs["per_tablet_price"] > 0 else "",
            "jan_aushadhi_savings": max(round(pricing["total_difference"], 2), 0) if pricing.get("total_difference") else 0,
        }
        detected_items.append(item)

        is_overpriced = pricing["total_difference"] is not None and pricing["total_difference"] > 0
        if pricing["confidence_tier"] == "low":
            low_confidence_items += 1
        if is_overpriced and pricing["confidence_tier"] != "low":
            flagged[product["generic"]] = {
                "expected": pricing["expected_price"],
                "billed": pricing["billed_price"],
                "quantity": quantity,
                "line_total": line_total,
                "expected_line_total": pricing["expected_line_total"],
                "extra": pricing["total_difference"],
                "overpricing_percentage": pricing["overpricing_percentage"],
                "comparison_basis": pricing["comparison_basis"],
                "ai_confidence": pricing["combined_confidence"],
                "confidence_tier": pricing["confidence_tier"],
                "category": item["category"],
                "note": (
                    f"Line total is Rs {pricing['total_difference']:.2f} above reference pricing "
                    f"({pricing['comparison_basis']} basis)."
                ),
            }

    invalid_pricing = [item["name"] for item in detected_items if item["detected_price"] is None or item["detected_price"] <= 0]
    category_counts: dict = {}
    for _i in detected_items:
        _c = _i.get("category_type", "medicine")
        category_counts[_c] = category_counts.get(_c, 0) + 1
    for _i in non_medicine_items:
        _c = _i.get("category_type", "other")
        category_counts[_c] = category_counts.get(_c, 0) + 1
    report = {
        "detected_items": detected_items,
        "non_medicine_items": non_medicine_items,
        "category_breakdown": category_counts,
        "duplicates": duplicates,
        "missing_medicine_detection": "No obvious medicine names were detected." if not detected_items else "",
        "invalid_pricing": invalid_pricing,
        "parse_source": parse_source,
        "structure_confidence": structure_confidence,
        "low_confidence_items": low_confidence_items,
        "summary": {
            "total_detected": len(detected_items),
            "overpriced_count": len(flagged),
            "estimated_savings": round(sum(item["extra"] for item in flagged.values()), 2),
            "low_confidence_disclaimer": (
                "Estimated comparison based on limited bill information."
                if low_confidence_items
                else ""
            ),
        },
    }
    return flagged, report


def gemini_bill_context(text):
    try:
        prompt = (
            "Review this medical bill OCR text. In two short paragraphs, say likely treatment category "
            "and whether common items may be covered under Ayushman Bharat PM-JAY. Avoid firm diagnosis.\n\n"
            f"{text[:5000]}"
        )
        analysis = extract_gemini_text(_gemini_generate_with_fallback(prompt))
        if not analysis:
            raise RuntimeError("Gemini returned an empty bill analysis")
        ayushman = extract_gemini_text(_gemini_generate_with_fallback(
            "From this analysis, give a cautious PM-JAY coverage note in 2-3 lines:\n" + analysis[:2000]
        ))
        illness = analysis.splitlines()[0] if analysis else "N/A"
        return illness, ayushman or "Coverage depends on PM-JAY package rules and whether the hospital is empanelled.", analysis
    except Exception as exc:
        app.logger.warning("Gemini bill context unavailable: %s", exc)
        return (
            "N/A",
            "Coverage depends on PM-JAY package rules and whether the hospital is empanelled.",
            fallback_chat_response("bill coverage"),
        )

def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return round(2 * radius * asin(sqrt(a)), 2)


def fetch_overpass_hospitals(lat, lon, radius=5000):
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="hospital"](around:{radius},{lat},{lon});
      way["amenity"="hospital"](around:{radius},{lat},{lon});
      relation["amenity"="hospital"](around:{radius},{lat},{lon});
    );
    out center tags;
    """
    data = urlencode({"data": query}).encode()
    req = Request("https://overpass-api.de/api/interpreter", data=data, headers={"User-Agent": "AyushScan/1.0"})
    with urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    hospitals = []
    for element in payload.get("elements", []):
        tags = element.get("tags", {})
        hlat = element.get("lat") or element.get("center", {}).get("lat")
        hlon = element.get("lon") or element.get("center", {}).get("lon")
        if not hlat or not hlon:
            continue
        name = tags.get("name") or "Unnamed Hospital"
        address = ", ".join(filter(None, [tags.get("addr:street"), tags.get("addr:city"), tags.get("addr:postcode")])) or "Address not available"
        hayushman = any(hint in " ".join(tags.values()).lower() for hint in AYUSHMAN_HINTS)
        hospitals.append({
            "name": name,
            "address": address,
            "distance": haversine_km(float(lat), float(lon), float(hlat), float(hlon)),
            "contact": tags.get("phone") or tags.get("contact:phone") or "Not available",
            "lat": hlat,
            "lon": hlon,
            "ayushman": hayushman,
            "map_url": f"https://www.openstreetmap.org/?mlat={hlat}&mlon={hlon}#map=16/{hlat}/{hlon}",
        })
    return sorted(hospitals, key=lambda h: h["distance"])[:20]


# State-specific scheme database
_STATE_SCHEMES = {
    "maharashtra": {"name": "Mahatma Jyotiba Phule Jan Arogya Yojana", "description": "₹5 lakh cover for 1000+ procedures in Maharashtra empanelled hospitals.", "eligibility": "Maharashtra residents — yellow/orange/white ration card holders", "website": "https://www.jeevandayee.gov.in/"},
    "tamil nadu": {"name": "CM Comprehensive Health Insurance (CMCHIS)", "description": "₹5 lakh coverage per year for government hospital treatment in TN.", "eligibility": "Tamil Nadu families with income below ₹72,000/year", "website": "https://www.cmchistn.com/"},
    "karnataka": {"name": "Arogya Karnataka", "description": "Free treatment up to ₹5 lakh in government hospitals in Karnataka.", "eligibility": "Karnataka residents below ₹1.5 lakh annual income", "website": "https://arogyakarnataka.gov.in/"},
    "west bengal": {"name": "Swasthya Sathi", "description": "₹5 lakh health cover per family per year across all Bengal government hospitals.", "eligibility": "All West Bengal families — no income bar", "website": "https://swasthyasathi.gov.in/"},
    "telangana": {"name": "Aarogyasri (Telangana)", "description": "Covers 3,000+ medical procedures for BPL families in Telangana.", "eligibility": "BPL ration card holders in Telangana", "website": "https://www.aarogyasri.telangana.gov.in/"},
    "andhra pradesh": {"name": "YSR Aarogyasri", "description": "₹5 lakh health cover per year for eligible AP families.", "eligibility": "Families with white or yellow ration card in Andhra Pradesh", "website": "https://ysrarogyasri.ap.gov.in/"},
    "rajasthan": {"name": "Chiranjeevi Swasthya Bima Yojana", "description": "₹25 lakh cashless cover at empanelled hospitals in Rajasthan.", "eligibility": "All Rajasthan families — free for BPL/small farmers", "website": "https://chiranjeevi.rajasthan.gov.in/"},
    "gujarat": {"name": "Mukhyamantri Amrutum (MA) Yojana", "description": "₹5 lakh health cover for secondary and tertiary care in Gujarat.", "eligibility": "Gujarat families with income below ₹1.20 lakh/year", "website": "https://magmayojana.gujarat.gov.in/"},
    "delhi": {"name": "Delhi Arogya Kosh", "description": "Free treatment at Delhi government hospitals; covers major surgeries.", "eligibility": "Delhi residents — BPL families prioritised", "website": "https://delhigovt.nic.in/"},
    "kerala": {"name": "Karunya Arogya Suraksha Padhathi", "description": "₹5 lakh per family per year for BPL families in Kerala.", "eligibility": "Kerala BPL families — below poverty line card holders", "website": "https://kasp.kerala.gov.in/"},
}

_CASTE_SCHEMES = {
    "sc": {"name": "National SC/ST Health Scheme (MoSJE)", "description": "Additional health benefits and waiver of co-payment under PM-JAY for SC families.", "eligibility": "Scheduled Caste families — caste certificate required", "website": "https://socialjustice.gov.in/"},
    "st": {"name": "Tribal Health Mission", "description": "Dedicated health centres and PM-JAY priority enrolment for Scheduled Tribe families.", "eligibility": "Scheduled Tribe families — tribal certificate required", "website": "https://tribal.nic.in/"},
    "ews": {"name": "EWS Health Coverage under PM-JAY", "description": "Economically Weaker Sections can access PM-JAY benefits with an EWS certificate.", "eligibility": "Annual income below ₹8 lakh — EWS certificate from tehsildar required", "website": "https://nha.gov.in/"},
}


def _rule_based_schemes(illness, user_profile=None):
    illness_lower = (illness or "").lower()
    profile = user_profile or {}
    state = (profile.get("state") or "").lower().strip().replace("_", " ")
    caste = (profile.get("caste_category") or "general").lower()
    income = (profile.get("annual_income") or "not_specified").lower()
    schemes = []

    # ── Disease-specific central schemes ─────────────────────────────────────
    if any(k in illness_lower for k in ("cancer", "tumor", "oncolog", "malignant")):
        schemes.append({"name": "Rashtriya Arogya Nidhi (RAN)", "description": "Financial assistance for BPL patients with life-threatening diseases including cancer.", "eligibility": "Below Poverty Line (BPL) families — apply via district hospital", "website": "https://mohfw.gov.in/schemes-and-programmes"})
    if any(k in illness_lower for k in ("heart", "cardiac", "coronary", "bypass")):
        schemes.append({"name": "PM-JAY — Cardiac Care Package", "description": "Covers cardiac surgeries, angioplasty, and related procedures up to ₹5 lakh.", "eligibility": "SECC 2011 eligible or state-nominated beneficiaries — check eligibility online", "website": "https://nha.gov.in/"})
    if any(k in illness_lower for k in ("kidney", "renal", "dialysis", "transplant")):
        schemes.append({"name": "PM-JAY — Renal Care Package", "description": "Covers kidney dialysis and renal transplants; free at all PM-JAY empanelled hospitals.", "eligibility": "SECC 2011 eligible families — verify at nha.gov.in", "website": "https://nha.gov.in/"})
    if any(k in illness_lower for k in ("maternal", "delivery", "pregnancy", "antenatal", "prenatal")):
        schemes.append({"name": "Pradhan Mantri Matru Vandana Yojana (PMMVY)", "description": "₹5,000 cash benefit for first live birth — covers ante-natal care and nutrition.", "eligibility": "Pregnant and lactating women for first live birth", "website": "https://wcd.nic.in/schemes/pradhan-mantri-matru-vandana-yojana"})

    # ── Caste-based additions ─────────────────────────────────────────────────
    if caste in ("sc", "st", "ews") and caste in _CASTE_SCHEMES:
        schemes.append(_CASTE_SCHEMES[caste])

    # ── State-specific scheme ─────────────────────────────────────────────────
    if state and state in _STATE_SCHEMES:
        schemes.append(_STATE_SCHEMES[state])

    # ── Income-based eligibility note ─────────────────────────────────────────
    income_label = ""
    if income in ("below_1lakh", "1_2lakh"):
        income_label = "Your income range makes you likely eligible for PM-JAY. Check at nha.gov.in."
    elif income in ("2_5lakh",):
        income_label = "You may qualify for state-specific schemes. Check with your district hospital."

    # ── PM-JAY always included ────────────────────────────────────────────────
    schemes.append({
        "name": "Ayushman Bharat PM-JAY",
        "description": f"₹5 lakh cover per year for secondary and tertiary hospitalisation.{' ' + income_label if income_label else ''}",
        "eligibility": "SECC 2011 families and state-nominated beneficiaries — verify eligibility online",
        "website": "https://nha.gov.in/",
    })
    # Deduplicate by name
    seen_names: set = set()
    unique: list = []
    for s in schemes:
        if s["name"] not in seen_names:
            seen_names.add(s["name"])
            unique.append(s)
    return unique[:4]


def suggest_government_schemes(illness, flagged, report, user_profile=None):
    if not illness or illness in ("N/A", ""):
        return _rule_based_schemes("", user_profile)
    try:
        if genai is None or not os.getenv("GOOGLE_API_KEY"):
            return _rule_based_schemes(illness, user_profile)
        profile = user_profile or {}
        state = profile.get("state", "")
        caste = profile.get("caste_category", "general")
        income = profile.get("annual_income", "not_specified")
        flagged_names = list(flagged.keys())[:5] if flagged else []
        prompt = (
            "Based on the patient profile and medical context below, suggest up to 3 relevant "
            "Indian government health schemes the patient may be eligible for. "
            "Include Ayushman Bharat PM-JAY if applicable. Use accurate, working government website URLs. "
            "Return ONLY valid JSON:\n"
            '{"schemes": [{"name": "...", "description": "...", "eligibility": "...", "website": "https://..."}]}\n\n'
            f"State: {state or 'not specified'}\n"
            f"Caste category: {caste}\n"
            f"Annual income: {income}\n"
            f"Treatment context: {illness[:400]}\n"
            f"Flagged medicines: {', '.join(flagged_names) or 'none'}\n"
        )
        raw = gemini_generate_json(prompt)
        payload = parse_json_payload(raw)
        if isinstance(payload, dict) and isinstance(payload.get("schemes"), list) and payload["schemes"]:
            gemini_schemes = [s for s in payload["schemes"][:3] if isinstance(s, dict) and s.get("name")]
            if gemini_schemes:
                return gemini_schemes
    except Exception as exc:
        app.logger.warning("Scheme suggestion failed: %s", exc)
    return _rule_based_schemes(illness, user_profile)


@app.route("/api/status")
def api_status():
    key = os.getenv("GOOGLE_API_KEY", "")
    key_ok = bool(key and len(key) > 10)
    email_ok = bool(os.getenv("EMAIL_ADDRESS") and os.getenv("EMAIL_PASSWORD"))
    gemini_test = ""
    if genai and key_ok:
        try:
            model = get_gemini_model()
            model.generate_content("ping")
            gemini_test = "ok"
        except Exception as exc:
            gemini_test = str(exc)
    elif not key:
        gemini_test = "GOOGLE_API_KEY not set"
    elif not key_ok:
        gemini_test = "GOOGLE_API_KEY too short — check your .env"
    else:
        gemini_test = "google-generativeai not installed"
    return jsonify({
        "google_api_key_set": bool(key),
        "google_api_key_format_ok": key_ok,
        "google_api_key_hint": f"{key[:6]}…" if key else "not set",
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        "gemini_ping": gemini_test,
        "email_configured": email_ok,
        "tesseract_path": os.getenv("TESSERACT_CMD", "default"),
        "products_loaded": len(PRODUCTS),
    })


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["POST"])
def contact():
    name = (request.form.get("name") or "").strip()[:200]
    email = (request.form.get("email") or "").strip()[:200]
    message = (request.form.get("message") or "").strip()[:2000]

    sender = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    if not sender or not password:
        flash("Contact form is not configured. Please email us directly.", "danger")
        return redirect(url_for("about"))

    try:
        msg = EmailMessage()
        msg["Subject"] = f"AyushScan Contact - {name}"
        msg["From"] = sender
        msg["To"] = sender
        msg.set_content(f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
            smtp.login(sender, password)
            smtp.send_message(msg)
        app.logger.info("Contact form submitted from %s", email)
        flash("Message sent successfully!", "success")
    except Exception as exc:
        app.logger.exception("Contact form email failed")
        flash("Could not send message. Please try again later.", "danger")

    return redirect(url_for("about"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    data = request.get_json(silent=True) or {}
    required = ["firstName", "lastName", "username", "email", "password"]
    if not all(data.get(field) for field in required):
        return jsonify(success=False, message="Please fill all required fields."), 400
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO users (first_name, last_name, username, email, password, preferred_language) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    data["firstName"].strip(),
                    data["lastName"].strip(),
                    data["username"].strip(),
                    data["email"].strip().lower(),
                    generate_password_hash(data["password"]),
                    session.get("language", "english"),
                ),
            )
            conn.commit()
            session["user_id"] = cursor.lastrowid
        return jsonify(success=True, redirect_url="/dashboard")
    except sqlite3.IntegrityError:
        return jsonify(success=False, message="Email or username already registered."), 409


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    # Rate limit: 10 login attempts per email per minute
    if not check_rate_limit(f"login:{email}", max_requests=10, window_sec=60):
        return jsonify(success=False, message="Too many login attempts. Please wait 1 minute."), 429
    with get_db_connection() as conn:
        user = conn.execute("SELECT id, password, preferred_language FROM users WHERE email = ?", (email,)).fetchone()
        if user and is_password_valid(user["password"], password):
            upgrade_password_if_plaintext(conn, user["id"], user["password"], password)
            session["user_id"] = user["id"]
            session["language"] = user["preferred_language"] or session.get("language", "english")
            return jsonify(success=True, redirect_url="/dashboard")
    return jsonify(success=False, message="Invalid credentials"), 401


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index", message="Logged out successfully"))


@app.route("/set_language", methods=["POST"])
def set_language():
    selected = request.form.get("language", "english")
    if selected not in TRANSLATIONS:
        selected = "english"
    session["language"] = selected
    if "user_id" in session:
        with get_db_connection() as conn:
            conn.execute("UPDATE users SET preferred_language = ? WHERE id = ?", (selected, session["user_id"]))
            conn.commit()
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_id = session["user_id"]
    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT username, email, first_name, last_name, preferred_language, state, caste_category, annual_income FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        scans = conn.execute("SELECT id, filename, flagged, savings, timestamp FROM scans WHERE user_id = ? ORDER BY timestamp DESC LIMIT 50", (user_id,)).fetchall()
        chat_count = conn.execute("SELECT COUNT(*) FROM chat_history WHERE user_id = ?", (user_id,)).fetchone()[0]
        savings = conn.execute("SELECT COALESCE(SUM(savings), 0) FROM scans WHERE user_id = ?", (user_id,)).fetchone()[0]
    metrics = {
        "total_scans": len(scans),
        "recent_scans": len(scans[:5]),
        "chat_count": chat_count,
        "savings": round(float(savings or 0), 2),
    }
    return render_template("dashboard.html", user=user, scans=scans, metrics=metrics)


@app.route("/chatbot")
def chatbot_page():
    if "user_id" not in session:
        return redirect(url_for("login"))
    with get_db_connection() as conn:
        user = conn.execute("SELECT username, email, first_name, last_name FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        history = conn.execute(
            "SELECT user_message, bot_response, language, mode, timestamp FROM chat_history WHERE user_id = ? ORDER BY timestamp ASC LIMIT 100",
            (session["user_id"],),
        ).fetchall()
    return render_template("chatbot.html", user=user, history=history)


@app.route("/chatbot/message", methods=["POST"])
def chatbot_message():
    if "user_id" not in session:
        return jsonify(success=False, reply="Please log in first.", source="error"), 401
    data = request.get_json(silent=True) or {}
    user_input = (data.get("message") or "").strip()
    mode = data.get("mode", "gemini")
    language = detect_language(user_input)
    if not user_input:
        reply = fallback_chat_response("", language, mode)
        return jsonify(success=False, reply=reply, language=language, mode=mode, source="fallback"), 400

    source = "fallback"
    reply = ""
    error_reason = ""
    try:
        if mode == "price":
            reply = find_medicine_price(user_input)
            if reply:
                source = "price_lookup"
            else:
                reply = fallback_chat_response(user_input, language, mode)
        else:
            reply = ask_gemini(user_input, language, user_id=session["user_id"])
            source = "gemini"
    except Exception as exc:
        error_reason = str(exc)
        app.logger.warning("Chatbot fallback (%s): %s", type(exc).__name__, exc)
        reply = fallback_chat_response(user_input, language, mode)
        source = "fallback"

    save_chat(session["user_id"], user_input, reply, language, mode)
    return jsonify(
        success=True,
        reply=reply,
        language=language,
        mode=mode,
        source=source,
        error_reason=error_reason if source == "fallback" else "",
    )


@app.route("/hospitals/nearby")
def hospitals_nearby():
    if "user_id" not in session:
        return jsonify(success=False, message="Unauthorized"), 401
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
        ayushman_only = request.args.get("ayushman") == "1"
        hospitals = fetch_overpass_hospitals(lat, lon)
        if ayushman_only:
            hospitals = [hospital for hospital in hospitals if hospital["ayushman"]]
        return jsonify(success=True, hospitals=hospitals)
    except Exception as exc:
        app.logger.warning("Hospital lookup failed: %s", exc)
        return jsonify(success=False, message="Hospital search is temporarily unavailable.", hospitals=[]), 503


@app.route("/scan", methods=["POST"])
def scan():
    if "user_id" not in session:
        return jsonify(success=False, message="Unauthorized access"), 401

    # Rate limit: 15 scans per user per minute
    if not check_rate_limit(f"scan:{session['user_id']}", max_requests=15, window_sec=60):
        return jsonify(success=False, message="Too many scans. Please wait a moment before trying again."), 429

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify(success=False, message="No file selected"), 400

    # Extension whitelist
    suffix = Path(secure_filename(file.filename)).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        return jsonify(success=False, message="Unsupported file type. Please upload a JPG, PNG, or PDF."), 400

    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
    file_path = UPLOAD_FOLDER / filename
    file.save(file_path)
    try:
        if file_path.suffix.lower() == ".pdf":
            text, scan_mode = extract_pdf_text(file_path)
            if not text:
                if pytesseract is None or Image is None:
                    return jsonify(
                        success=False,
                        message="This PDF needs OCR to read scanned pages, but OCR dependencies are missing. Text-based PDFs still work.",
                    ), 500
                if pdfium is None:
                    return jsonify(
                        success=False,
                        message="PDF rendering support is missing. Run pip install -r requirements.txt, then restart the app.",
                    ), 500
                return jsonify(success=False, message="Could not read this PDF. Please try a clearer PDF or an image upload."), 400
        else:
            if pytesseract is None or Image is None:
                return jsonify(success=False, message="OCR dependencies are missing. Run pip install -r requirements.txt."), 500
            image = Image.open(file_path)
            text = ocr_image_to_text(image)
            scan_mode = "image"
        flagged, report = analyze_bill(text)
        illness, covered, gemini_analysis = gemini_bill_context(text)
        savings = report["summary"]["estimated_savings"]
        with get_db_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO scans (user_id, filename, text, flagged, report, illness, covered, savings) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (session["user_id"], filename, text, json.dumps(flagged), json.dumps(report), illness, covered, savings),
            )
            conn.commit()
            scan_id = cursor.lastrowid
        return jsonify(
            success=True,
            scan_id=scan_id,
            message="Overbilling detected." if flagged else "No overbilling detected.",
            flagged=flagged,
            report=report,
            text=text,
            gemini_analysis=gemini_analysis,
            scan_mode=scan_mode,
        )
    except UnidentifiedImageError:
        return jsonify(success=False, message="Invalid or corrupted image file."), 400
    except Exception as exc:
        app.logger.exception("Scan failed")
        return jsonify(success=False, message=f"Scan failed: {exc}"), 500
    finally:
        if file_path.exists():
            file_path.unlink()


@app.route("/result/<int:scan_id>")
def result(scan_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT text, flagged, report, illness, covered FROM scans WHERE id = ? AND user_id = ?",
            (scan_id, session["user_id"]),
        ).fetchone()
    if not row:
        flash("Scan not found.", "danger")
        return redirect(url_for("dashboard"))
    flagged = json.loads(row["flagged"] or "{}")
    report = json.loads(row["report"] or "{}")
    illness = row["illness"] or "N/A"
    with get_db_connection() as conn:
        uprofile = conn.execute(
            "SELECT state, caste_category, annual_income FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
    user_profile = dict(uprofile) if uprofile else {}
    schemes = suggest_government_schemes(illness, flagged, report, user_profile)
    return render_template(
        "result.html",
        scan_id=scan_id,
        flagged=flagged,
        report=report,
        illness=illness,
        covered=row["covered"] or "N/A",
        transcript=row["text"] or "",
        scheme_info=bool(row["covered"]),
        schemes=schemes,
    )


@app.route("/result/<int:scan_id>/export/csv")
def export_scan_csv(scan_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT filename, report, illness, timestamp FROM scans WHERE id = ? AND user_id = ?",
            (scan_id, session["user_id"]),
        ).fetchone()
    if not row:
        flash("Scan not found.", "danger")
        return redirect(url_for("dashboard"))
    report = json.loads(row["report"] or "{}")
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["AyushScan Bill Analysis Report"])
    writer.writerow(["File", row["filename"]])
    writer.writerow(["Date", row["timestamp"]])
    if row["illness"] and row["illness"] != "N/A":
        writer.writerow(["Treatment Context", row["illness"]])
    writer.writerow([])
    writer.writerow(["Medicine", "Category", "Quantity", "Billed Price (Rs)",
                     "Expected Price (Rs)", "Overpaid (Rs)", "Confidence"])
    for item in report.get("detected_items", []):
        writer.writerow([
            item.get("name", ""),
            item.get("category", item.get("category_type", "Medicine")),
            item.get("quantity", ""),
            item.get("billed_price", ""),
            item.get("expected_price", ""),
            item.get("difference", 0) if item.get("difference") is not None else 0,
            item.get("confidence_tier", ""),
        ])
    if report.get("non_medicine_items"):
        writer.writerow([])
        writer.writerow(["Other Bill Entries", "Category", "Quantity", "Amount (Rs)"])
        for item in report["non_medicine_items"]:
            writer.writerow([item.get("name", ""), item.get("category_type", ""),
                             item.get("quantity", ""), item.get("line_total", "")])
    summary = report.get("summary", {})
    writer.writerow([])
    writer.writerow(["Summary"])
    writer.writerow(["Total Medicines Detected", summary.get("total_detected", 0)])
    writer.writerow(["Overpriced Items", summary.get("overpriced_count", 0)])
    writer.writerow(["Estimated Savings (Rs)", summary.get("estimated_savings", 0)])
    buf.seek(0)
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=ayushscan_report_{scan_id}.csv"},
    )


@app.route("/result/<int:scan_id>/export/pdf")
def export_scan_pdf(scan_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    if not _reportlab_available:
        flash("PDF export requires reportlab. Run: pip install reportlab", "danger")
        return redirect(url_for("result", scan_id=scan_id))
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT filename, flagged, report, illness, covered, timestamp FROM scans WHERE id = ? AND user_id = ?",
            (scan_id, session["user_id"]),
        ).fetchone()
    if not row:
        flash("Scan not found.", "danger")
        return redirect(url_for("dashboard"))
    report = json.loads(row["report"] or "{}")
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    green = _rl_colors.HexColor("#2db646")
    elements = []
    elements.append(Paragraph("AyushScan — Bill Analysis Report", styles["Title"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(f"<b>File:</b> {row['filename']}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Date:</b> {row['timestamp']}", styles["Normal"]))
    if row["illness"] and row["illness"] != "N/A":
        elements.append(Paragraph(f"<b>Treatment:</b> {row['illness'][:300]}", styles["Normal"]))
    elements.append(Spacer(1, 10))
    summary = report.get("summary", {})
    elements.append(Paragraph("Summary", styles["Heading2"]))
    sum_data = [
        ["Total medicines detected", str(summary.get("total_detected", 0))],
        ["Overpriced items (high/medium confidence)", str(summary.get("overpriced_count", 0))],
        ["Estimated savings", f"Rs {summary.get('estimated_savings', 0)}"],
    ]
    sum_table = Table(sum_data, colWidths=[300, 180])
    sum_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), _rl_colors.HexColor("#f0fdf4")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, _rl_colors.grey),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(sum_table)
    elements.append(Spacer(1, 10))
    items = report.get("detected_items", [])
    if items:
        elements.append(Paragraph("Detected Medicines", styles["Heading2"]))
        tdata = [["Medicine", "Qty", "Billed (Rs)", "Expected (Rs)", "Overpaid (Rs)", "Confidence"]]
        for item in items:
            tdata.append([
                Paragraph(item.get("name", "")[:40], styles["Normal"]),
                str(item.get("quantity", "")),
                str(item.get("billed_price", "N/A")),
                str(item.get("expected_price", "N/A")),
                str(item.get("difference", 0) if item.get("difference") is not None else 0),
                item.get("confidence_tier", ""),
            ])
        med_table = Table(tdata, colWidths=[150, 35, 65, 75, 70, 65])
        med_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), green),
            ("TEXTCOLOR", (0, 0), (-1, 0), _rl_colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, _rl_colors.grey),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_rl_colors.white, _rl_colors.HexColor("#f8f8f8")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(med_table)
    if row["covered"] and row["covered"] != "N/A":
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Ayushman Bharat / PM-JAY Note", styles["Heading2"]))
        elements.append(Paragraph(row["covered"][:600], styles["Normal"]))
    doc.build(elements)
    buf.seek(0)
    return Response(
        buf.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=ayushscan_report_{scan_id}.pdf"},
    )


@app.route("/update_profile", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    allowed_incomes = {"not_specified", "below_1lakh", "1_2lakh", "2_5lakh", "above_5lakh"}
    allowed_castes = {"general", "obc", "sc", "st", "ews"}
    income = request.form.get("annual_income", "not_specified")
    caste = request.form.get("caste_category", "general")
    if income not in allowed_incomes:
        income = "not_specified"
    if caste not in allowed_castes:
        caste = "general"
    try:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE users SET first_name=?, last_name=?, username=?, state=?, caste_category=?, annual_income=? WHERE id=?",
                (
                    (request.form.get("first_name") or "").strip()[:100],
                    (request.form.get("last_name") or "").strip()[:100],
                    (request.form.get("username") or "").strip()[:50],
                    (request.form.get("state") or "").strip()[:100],
                    caste,
                    income,
                    session["user_id"],
                ),
            )
            conn.commit()
        return redirect(url_for("dashboard", message="Profile updated successfully"))
    except sqlite3.IntegrityError:
        return redirect(url_for("dashboard", message="Username already taken"))


@app.route("/change_password", methods=["POST"])
def change_password():
    if "user_id" not in session:
        return redirect(url_for("login"))
    current = request.form.get("current_password", "")
    confirm = request.form.get("confirm_current_password", "")
    new = request.form.get("new_password", "")
    confirm_new = request.form.get("confirm_new_password", "")
    if current != confirm:
        return redirect(url_for("dashboard", message="Current passwords do not match"))
    if new != confirm_new:
        return redirect(url_for("dashboard", message="New passwords do not match"))
    with get_db_connection() as conn:
        user = conn.execute("SELECT password FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        if not user or not is_password_valid(user["password"], current):
            return redirect(url_for("dashboard", message="Incorrect current password"))
        conn.execute("UPDATE users SET password = ? WHERE id = ?", (generate_password_hash(new), session["user_id"]))
        conn.commit()
    return redirect(url_for("dashboard", message="Password changed successfully"))


@app.route("/forgot_password", methods=["POST"])
def forgot_password():
    if request.is_json:
        email = (request.get_json(silent=True) or {}).get("email", "").strip().lower()
    else:
        email = request.form.get("email", "").strip().lower()
    if not email:
        if request.is_json:
            return jsonify(success=False, message="Email is required."), 400
        return redirect(url_for("dashboard", message="Email is required."))

    # Rate limit: 5 OTP requests per email per 5 minutes
    if not check_rate_limit(f"otp:{email}", max_requests=5, window_sec=300):
        msg = "Too many OTP requests. Please wait 5 minutes before requesting a new one."
        if request.is_json:
            return jsonify(success=False, message=msg), 429
        return redirect(url_for("dashboard", message=msg))

    with get_db_connection() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            if request.is_json:
                return jsonify(success=False, message="No account found with that email."), 404
            return redirect(url_for("dashboard", message="No account with that email"))
        otp = str(random.randint(100000, 999999))
        conn.execute(
            "DELETE FROM otp_tokens WHERE email = ? AND purpose = 'forgot_password' AND used = 0",
            (email,),
        )
        conn.execute(
            "INSERT INTO otp_tokens (email, otp, purpose) VALUES (?, ?, ?)",
            (email, otp, "forgot_password"),
        )
        conn.commit()
    ok, message = send_otp_email(email, otp, "forgot_password")
    if request.is_json:
        return jsonify(success=ok, message=message)
    return redirect(url_for("dashboard", message=message if ok else message))


@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    otp = (data.get("otp") or "").strip()
    if not email or not otp:
        return jsonify(success=False, message="Email and OTP are required."), 400
    with get_db_connection() as conn:
        row = conn.execute(
            """SELECT id FROM otp_tokens
               WHERE email = ? AND otp = ? AND purpose = 'forgot_password'
               AND used = 0
               AND created_at >= datetime('now', '-15 minutes')""",
            (email, otp),
        ).fetchone()
    if not row:
        return jsonify(success=False, message="Invalid or expired OTP. Please request a new one."), 400
    session["otp_verified_email"] = email
    return jsonify(success=True, message="OTP verified. Please set your new password.")


@app.route("/reset_password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or {}
    new_password = data.get("new_password") or ""
    confirm_password = data.get("confirm_password") or ""
    verified_email = session.get("otp_verified_email")
    if not verified_email:
        return jsonify(success=False, message="Session expired. Please restart the forgot password process."), 400
    if len(new_password) < 8:
        return jsonify(success=False, message="Password must be at least 8 characters."), 400
    if new_password != confirm_password:
        return jsonify(success=False, message="Passwords do not match."), 400
    with get_db_connection() as conn:
        result = conn.execute(
            "UPDATE users SET password = ? WHERE email = ?",
            (generate_password_hash(new_password), verified_email),
        )
        conn.execute(
            "UPDATE otp_tokens SET used = 1 WHERE email = ? AND purpose = 'forgot_password' AND used = 0",
            (verified_email,),
        )
        conn.commit()
        if result.rowcount == 0:
            return jsonify(success=False, message="Account not found."), 404
    session.pop("otp_verified_email", None)
    return jsonify(success=True, message="Password reset successfully. You can now log in with your new password.")


@app.route("/delete_account", methods=["POST"])
def delete_account():
    if "user_id" not in session:
        return redirect(url_for("login"))
    password = request.form.get("delete_password", "")
    with get_db_connection() as conn:
        user = conn.execute("SELECT password FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        if not user or not is_password_valid(user["password"], password):
            return redirect(url_for("dashboard", message="Incorrect password"))
        conn.execute("DELETE FROM users WHERE id = ?", (session["user_id"],))
        conn.commit()
    session.clear()
    return redirect(url_for("login", message="Account deleted successfully"))


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(_error):
    return render_template("500.html"), 500


if __name__ == "__main__":
    init_db()
    app.run(debug=False)
