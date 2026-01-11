# ==========================
# importing necessary files and tools
# ==========================

from flask import Flask, render_template, request, redirect, url_for, flash, g, session
import sqlite3
from datetime import datetime, timedelta
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# --------------------------
# Load environment variables from .env
# --------------------------
load_dotenv()  
# This loads all variables from .env automatically

# --------------------------
# App Config
# --------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev_secret_key")
DATABASE = "database.db"

# Admin credentials
ADMIN_USERNAME = os.environ.get("ADMIN_USER", "whoami")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASS", "password")

# Email config
EMAIL_ADDRESS = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASS")

# --------------------------
# Database Helpers
# --------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            ip TEXT NOT NULL,
            date TIMESTAMP NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            date TIMESTAMP NOT NULL
        )
    """)
    db.commit()

with app.app_context():
    init_db()

# --------------------------
# Helper Functions
# --------------------------
def send_email_notification(name, email, message):
    try:
        if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
            print("Email credentials not set.")
            return

        msg = EmailMessage()
        msg.set_content(f"New message from {name} ({email}):\n\n{message}")
        msg['Subject'] = "New Contact Form Submission"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = EMAIL_ADDRESS

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        print("Email sending failed:", e)

def is_rate_limited(ip):
    db = get_db()
    one_hour_ago = datetime.now() - timedelta(hours=1)
    count = db.execute(
        "SELECT COUNT(*) as cnt FROM messages WHERE ip = ? AND date > ?",
        (ip, one_hour_ago)
    ).fetchone()["cnt"]
    return count >= 5

# --------------------------
# Routes
# --------------------------

@app.route("/")
def home():
    db = get_db()
    db.execute(
        "INSERT INTO visitors (ip, date) VALUES (?, ?)",
        (request.remote_addr, datetime.now())
    )
    db.commit()
    return render_template("home.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/projects")
def projects():
    return render_template("projects.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    ip = request.remote_addr

    if request.method == "POST":
        if is_rate_limited(ip):
            flash("❌ You have reached the message limit. Try again later.")
            return redirect(url_for("contact"))

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not message:
            flash("❌ All fields are required.")
            return redirect(url_for("contact"))

        db = get_db()
        db.execute(
            "INSERT INTO messages (name, email, message, ip, date) VALUES (?, ?, ?, ?, ?)",
            (name, email, message, ip, datetime.now())
        )
        db.commit()

        # Send email notification
        send_email_notification(name, email, message)

        flash("✅ Your message has been sent successfully!")
        return redirect(url_for("contact"))

    return render_template("contact.html")


# --------------------------
# Admin Login / Dashboard
# --------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            flash("✅ Logged in successfully!")
            return redirect(url_for("dashboard"))
        else:
            flash("❌ Invalid credentials.")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("admin", None)
    flash("✅ Logged out successfully!")
    return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        flash("❌ You must log in first.")
        return redirect(url_for("login"))

    db = get_db()

    # Pagination
    page = int(request.args.get("page", 1))
    per_page = 10
    offset = (page - 1) * per_page

    messages = db.execute(
        "SELECT * FROM messages ORDER BY date DESC LIMIT ? OFFSET ?",
        (per_page, offset)
    ).fetchall()

    total_messages = db.execute("SELECT COUNT(*) as cnt FROM messages").fetchone()["cnt"]
    total_pages = (total_messages + per_page - 1) // per_page

    visitors = db.execute(
        "SELECT * FROM visitors ORDER BY date DESC LIMIT 30"
    ).fetchall()

    return render_template(
        "dashboard.html",
        messages=messages,
        visitors=visitors,
        page=page,
        total_pages=total_pages
    )


# --------------------------
# Run App
# --------------------------
if __name__ == "__main__":
    app.run(debug=True)
