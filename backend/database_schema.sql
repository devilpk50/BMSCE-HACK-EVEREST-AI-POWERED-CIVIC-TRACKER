-- 1. Enable Spatial Support
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Main Reports Table
CREATE TABLE IF NOT EXISTS civic_reports (
    id SERIAL PRIMARY KEY,
    location GEOGRAPHY(Point, 4326), 
    image_hash TEXT UNIQUE,          -- Enforces uniqueness for Piyush's hashing logic
    category TEXT,                   
    severity INT DEFAULT 1,          -- Incremented automatically by the trigger
    status TEXT DEFAULT 'Pending',   -- Default status for Vittal's map
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Performance Optimization
-- This index makes coordinate-based searches (like "potholes near me") much faster.
CREATE INDEX IF NOT EXISTS idx_civic_reports_location ON civic_reports USING GIST(location);

-- 4. Automation: The "Severity Boost" Trigger
-- This function checks if an image hash already exists. 
-- If it does, it updates the existing row's severity instead of adding a new one.
CREATE OR REPLACE FUNCTION handle_duplicate_reports()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM civic_reports WHERE image_hash = NEW.image_hash) THEN
        UPDATE civic_reports 
        SET severity = severity + 1 
        WHERE image_hash = NEW.image_hash;
        RETURN NULL; -- Blocks the duplicate insertion
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach the automation to the table
DROP TRIGGER IF EXISTS trigger_duplicate_check ON civic_reports;
CREATE TRIGGER trigger_duplicate_check
BEFORE INSERT ON civic_reports
FOR EACH ROW
EXECUTE FUNCTION handle_duplicate_reports();

-- 5. Data View for Frontend
-- Simplifies geometry data into plain Lat/Lng for Vittal and Prashant.
CREATE OR REPLACE VIEW map_data_view AS
SELECT 
    id, 
    ST_Y(location::geometry) AS lat, 
    ST_X(location::geometry) AS lng, 
    category, 
    severity,
    status
FROM civic_reports;
