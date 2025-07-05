from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = "secret_ayushscan_key"
DATABASE = "users.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE, timeout=10)  # wait up to 10 seconds if DB is locked
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                email TEXT UNIQUE,
                password TEXT
            )
        """)

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
            return jsonify(success=False, message="Invalid request"), 400

        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                            (username, email, password))
                conn.commit()
                user_id = cur.lastrowid
            session["user_id"] = user_id  # 👈 session set
            return jsonify(success=True, redirect_url="/dashboard")
        except sqlite3.IntegrityError:
            return jsonify(success=False, message="Email already registered.")
        except sqlite3.OperationalError as e:
            return jsonify(success=False, message=f"Database error: {e}")

    return render_template("signup.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        try:
            data = request.get_json()
            email = data.get("email")
            password = data.get("password")
        except:
            return jsonify(success=False, message="Invalid request")

        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT id, password FROM users WHERE email = ?", (email,))
                user = cur.fetchone()

            if user and user["password"] == password:
                session["user_id"] = user["id"]  # ✅ Session set
                return jsonify(success=True, redirect_url="/dashboard")
            else:
                return jsonify(success=False, message="Invalid credentials")
        except Exception as e:
            return jsonify(success=False, message="Login error")

    return render_template("login.html")


@app.route('/scanner')
def scanner():
    if 'user_id' not in session:
        flash("Please login first.", "error")
        return redirect(url_for("home"))
    return render_template("scanner.html")

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")  # Optional: check if user logged in
    return render_template("dashboard.html")

@app.route("/scan", methods=["POST"])
def scan():
    if 'user_id' not in session:
        return jsonify(success=False, message="Unauthorized"), 401

    if 'file' not in request.files:
        return jsonify(success=False, message="No file part"), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify(success=False, message="No selected file"), 400

    # You can save the file or process it here.
    # For now, just simulate success:
    return jsonify(success=True, message="Scan successful!")



if __name__ == '__main__':
    init_db()
    app.run(debug=True)
