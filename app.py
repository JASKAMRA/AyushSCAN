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
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                            (username, email, password))
                # commit happens automatically with `with`
            flash("Signup successful! Please login.", "success")
            return redirect(url_for("scanner"))
        except sqlite3.IntegrityError:
            flash("Email already registered.", "error")
        except sqlite3.OperationalError as e:
            flash(f"Database error: {e}", "error")

    return render_template("signup.html")

@app.route('/login', methods=["GET","POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
    except Exception:
        return jsonify(success=False, message="Invalid request"), 400

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
            user = cur.fetchone()
    except sqlite3.OperationalError as e:
        return jsonify(success=False, message=f"Database error: {e}"), 500

    if user:
        session['user_id'] = user['id']
        return jsonify(success=True)
    else:
        return jsonify(success=False, message="Invalid credentials")

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

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
