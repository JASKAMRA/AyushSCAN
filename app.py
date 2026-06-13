# print(__file__)
import csv
import json
import os
# print("EMAIL_ADDRESS =", os.getenv("EMAIL_ADDRESS"))
# print("EMAIL_PASSWORD =", os.getenv("EMAIL_PASSWORD"))
import random
import re
import smtplib
import sqlite3
import ssl
from datetime import datetime
from email.message import EmailMessage
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
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
    from PIL import Image, UnidentifiedImageError
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

    fuzz = _FuzzFallback()

try:
    import google.generativeai as genai
except ImportError:
    genai = None


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "users.db"
CSV_FILE = BASE_DIR / "products.csv"
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")

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


def detect_language(text):
    if re.search(r"[\u0900-\u097F]", text or ""):
        return "hindi"
    words = set(re.findall(r"[a-zA-Z]+", (text or "").lower()))
    if words & HINGLISH_HINTS:
        return "hinglish"
    return session.get("language", "english")


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


def extract_price_info(line):
    rupee_values = re.findall(r"(?:rs\.?|inr|₹)\s*(\d+(?:\.\d{1,2})?)", line, flags=re.I)
    numbers = rupee_values or re.findall(r"\d+\.\d{1,2}|\d+", line)
    if not numbers:
        return None, "not_found"
    try:
        values = [float(v) for v in numbers]
    except ValueError:
        return None, "not_found"
    if len(values) >= 2 and values[-2] > 0 and values[-1] > values[-2]:
        return round(values[-1] / values[-2], 2), "calculated_unit_price"
    return values[-1], "detected_price"


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
                "mg": extract_mg(generic),
            })
    return products


PRODUCTS = load_products()


def find_best_product(line):
    clean_line = preprocess(line)
    line_mg = extract_mg(line)
    best_product = None
    best_score = 0
    for product in PRODUCTS:
        if line_mg and product["mg"] and abs(line_mg - product["mg"]) > 0.01:
            continue
        score = fuzz.token_set_ratio(clean_line, product["search"])
        if score > best_score:
            best_score = score
            best_product = product
    return (best_product, best_score) if best_score >= 68 else (None, best_score)


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


def ask_gemini(message, language):
    if genai is None:
        raise RuntimeError("google-generativeai is not installed")
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY is not configured")
    instruction = {
        "english": "Reply in clear English.",
        "hindi": "Reply in simple Hindi.",
        "hinglish": "Reply in friendly Hinglish using Roman script.",
    }.get(language, "Reply clearly.")
    prompt = (
        "You are Lia, AyushScan's careful medical billing assistant. "
        "Do not diagnose. Explain bills, medicine pricing, and healthcare navigation safely. "
        f"{instruction}\n\nUser: {message}"
    )
    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "models/gemini-1.5-flash-latest"))
    response = model.generate_content(prompt)
    return response.text.strip()


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
    text = re.sub(r"[^\S\r\n]+", " ", text or "")
    text = text.replace("|", " ")
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def analyze_bill(text):
    lines = clean_ocr_text(text).splitlines()
    flagged = {}
    detected_items = []
    duplicates = []
    seen = {}

    for raw_line in lines:
        product, score = find_best_product(raw_line)
        if not product:
            continue
        billed, price_type = extract_price_info(raw_line)
        key = product["generic"].lower()
        seen[key] = seen.get(key, 0) + 1
        if seen[key] == 2:
            duplicates.append(product["generic"])
        expected = product["mrp"]
        difference = round((billed or 0) - expected, 2) if billed is not None else None
        overpricing_percentage = round((difference / expected) * 100, 2) if expected and difference and difference > 0 else 0
        item = {
            "name": product["generic"],
            "brand": product["brand"] or "N/A",
            "category": product["category"] or "N/A",
            "unit": product["unit"],
            "detected_price": billed,
            "expected_price": expected,
            "difference": difference,
            "overpricing_percentage": overpricing_percentage,
            "match_score": score,
            "note": f"Compared using {price_type}",
        }
        detected_items.append(item)
        if billed is not None and billed > expected:
            flagged[product["generic"]] = {
                "expected": expected,
                "billed": billed,
                "extra": difference,
                "overpricing_percentage": overpricing_percentage,
                "category": item["category"],
                "note": f"Overpriced by {overpricing_percentage}% compared with reference MRP.",
            }

    invalid_pricing = [item["name"] for item in detected_items if item["detected_price"] is None or item["detected_price"] <= 0]
    report = {
        "detected_items": detected_items,
        "duplicates": duplicates,
        "missing_medicine_detection": "No obvious medicine names were detected." if not detected_items else "",
        "invalid_pricing": invalid_pricing,
        "summary": {
            "total_detected": len(detected_items),
            "overpriced_count": len(flagged),
            "estimated_savings": round(sum(item["extra"] for item in flagged.values()), 2),
        },
    }
    return flagged, report


