 -- Team Everest: Database Schema for Civic Tracker
-- Lead: Prajesh L

-- Enable PostGIS for spatial mapping
CREATE EXTENSION IF NOT EXISTS postgis;

-- Main reports table
CREATE TABLE IF NOT EXISTS civic_reports (
    id SERIAL PRIMARY KEY,
    location GEOGRAPHY(Point, 4326), 
    image_hash TEXT UNIQUE,          
    category TEXT,                   
    severity INT DEFAULT 1,          
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast proximity searches
CREATE INDEX IF NOT EXISTS idx_report_location ON civic_reports USING GIST(location);
