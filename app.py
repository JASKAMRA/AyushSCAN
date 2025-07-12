from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import pytesseract
from PIL import Image, UnidentifiedImageError
import os
import google.generativeai as genai
import re
import csv
from difflib import SequenceMatcher
from rapidfuzz import fuzz
import random


app = Flask(__name__)
genai.configure(api_key="AIzaSyAD3ErnFohSPwhSJsNOjwg3JuuNZFBmtG8")
# @app.before_request
# def ensure_language_selected():
#     if request.endpoint not in ['set_language', 'static', 'home', 'index']:
#         if 'language' not in session:
#             return redirect(url_for('index'))
@app.context_processor
def inject_lang():
    return {'lang': session.get('language', 'english')}

app.secret_key = "secret_ayushscan_key"
DATABASE = "users.db"

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


UPLOAD_FOLDER = "uploads"
CSV_FILE = "products.csv"



products = []

def extract_drugs_with_mg(text):
    # Extracts all drug + mg pairs like ("paracetamol", 500)
    matches = re.findall(r"([a-zA-Z\s]+)\s*(\d+)\s*mg", text.lower())
    return [(preprocess(name), int(mg)) for name, mg in matches]

def find_medicine_price(query):
    query = query.lower()
    query_drugs = [d.strip() for d in re.split(r' and |,', query)]
    query_info = []

    for drug in query_drugs:
        name = preprocess(drug)
        mg = extract_mg(drug)
        if name:
            query_info.append((name, mg))

    best_match = None
    highest_score = 0

    with open(CSV_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            product_name = row.get("Generic Name", "").lower()
            unit = row.get("Unit Size", "").lower()
            full_text = f"{product_name} {unit}"

            entry_drugs = [d.strip() for d in re.split(r' and |,', full_text)]
            entry_info = []
            for d in entry_drugs:
                entry_name = preprocess(d)
                entry_mg = extract_mg(d)
                if entry_name:
                    entry_info.append((entry_name, entry_mg))

            # ❌ Skip if more components than asked
            if len(entry_info) != len(query_info):
                continue

            matched_all = True
            total_score = 0

            for q_name, q_mg in query_info:
                found_match = False
                for e_name, e_mg in entry_info:
                    score = fuzz.token_set_ratio(q_name, e_name)
                    if score >= 70 and (q_mg is None or (e_mg is not None and q_mg == e_mg)):
                        total_score += score
                        found_match = True
                        break
                if not found_match:
                    matched_all = False
                    break

            if matched_all and total_score > highest_score:
                highest_score = total_score
                best_match = row

    if best_match:
        return (
            f"The price of {best_match['Generic Name']} "
            f"({best_match['Unit Size']}) is ₹{best_match['MRP']} as per Janaushadhi."
        )

    return None



with open('products.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        products.append(row)


def detect_column_indices(lines):
    for i, line in enumerate(lines[:3]):
        if "quantity" in line.lower() and ("price" in line.lower() or "unit" in line.lower()):
            headers = re.split(r"\s{2,}", line.lower())
            col_map = {}
            for idx, header in enumerate(headers):
                if "quantity" in header:
                    col_map["quantity"] = idx
                elif "price" in header or "unit" in header:
                    col_map["price"] = idx
                elif "total" in header:
                    col_map["total"] = idx
            return col_map, i
    return {}, -1



# Load standard prices from CSV
def extract_price_info(line):
    numbers = re.findall(r"\d+\.\d{1,2}|\d+", line)
    if len(numbers) >= 2:
        try:
            total = float(numbers[-1])
            quantity = float(numbers[-2])
            if quantity > 0:
                return round(total / quantity, 2), "calculated_unit_price"
        except:
            pass
    elif len(numbers) == 1:
        try:
            return float(numbers[0]), "single_number"
        except:
            pass
    return None, "not_found"




def load_standard_prices(csv_path):
    prices = {}
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            name = row["Generic Name"].strip().lower()
            try:
                mrp = float(row["MRP"])
                prices[name] = mrp
            except ValueError:
                continue
    return prices
def preprocess(text):
    text = text.lower()
    remove_words = ["ip", "bp", "usp", "tablet", "tab", "capsule", "cap", "syrup", "injection"]
    for word in remove_words:
        text = text.replace(word, "")
    return text.strip()

def extract_mg(text):
    match = re.search(r"(\d+)\s*mg", text.lower())
    return int(match.group(1)) if match else None

standard_prices = load_standard_prices(CSV_FILE)

# =================== Standard Price Dataset ===================
# standard_prices = {
#     "paracetamol": 5.0,
#     "amoxicillin": 8.0,
#     "ibuprofen": 6.0,
#     "blood test": 150.0,
#     "xray": 300.0,
#     "mri brain": 2500.0,
#     "ct scan": 2000.0,
#     "ultrasound": 500.0,
#     "ecg": 250.0,
#     "iv drip": 150.0,
#     "consultation": 500.0,
#     "oxygen cylinder": 800.0,
#     "covid test": 1000.0,
#     "cbc": 200.0,
#     "urine test": 100.0,
#     "liver function test": 500.0,
#     "kidney function test": 500.0
# }

# =================== Database Init ===================
def get_db_connection():
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT,
                last_name TEXT,
                username TEXT UNIQUE,
                email TEXT UNIQUE,
                password TEXT
            )
        """)

        # Scans table (for saving scan history)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                filename TEXT,
                text TEXT,
                flagged TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # OTP tokens table (for email verification / reset password)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS otp_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                otp TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()


# =================== Auth Routes ===================
@app.route('/')
def home():
    return render_template("index.html")
@app.route("/chatbot/message", methods=["POST"])
def chatbot():
    data = request.get_json()
    user_input = data.get("message", "")
    mode = data.get("mode", "price")

    print("User input:", user_input)
    print("Selected mode:", mode)

    if mode == "price":
        price_response = find_medicine_price(user_input)
        print("Medicine Match:", price_response)
        if price_response:
            return jsonify({"reply": price_response})
        return jsonify({"reply": "Sorry, medicine not found in Janaushadhi database."})

    elif mode == "gemini":
        print("Calling Gemini...")
        try:
            model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")
            chat = model.start_chat()
            response = chat.send_message(user_input)
            return jsonify({"reply": response.text})
        except Exception as e:
            print("Gemini error:", e)
            return jsonify({"reply": "Gemini failed: " + str(e)})

    return jsonify({"reply": "Invalid mode selected."})


@app.route("/chatbot")
def chatbot_page():
    if "user_id" not in session:
        return redirect("/login")

    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT username, email, first_name, last_name FROM users WHERE id = ?",
            (session["user_id"],)
        ).fetchone()

    return render_template("chatbot.html", lang=session.get("language", "english"), user=user)




@app.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        try:
            data = request.get_json()
            first_name = data.get("firstName")
            last_name = data.get("lastName")
            username = data.get("username")
            email = data.get("email")
            password = data.get("password")
 
        except:
            return jsonify(success=False, message="Invalid request format"), 400

        try:
            with get_db_connection() as conn:
                conn.execute("INSERT INTO users (first_name, last_name, username, email, password) VALUES (?, ?, ?, ?, ?)",
                             (first_name,last_name,username, email, password))
                conn.commit()
                user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            session["user_id"] = user_id
            return jsonify(success=True, redirect_url="/dashboard")
        except sqlite3.IntegrityError:
            return jsonify(success=False, message="Email already registered.")
        except Exception as e:
            return jsonify(success=False, message=f"Database error: {str(e)}")

    return render_template("signup.html")
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/contact', methods=['POST'])
def contact():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']
    
    # for now: just print to console or later store in db
    print(f"Message from {name} ({email}): {message}")
    flash("Your message has been sent!", "success")
    return redirect(url_for('about'))  # back to About page
@app.route('/about')
def about():
    return render_template('about.html')

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
@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    username = request.form.get('username')

    try:
        with get_db_connection() as conn:
            conn.execute("""
                UPDATE users
                SET first_name = ?, last_name = ?, username = ?
                WHERE id = ?
            """, (first_name, last_name, username, user_id))
            conn.commit()
        return redirect(url_for('dashboard', message="Profile updated successfully"))


    except sqlite3.IntegrityError:
        flash("Username already taken.", "danger")

    return redirect(url_for('dashboard'))


@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    current = request.form['current_password']
    confirm = request.form['confirm_current_password']
    new = request.form['new_password']
    confirm_new = request.form['confirm_new_password']

    if current != confirm:
        return redirect(url_for('dashboard', message="Current passwords don’t match"))

    if new != confirm_new:
        return redirect(url_for('dashboard', message="New passwords don’t match"))

        

    with get_db_connection() as conn:
        user = conn.execute("SELECT password FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        if user and user["password"] != current:
            return redirect(url_for('dashboard', message="Incorrect current password"))

            

        conn.execute("UPDATE users SET password = ? WHERE id = ?", (new, session["user_id"]))
        conn.commit()

    return redirect(url_for('dashboard', message="Password changed successfully"))

@app.route('/set_language', methods=['POST'])
def set_language():
    selected = request.form.get('language', 'english')
    session['language'] = selected
    return redirect(request.referrer or '/dashboard')  # return to current page



@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    email = request.form['email']

    with get_db_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            flash("No account with that email.", "danger")
            return redirect(url_for('dashboard'))

        otp = str(random.randint(100000, 999999))
        conn.execute("INSERT INTO otp_tokens (email, otp) VALUES (?, ?)", (email, otp))
        conn.commit()

    # For now, log OTP in terminal (later send email)
    print(f"🔐 OTP for {email}: {otp}")

    return redirect(url_for('dashboard', message="OTP sent to your email"))


@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    password = request.form['delete_password']

    with get_db_connection() as conn:
        user = conn.execute("SELECT password FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        if not user or user['password'] != password:
            return redirect(url_for('dashboard', message="Incorrect password"))

        conn.execute("DELETE FROM users WHERE id = ?", (session["user_id"],))
        conn.commit()

    session.clear()
    return redirect(url_for('login', message="Account deleted successfully."))



@app.route('/logout')
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index", message="Logged out successfully"))


# =================== Scanner & Dashboard ===================
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    with get_db_connection() as conn:
        user = conn.execute("SELECT username, email, first_name, last_name FROM users WHERE id = ?", (user_id,)).fetchone()

        scans = conn.execute("""
    SELECT id, filename, flagged, timestamp 
    FROM scans 
    WHERE user_id = ? 
    ORDER BY timestamp DESC
""", (user_id,)).fetchall()

    return render_template("dashboard.html", user=user, scans=scans)




from datetime import datetime
import json

@app.route("/scan", methods=["POST"])
def scan():
    if "user_id" not in session:
        return jsonify(success=False, message="Unauthorized access"), 401

    if 'file' not in request.files:
        return jsonify(success=False, message="No file uploaded"), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify(success=False, message="No file selected"), 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Make filename unique to avoid overwrites
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename.replace(' ', '_')}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        print("\n========== 🧾 OCR EXTRACTED TEXT ==========")
        print(text)
        print("==========================================\n")

        lines = text.lower().splitlines()
        col_map, header_idx = detect_column_indices(lines)
        overbilled_items = {}

        print("🔍 ANALYSIS:")
        for i, line in enumerate(lines):
            if i <= header_idx:
                continue  # Skip header line and above

            clean_line = preprocess(line.strip())
            if not clean_line:
                continue

            print(f"\n📄 Line: {clean_line}")
            matched = False
            best_match = None
            best_score = 0.0
            ocr_mg = extract_mg(clean_line)

            for product in standard_prices:
                processed_product = preprocess(product)
                product_mg = extract_mg(processed_product)

                if ocr_mg and product_mg and ocr_mg != product_mg:
                    continue

                score = fuzz.token_set_ratio(clean_line, processed_product) / 100.0
                if score > best_score and score > 0.6:
                    best_score = score
                    best_match = product

            if best_match:
                matched = True
                expected_price = standard_prices[best_match]
                billed_amount = None
                price_type = "unknown"
                parts = re.split(r"\s{2,}", line.strip())

                try:
                    if col_map and "price" in col_map and len(parts) > col_map["price"]:
                        billed_amount = float(parts[col_map["price"]].replace("₹", "").strip())
                        price_type = "unit_price (from column)"
                        print("📊 Price extracted from column format.")
                    else:
                        billed_amount, price_type = extract_price_info(line)
                except Exception as e:
                    print(f"⚠️ Error extracting price: {e}")

                if billed_amount is not None:
                    print(f"→ 🏷 Matched Item: {best_match.upper()} (Score: {best_score:.2f})")
                    print(f"   💊 Price Type: {price_type}")
                    print(f"   🏷 MRP from CSV: ₹{expected_price:.2f}")
                    print(f"   💵 Billed Amount: ₹{billed_amount:.2f}")

                    if billed_amount > expected_price:
                        overbilled_items[best_match] = {
                            "expected": expected_price,
                            "billed": billed_amount,
                            "extra": round(billed_amount - expected_price, 2),
                            "note": f"Compared using {price_type}"
                        }
                        print(f"   🚨 Overbilled by ₹{billed_amount - expected_price:.2f}")
                    else:
                        print(f"   ✅ Billed correctly or below MRP.")
                else:
                    print("⚠️ Could not extract billed price.")
            else:
                print("❌ No matching product found in this line.")

        print("\n✅ Scan Complete.\n")

        # ✅ Save to DB
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(""" 
                INSERT INTO scans (user_id, filename, text, flagged)
                VALUES (?, ?, ?, ?)
            """, (session["user_id"], filename, text, json.dumps(overbilled_items)))
            conn.commit()
            scan_id = cursor.lastrowid  # ✅ Now this will return the correct scan ID

        return jsonify(
            success=True,
            scan_id=scan_id,
            message="⚠️ Overbilling detected in scanned bill." if overbilled_items else "✅ No overbilling detected.",
            flagged=overbilled_items,
            text=text
        )
        

    except UnidentifiedImageError:
        return jsonify(success=False, message="Invalid or corrupted image file."), 400
    except Exception as e:
        return jsonify(success=False, message=f"Scan failed: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@app.route("/result/<int:scan_id>")
def results(scan_id):
    if "user_id" not in session:
        return redirect("/login")

    with get_db_connection() as conn:
        scan = conn.execute(
            "SELECT * FROM scans WHERE id = ? AND user_id = ?",
            (scan_id, session["user_id"])
        ).fetchone()

        if not scan:
            return "Scan not found or unauthorized access", 404

        flagged = json.loads(scan["flagged"] or "{}")
        non_flagged = {}  # You can populate this later if needed

    return render_template("result.html", flagged=flagged, non_flagged=non_flagged)


# =================== Main ===================
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
