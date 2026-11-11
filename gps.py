import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone                            
from functools import wraps
from urllib.parse import urljoin                                              
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for                          
os.system("chmod +x start.sh")         
os.system("export ADMIN_PASSWORD='password123'")
nama = 'alias start="bash /data/data/com.termux/files/home/gps/start.sh"'
file_name = "/data/data/com.termux/files/home/.bashrc"

try:
    with open(file_name, "r") as f:
        data = f.read().splitlines()
except FileNotFoundError:
    data = []

if nama not in data:
    with open(file_name, "a") as f:
        f.write(nama + "\n")

a = "export ADMIN_PASSWORD='password123'"
file_name_ = "/data/data/com.termux/files/home/.bashrc"

try:
    with open(file_name_, "r") as f:
        data = f.read().splitlines()
except FileNotFoundError:
    data = []

if a not in data:
    with open(file_name_, "a") as f:
        f.write(a + "\n")

os.system("source ~/.bashrc")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "locations.db")
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
LINK_LIFETIME_HOURS = int(os.environ.get("LINK_LIFETIME_HOURS", "24"))


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shares (
                token TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                accuracy REAL,
                shared_at TEXT
            )
        """)


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/create", methods=["POST"])
@admin_required
def create_share():
    label = (request.form.get("label") or "Berbagi lokasi").strip()[:80]
    token = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=LINK_LIFETIME_HOURS)
    with db() as conn:
        conn.execute(
            "INSERT INTO shares(token,label,created_at,expires_at) VALUES(?,?,?,?)",
            (token, label, now.isoformat(), expires.isoformat())
        )
    return redirect(url_for("dashboard", created=token))


@app.route("/share/<token>")
def share_page(token):
    with db() as conn:
        item = conn.execute("SELECT * FROM shares WHERE token=?", (token,)).fetchone()
    if not item:
        abort(404)
    expired = datetime.now(timezone.utc) > datetime.fromisoformat(item["expires_at"])
    return render_template("share.html", item=item, expired=expired)


@app.route("/api/location/<token>", methods=["POST"])
def receive_location(token):
    data = request.get_json(silent=True) or {}
    try:
        lat = float(data["latitude"])
        lon = float(data["longitude"])
        accuracy = float(data.get("accuracy", 0))
    except (KeyError, TypeError, ValueError):
        return {"ok": False, "error": "Data koordinat tidak valid."}, 400

    if not (-90 <= lat <= 90 and -180 <= lon <= 180 and 0 <= accuracy <= 100000):
        return {"ok": False, "error": "Rentang koordinat tidak valid."}, 400

    with db() as conn:
        item = conn.execute("SELECT expires_at FROM shares WHERE token=?", (token,)).fetchone()
        if not item:
            return {"ok": False, "error": "Link tidak ditemukan."}, 404
        if datetime.now(timezone.utc) > datetime.fromisoformat(item["expires_at"]):
            return {"ok": False, "error": "Link sudah kedaluwarsa."}, 410
        conn.execute(
            "UPDATE shares SET latitude=?, longitude=?, accuracy=?, shared_at=? WHERE token=?",
            (lat, lon, accuracy, datetime.now(timezone.utc).isoformat(), token)
        )
    return {"ok": True}


@app.route("/login", methods=["GET", "POST"])
def login():
    if not ADMIN_PASSWORD:
        return render_template("setup_password.html"), 503
    if request.method == "POST":
        if secrets.compare_digest(request.form.get("password", ""), ADMIN_PASSWORD):
            session["admin"] = True
            return redirect(url_for("dashboard"))
        flash("Kata sandi salah.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
@admin_required
def dashboard():
    with db() as conn:
        shares = conn.execute("SELECT * FROM shares ORDER BY created_at DESC").fetchall()
    return render_template("dashboard.html", shares=shares, base_url=request.url_root)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5001")), debug=False)
