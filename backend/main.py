import os
import sqlite3
import psycopg2
import hashlib
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE HELPERS ---

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

# --- API ENDPOINTS ---

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
):
    # 1. Save Image
    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    file_path = os.path.join(uploads_dir, image.filename)

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
        "message": "Report logged. Severity updated if duplicate detected."
    }
