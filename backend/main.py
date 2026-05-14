import hashlib
import os
import sqlite3
import psycopg2
from psycopg2 import sql
from typing import List, Dict, Optional, Tuple
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Database configuration
DB_CONFIG = {
    "dbname": "everest_db",
    "user": "postgres",
    "password": "YOUR_PASSWORD_HERE",  # Update with actual password
    "host": "localhost",
    "port": "5432"
}

DB_SQLITE_PATH = os.path.join(os.path.dirname(__file__), "sqlite_fallback.db")

app = FastAPI(title="Civic Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5501", "http://localhost:5501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_sqlite_connection():
    conn = sqlite3.connect(DB_SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_sqlite():
    conn = get_sqlite_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS civic_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat REAL,
            lng REAL,
            image_hash TEXT UNIQUE,
            category TEXT,
            severity INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


init_sqlite()


class ReportCreate(BaseModel):
    lat: float
    lng: float
    img_hash: str
    category: str
    severity: int = 1


def get_connection():
    """
    Establish and return a database connection.
    
    Returns:
        psycopg2 connection object or None if connection fails
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Connection error: {e}")
        return None


def save_report_fallback(lat: float, lng: float, img_hash: str, category: str, severity: int = 1) -> bool:
    """
    Save report metadata to a local SQLite fallback when PostgreSQL is unavailable.
    """
    try:
        conn = get_sqlite_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO civic_reports (lat, lng, image_hash, category, severity)
            VALUES (?, ?, ?, ?, ?)
            """,
            (lat, lng, img_hash, category, severity),
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"SQLite fallback save error: {e}")
        return False


def insert_report(lat: float, lng: float, img_hash: str, category: str, severity: int = 1) -> bool:
    """
    Insert a new civic report into the database.
    
    Args:
        lat (float): Latitude coordinate
        lng (float): Longitude coordinate
        img_hash (str): Hash of the image
        category (str): Category of the report (e.g., 'pothole', 'garbage', 'water_leak')
        severity (int): Severity level (default: 1)
    
    Returns:
        bool: True if insertion successful, False otherwise
    """
    try:
        conn = get_connection()
        if not conn:
            return save_report_fallback(lat, lng, img_hash, category, severity)
        
        cur = conn.cursor()
        
        # Query uses PostGIS to convert Lat/Lng into a Geography point
        query = """
        INSERT INTO civic_reports (location, image_hash, category, severity)
        VALUES (ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s)
        ON CONFLICT (image_hash) DO NOTHING;
        """
        
        cur.execute(query, (lng, lat, img_hash, category, severity))
        conn.commit()
        
        cur.close()
        conn.close()
        
        print(f"Report inserted successfully: {category} at ({lat}, {lng})")
        return True
    
    except Exception as e:
        print(f"Database error: {e}")
        return save_report_fallback(lat, lng, img_hash, category, severity)


def get_reports_by_category(category: str) -> List[Dict]:
    """
    Retrieve all reports of a specific category.
    
    Args:
        category (str): Category to filter by
    
    Returns:
        List[Dict]: List of reports matching the category
    """
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            query = """
            SELECT id, ST_X(location::geometry) as lat, ST_Y(location::geometry) as lng, 
                   image_hash, category, severity, created_at
            FROM civic_reports
            WHERE category = %s
            ORDER BY created_at DESC;
            """
            cur.execute(query, (category,))
            columns = [desc[0] for desc in cur.description]
            reports = [dict(zip(columns, row)) for row in cur.fetchall()]
            cur.close()
            conn.close()
            return reports
        except Exception as e:
            print(f"Database error: {e}")
            conn.close()
    
    try:
        conn = get_sqlite_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, lat as lat, lng as lng, image_hash, category, severity, created_at
            FROM civic_reports
            WHERE category = ?
            ORDER BY created_at DESC;
            """,
            (category,)
        )
        reports = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return reports
    except Exception as e:
        print(f"SQLite error: {e}")
        return []


def get_nearby_reports(lat: float, lng: float, radius_meters: int = 1000) -> List[Dict]:
    """
    Get all reports within a specified radius of a coordinate.
    
    Args:
        lat (float): Latitude coordinate
        lng (float): Longitude coordinate
        radius_meters (int): Search radius in meters (default: 1000)
    
    Returns:
        List[Dict]: List of nearby reports
    """
    try:
        conn = get_connection()
        if not conn:
            return []
        
        cur = conn.cursor()
        query = """
        SELECT id, ST_X(location::geometry) as lat, ST_Y(location::geometry) as lng, 
               image_hash, category, severity, created_at,
               ST_Distance(location, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) as distance
        FROM civic_reports
        WHERE ST_DWithin(location, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s)
        ORDER BY distance;
        """
        
        cur.execute(query, (lng, lat, lng, lat, radius_meters))
        columns = [desc[0] for desc in cur.description]
        reports = [dict(zip(columns, row)) for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return reports
    
    except Exception as e:
        print(f"Database error: {e}")
        return []


def get_report_by_id(report_id: int) -> Optional[Dict]:
    """
    Retrieve a specific report by ID.
    
    Args:
        report_id (int): ID of the report
    
    Returns:
        Dict: Report data or None if not found
    """
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            query = """
            SELECT id, ST_X(location::geometry) as lat, ST_Y(location::geometry) as lng, 
                   image_hash, category, severity, created_at
            FROM civic_reports
            WHERE id = %s;
            """
            cur.execute(query, (report_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                columns = [desc[0] for desc in cur.description]
                return dict(zip(columns, row))
            return None
        except Exception as e:
            print(f"Database error: {e}")
            conn.close()
    
    try:
        conn = get_sqlite_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, lat as lat, lng as lng, image_hash, category, severity, created_at
            FROM civic_reports
            WHERE id = ?;
            """,
            (report_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"SQLite error: {e}")
        return None


def update_report_severity(report_id: int, severity: int) -> bool:
    """
    Update the severity level of a report.
    
    Args:
        report_id (int): ID of the report
        severity (int): New severity level
    
    Returns:
        bool: True if update successful, False otherwise
    """
    try:
        conn = get_connection()
        if not conn:
            return False
        
        cur = conn.cursor()
        query = """
        UPDATE civic_reports
        SET severity = %s
        WHERE id = %s;
        """
        
        cur.execute(query, (severity, report_id))
        conn.commit()
        
        cur.close()
        conn.close()
        
        return True
    
    except Exception as e:
        print(f"Database error: {e}")
        return False


def delete_report(report_id: int) -> bool:
    """
    Delete a report by ID.
    
    Args:
        report_id (int): ID of the report to delete
    
    Returns:
        bool: True if deletion successful, False otherwise
    """
    try:
        conn = get_connection()
        if not conn:
            return False
        
        cur = conn.cursor()
        query = "DELETE FROM civic_reports WHERE id = %s;"
        
        cur.execute(query, (report_id,))
        conn.commit()
        
        cur.close()
        conn.close()
        
        return True
    
    except Exception as e:
        print(f"Database error: {e}")
        return False


def get_all_reports() -> List[Dict]:
    """
    Retrieve all reports from the database.
    
    Returns:
        List[Dict]: List of all reports
    """
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            query = """
            SELECT id, ST_X(location::geometry) as lat, ST_Y(location::geometry) as lng, 
                   image_hash, category, severity, created_at
            FROM civic_reports
            ORDER BY created_at DESC;
            """
            cur.execute(query)
            columns = [desc[0] for desc in cur.description]
            reports = [dict(zip(columns, row)) for row in cur.fetchall()]
            cur.close()
            conn.close()
            return reports
        except Exception as e:
            print(f"Database error: {e}")
            conn.close()
    
    try:
        conn = get_sqlite_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, lat as lat, lng as lng, image_hash, category, severity, created_at
            FROM civic_reports
            ORDER BY created_at DESC;
            """
        )
        reports = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return reports
    except Exception as e:
        print(f"SQLite error: {e}")
        return []


def get_report_statistics() -> Dict:
    """
    Get statistics about reports in the database.
    
    Returns:
        Dict: Statistics including total reports, reports by category, and severity distribution
    """
    try:
        conn = get_connection()
        if not conn:
            return {}
        
        cur = conn.cursor()
        
        # Total reports
        cur.execute("SELECT COUNT(*) FROM civic_reports;")
        total_reports = cur.fetchone()[0]
        
        # Reports by category
        cur.execute("""
            SELECT category, COUNT(*) as count
            FROM civic_reports
            GROUP BY category
            ORDER BY count DESC;
        """)
        by_category = dict(cur.fetchall())
        
        # Reports by severity
        cur.execute("""
            SELECT severity, COUNT(*) as count
            FROM civic_reports
            GROUP BY severity
            ORDER BY severity;
        """)
        by_severity = dict(cur.fetchall())
        
        cur.close()
        conn.close()
        
        return {
            "total_reports": total_reports,
            "by_category": by_category,
            "by_severity": by_severity
        }
    
    except Exception as e:
        print(f"Database error: {e}")
        return {}


@app.get("/")
def read_root():
    return {"message": "Civic Tracker API"}


@app.post("/upload")
async def upload_report(
    name: str = Form(...),
    description: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    image: UploadFile = File(...),
):
    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    file_path = os.path.join(uploads_dir, image.filename)

    image_bytes = await image.read()
    with open(file_path, "wb") as f:
        f.write(image_bytes)

    img_hash = hashlib.md5(image_bytes).hexdigest()
    category = description or "reported_issue"

    success = insert_report(latitude, longitude, img_hash, category, severity=1)
    if not success:
        fallback_saved = save_report_fallback(latitude, longitude, img_hash, category, severity=1)
        if not fallback_saved:
            raise HTTPException(status_code=500, detail="Failed to save report to database or fallback storage")
        print(f"DB unavailable, saved fallback record for {img_hash}")
        return {
            "message": "Upload received successfully (saved to local fallback)",
            "saved_file": file_path,
            "image_hash": img_hash,
            "category": category,
            "fallback": True,
        }

    print(f"Received upload: {name}, {description}, {latitude}, {longitude}, saved {file_path}")

    return {
        "message": "Upload received successfully",
        "saved_file": file_path,
        "image_hash": img_hash,
        "category": category,
    }


@app.post("/reports")
def create_report_route(report: ReportCreate):
    success = insert_report(report.lat, report.lng, report.img_hash, report.category, report.severity)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to insert report")
    return {"message": "Report inserted successfully"}


@app.get("/reports")
def read_reports():
    return get_all_reports()


@app.get("/reports/{report_id}")
def read_report(report_id: int):
    report = get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


if __name__ == "__main__":
    # Example usage
    print("Civic Tracker Database Module")
    print("=" * 50)
    
    # Test insert
    print("\n1. Inserting sample reports...")
    insert_report(13.0170, 77.5905, "hash_001", "pothole", severity=3)
    insert_report(13.0175, 77.5910, "hash_002", "garbage", severity=1)
    insert_report(13.0165, 77.5900, "hash_003", "water_leak", severity=2)
    
    # Test get all reports
    print("\n2. Retrieving all reports...")
    all_reports = get_all_reports()
    for report in all_reports:
        print(f"  - {report}")
    
    # Test statistics
    print("\n3. Report Statistics:")
    stats = get_report_statistics()
    print(f"  - Total Reports: {stats.get('total_reports', 0)}")
    print(f"  - By Category: {stats.get('by_category', {})}")
    print(f"  - By Severity: {stats.get('by_severity', {})}")
    
    # Test nearby reports
    print("\n4. Nearby reports (within 5000m of 13.0170, 77.5905):")
    nearby = get_nearby_reports(13.0170, 77.5905, 5000)
    for report in nearby:
        print(f"  - {report}")