def gemini_bill_context(text):
    try:
        if genai is None:
            raise RuntimeError("google-generativeai is not installed")
        if not os.getenv("GOOGLE_API_KEY"):
            raise RuntimeError("GOOGLE_API_KEY missing")
        model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "models/gemini-1.5-flash-latest"))
        prompt = (
            "Review this medical bill OCR text. In two short paragraphs, say likely treatment category "
            "and whether common items may be covered under Ayushman Bharat PM-JAY. Avoid firm diagnosis.\n\n"
            f"{text[:5000]}"
        )
        analysis = model.generate_content(prompt).text.strip()
        ayushman = model.generate_content(
            "From this analysis, give a cautious PM-JAY coverage note in 2-3 lines:\n" + analysis[:2000]
        ).text.strip()
        illness = analysis.splitlines()[0] if analysis else "N/A"
        return illness, ayushman, analysis
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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")
# @app.route("/about")
# def about():
#     return "ABOUT ROUTE TEST"


@app.route("/contact", methods=["POST"])
def contact():
    print("CONTACT ROUTE HIT")

    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")

    print(name, email, message)

    sender = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")

    try:
        msg = EmailMessage()
        msg["Subject"] = f"AyushScan Contact - {name}"
        msg["From"] = sender
        msg["To"] = sender

        msg.set_content(
            f"""
Name: {name}
Email: {email}

Message:
{message}
"""
        )

        print("Connecting SMTP...")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, password)
            print("SMTP LOGIN SUCCESS")

            smtp.send_message(msg)
            print("EMAIL SENT SUCCESSFULLY")

        flash("Message sent successfully!", "success")

    except Exception as e:
        print("EMAIL ERROR:")
        print(repr(e))
        flash(str(e), "danger")

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
        user = conn.execute("SELECT username, email, first_name, last_name, preferred_language FROM users WHERE id = ?", (user_id,)).fetchone()
        scans = conn.execute("SELECT id, filename, flagged, savings, timestamp FROM scans WHERE user_id = ? ORDER BY timestamp DESC", (user_id,)).fetchall()
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
        return jsonify(reply="Please log in first."), 401
    data = request.get_json(silent=True) or {}
    user_input = (data.get("message") or "").strip()
    mode = data.get("mode", "price")
    language = detect_language(user_input)
    if not user_input:
        return jsonify(reply=fallback_chat_response("", language, mode)), 400
    if mode == "price":
        reply = find_medicine_price(user_input) or fallback_chat_response(user_input, language, mode)
    else:
        try:
            reply = ask_gemini(user_input, language)
        except Exception as exc:
            app.logger.warning("Gemini chatbot fallback: %s", exc)
            reply = fallback_chat_response(user_input, language, mode)
    save_chat(session["user_id"], user_input, reply, language, mode)
    return jsonify(reply=reply, language=language)


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
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify(success=False, message="No file selected"), 400
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
    file_path = UPLOAD_FOLDER / filename
    file.save(file_path)
    try:
        if file_path.suffix.lower() == ".pdf":
            return jsonify(success=False, message="PDF upload needs OCR conversion. Please upload JPG or PNG for this demo."), 400
        if pytesseract is None or Image is None:
            return jsonify(success=False, message="OCR dependencies are missing. Run pip install -r requirements.txt."), 500
        image = Image.open(file_path)
        text = clean_ocr_text(pytesseract.image_to_string(image))
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
    return render_template(
        "result.html",
        flagged=json.loads(row["flagged"] or "{}"),
        report=json.loads(row["report"] or "{}"),
        illness=row["illness"] or "N/A",
        covered=row["covered"] or "N/A",
        scheme_info=bool(row["covered"]),
    )


@app.route("/update_profile", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    try:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE users SET first_name = ?, last_name = ?, username = ? WHERE id = ?",
                (request.form.get("first_name"), request.form.get("last_name"), request.form.get("username"), session["user_id"]),
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
    email = request.form.get("email", "").strip().lower()
    with get_db_connection() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            return redirect(url_for("dashboard", message="No account with that email"))
        otp = str(random.randint(100000, 999999))
        conn.execute("INSERT OR IGNORE INTO otp_tokens (email, otp, purpose) VALUES (?, ?, ?)", (email, otp, "forgot_password"))
        conn.commit()
    ok, message = send_otp_email(email, otp, "forgot_password")
    return redirect(url_for("dashboard", message=message if ok else message))


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
