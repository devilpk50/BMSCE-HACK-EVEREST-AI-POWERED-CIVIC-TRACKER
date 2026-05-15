import os
import sqlite3
import psycopg2
import hashlib
import re
import secrets
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from model_service import CivicAI 

# --- CONFIGURATION ---
DB_CONFIG = {
    "dbname": "everest_db",
    "user": "postgres",
    "password": "YOUR_PASSWORD_HERE", # LEADS: Ensure this is updated!
    "host": "localhost",
    "port": "5432"
}

app = FastAPI(title="Civic Tracker API - Team Everest")
ai_engine = CivicAI()
ACTIVE_TOKENS: Dict[str, Dict[str, str]] = {}
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "sqlite_fallback.db")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE HELPERS ---

class RegisterRequest(BaseModel):
    name: str
    email: str
    phone: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def init_auth_db():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def validate_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def validate_phone(phone: str) -> bool:
    return bool(re.match(r"^[0-9+\-\s]{10,15}$", phone))


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return f"{salt}:{digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, digest = stored_hash.split(":", 1)
    except ValueError:
        return False
    check_digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return secrets.compare_digest(check_digest, digest)


def get_current_user(authorization: Optional[str]) -> Dict[str, str]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Login required")

    token = authorization.replace("Bearer ", "", 1).strip()
    user = ACTIVE_TOKENS.get(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user

def get_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"PostgreSQL Connection error: {e}")
        return None

def insert_report(lat: float, lng: float, img_hash: str, category: str) -> bool:
    """Inserts report into PostGIS. Trigger handles severity automatically."""
    try:
        conn = get_connection()
        if not conn: return False
        cur = conn.cursor()
        
        # We use lng, lat because ST_MakePoint expects X, Y
        query = """
        INSERT INTO civic_reports (location, image_hash, category, severity)
        VALUES (ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, 1)
        ON CONFLICT (image_hash) DO NOTHING;
        """
        cur.execute(query, (lng, lat, img_hash, category))
        conn.commit()
        
        # Check if the row was actually inserted or handled by the trigger/conflict
        success = cur.rowcount > 0
        cur.close()
        conn.close()
        return True # Return true as long as no exception occurred
    except Exception as e:
        print(f"Database Insert Error: {e}")
        return False


init_auth_db()

# --- API ENDPOINTS ---

@app.get("/ping")
async def ping():
    return {"message": "pong"}


@app.post("/auth/register")
async def register_user(payload: RegisterRequest):
    name = payload.name.strip()
    email = payload.email.strip().lower()
    phone = payload.phone.strip()
    password = payload.password

    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters")
    if not validate_email(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    if not validate_phone(phone):
        raise HTTPException(status_code=400, detail="Enter a valid phone number")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (name, email, phone, password_hash) VALUES (?, ?, ?, ?)",
            (name, email, phone, hash_password(password))
        )
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Registration successful"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Email is already registered")


@app.post("/auth/login")
async def login_user(payload: LoginRequest):
    email = payload.email.strip().lower()
    password = payload.password

    if not validate_email(email) or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, password_hash FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    conn.close()

    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = secrets.token_urlsafe(32)
    ACTIVE_TOKENS[token] = {
        "id": str(user["id"]),
        "name": user["name"],
        "email": user["email"]
    }
    return {
        "status": "success",
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }
    }

@app.get("/reports")
async def read_reports():
    """Returns data from the View for Vittal's Heatmap"""
    conn = get_connection()
    if not conn: 
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        cur = conn.cursor()
        # map_data_view provides clean 'lat' and 'lng' columns
        cur.execute("SELECT lat, lng, severity, category FROM map_data_view;")
        columns = [desc[0] for desc in cur.description]
        reports = [dict(zip(columns, row)) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return reports
    except Exception as e:
        return {"error": str(e)}

@app.post("/upload")
async def upload_report(
    name: str = Form(...),
    description: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    image: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
):
    current_user = get_current_user(authorization)
    name = name.strip()
    description = description.strip()

    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters")
    if len(description) < 10:
        raise HTTPException(status_code=400, detail="Description must be at least 10 characters")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(status_code=400, detail="Invalid location coordinates")
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed")

    # 1. Save Image
    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    safe_filename = os.path.basename(image.filename or "report-image")
    file_path = os.path.join(uploads_dir, f"{secrets.token_hex(8)}-{safe_filename}")

    image_bytes = await image.read()
    with open(file_path, "wb") as f:
        f.write(image_bytes)

    # 2. AI Validation (Vishwa's logic)
    print(f"--- AI Analyzing: {image.filename} ---")
    result = ai_engine.validate_report(file_path)

    if not result["is_valid"]:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="AI Validation Failed: No civic issues detected.")

    # 3. Database Insertion
    # Use the AI fingerprint to check for duplicates
    img_hash = result["fingerprint"]
    db_success = insert_report(latitude, longitude, img_hash, result.get("category", description))
    
    if not db_success:
        os.remove(file_path)
        raise HTTPException(status_code=500, detail="Failed to log report to database.")

    return {
        "status": "success",
        "category": result.get("category", description),
        "submitted_by": current_user["name"],
        "message": "Report logged. Severity updated if duplicate detected."
    }
