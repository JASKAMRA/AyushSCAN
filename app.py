from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import pytesseract
from PIL import Image, UnidentifiedImageError
import os
import re

app = Flask(__name__)
app.secret_key = "secret_ayushscan_key"
DATABASE = "users.db"

# Optional: pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =================== Standard Price Dataset ===================
standard_prices = {
    "paracetamol": 5.0,
    "amoxicillin": 8.0,
    "ibuprofen": 6.0,
    "blood test": 150.0,
    "xray": 300.0,
    "mri brain": 2500.0,
    "ct scan": 2000.0,
    "ultrasound": 500.0,
    "ecg": 250.0,
    "iv drip": 150.0,
    "consultation": 500.0,
    "oxygen cylinder": 800.0,
    "covid test": 1000.0,
    "cbc": 200.0,
    "urine test": 100.0,
    "liver function test": 500.0,
    "kidney function test": 500.0
}

# =================== Database Init ===================
def get_db_connection():
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                email TEXT UNIQUE,
                password TEXT
            )
        """)
        conn.commit()

# =================== Auth Routes ===================
@app.route('/')
def home():
    return render_template("index.html")

@app.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        try:
            data = request.get_json()
            username = data.get("username")
            email = data.get("email")
            password = data.get("password")
        except:
            return jsonify(success=False, message="Invalid request format"), 400

        try:
            with get_db_connection() as conn:
                conn.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                             (username, email, password))
                conn.commit()
                user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            session["user_id"] = user_id
            return jsonify(success=True, redirect_url="/dashboard")
        except sqlite3.IntegrityError:
            return jsonify(success=False, message="Email already registered.")
        except Exception as e:
            return jsonify(success=False, message=f"Database error: {str(e)}")

    return render_template("signup.html")

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            data = request.get_json()
            email = data.get("email")
            password = data.get("password")
        except:
            return jsonify(success=False, message="Invalid request format")

        try:
            with get_db_connection() as conn:
                user = conn.execute("SELECT id, password FROM users WHERE email = ?", (email,)).fetchone()

            if user and user["password"] == password:
                session["user_id"] = user["id"]
                return jsonify(success=True, redirect_url="/dashboard")
            else:
                return jsonify(success=False, message="Invalid credentials")
        except Exception as e:
            return jsonify(success=False, message="Login error: " + str(e))

    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop("user_id", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("home"))

# =================== Scanner & Dashboard ===================
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("dashboard.html")

@app.route('/scanner')
def scanner():
    if 'user_id' not in session:
        flash("Please login first.", "error")
        return redirect(url_for("home"))
    return render_template("scanner.html")

@app.route("/scan", methods=["POST"])
def scan():
    if "user_id" not in session:
        return jsonify(success=False, message="Unauthorized access"), 401

    if 'file' not in request.files:
        return jsonify(success=False, message="No file uploaded"), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify(success=False, message="No file selected"), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        print("OCR TEXT:\n", text)

        lines = text.lower().splitlines()
        overbilled_items = {}

        for line in lines:
            for item in standard_prices:
                if item in line:
                    amount_match = re.findall(r"\d+\.\d{1,2}|\d+", line)
                    if amount_match:
                        try:
                            billed_amount = float(amount_match[-1])
                            expected_price = standard_prices[item]
                            if billed_amount > expected_price:
                                overbilled_items[item] = {
                                    "expected": expected_price,
                                    "billed": billed_amount,
                                    "extra": round(billed_amount - expected_price, 2)
                                }
                        except:
                            continue

        if overbilled_items:
            return jsonify(
                success=True,
                message="⚠️ Overbilling detected in scanned bill.",
                flagged=overbilled_items,
                text=text
            )
        else:
            return jsonify(
                success=True,
                message="✅ No overbilling detected.",
                flagged={},
                text=text
            )

    except UnidentifiedImageError:
        return jsonify(success=False, message="Invalid or corrupted image file."), 400
    except Exception as e:
        return jsonify(success=False, message=f"Scan failed: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# =================== Main ===================
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
