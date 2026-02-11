-- Wujiang Public Security Data Schema
-- ============================================================
-- Comprehensive data tables for Wujiang region public security governance

-- 1. Police Station (派出所基础表)
CREATE TABLE IF NOT EXISTS ps_police_station (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    station_id VARCHAR(20) UNIQUE NOT NULL,
    station_name VARCHAR(100) NOT NULL,
    district VARCHAR(50),
    jurisdiction_area POLYGON,                 -- Jurisdiction polygon
    contact_phone VARCHAR(20),
    address VARCHAR(255),
    established_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_station_id (station_id),
    INDEX idx_active (is_active)
);

-- 2. Officer Personnel (警察人员表)
CREATE TABLE IF NOT EXISTS ps_officer (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    officer_id VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    id_number VARCHAR(18) NOT NULL,            -- ID number (masked in non-secure)
    rank VARCHAR(50),                          -- Police rank
    department VARCHAR(100),
    station_id VARCHAR(20),
    position VARCHAR(100),
    phone VARCHAR(20),
    assigned_area VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_officer_id (officer_id),
    INDEX idx_station_id (station_id),
    FOREIGN KEY (station_id) REFERENCES ps_police_station(station_id)
);

-- 3. Resident Profile (居民档案表)
CREATE TABLE IF NOT EXISTS ps_resident_profile (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    resident_id VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    id_number VARCHAR(18),                     -- ID number
    gender ENUM('M', 'F', 'Unknown'),
    age_group VARCHAR(20),
    phone VARCHAR(20),
    id_type ENUM('resident', 'temporary_resident', 'migrant_worker'),
    registration_address VARCHAR(255),
    current_address VARCHAR(255),
    registration_date DATE,
    area_id VARCHAR(20),                       -- Area/district
    profile_completeness DECIMAL(3, 2),        -- 0-1
    risk_level ENUM('low', 'medium', 'high', 'critical') DEFAULT 'low',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_resident_id (resident_id),
    INDEX idx_risk_level (risk_level),
    INDEX idx_area_id (area_id),
    FULLTEXT INDEX ft_profile (name, registration_address, current_address)
);

-- 4. Case Records (案件记录表)
CREATE TABLE IF NOT EXISTS ps_case_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    case_id VARCHAR(20) UNIQUE NOT NULL,
    case_number VARCHAR(30) NOT NULL,
    case_type VARCHAR(100),                    -- Type of crime/incident
    severity ENUM('critical', 'major', 'minor', 'trivial') DEFAULT 'minor',
    reported_date TIMESTAMP,
    incident_location VARCHAR(255),
    incident_coordinates POINT,
    reporting_officer_id VARCHAR(20),
    handling_station_id VARCHAR(20),
    status ENUM('open', 'investigation', 'solved', 'closed') DEFAULT 'open',
    description TEXT,
    involved_residents JSON,                   -- [resident_id1, resident_id2, ...]
    suspects JSON,                             -- [suspect_info1, ...]
    evidence_count INT DEFAULT 0,
    investigation_hours DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    closed_date TIMESTAMP NULL,
    INDEX idx_case_id (case_id),
    INDEX idx_status (status),
    INDEX idx_case_type (case_type),
    INDEX idx_reported_date (reported_date),
    SPATIAL INDEX idx_location (incident_coordinates)
);

-- 5. Dispatch Records (派警记录表)
CREATE TABLE IF NOT EXISTS ps_dispatch_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    dispatch_id VARCHAR(20) UNIQUE NOT NULL,
    case_id VARCHAR(20),
    dispatch_time TIMESTAMP,
    dispatch_location VARCHAR(255),
    dispatch_coordinates POINT,
    dispatched_officer_ids JSON,               -- [officer_id1, officer_id2, ...]
    dispatch_vehicle_ids JSON,                 -- [vehicle_id1, vehicle_id2, ...]
    response_time_seconds INT,
    arrival_time TIMESTAMP,
    on_scene_duration_seconds INT,
    incident_resolved BOOLEAN,
    completion_time TIMESTAMP,
    dispatch_reason VARCHAR(255),
    priority ENUM('critical', 'high', 'medium', 'low'),
    dispatch_officer_id VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_dispatch_id (dispatch_id),
    INDEX idx_dispatch_time (dispatch_time),
    INDEX idx_case_id (case_id),
    SPATIAL INDEX idx_location (dispatch_coordinates)
);

-- 6. Suspect Information (嫌疑人信息表)
CREATE TABLE IF NOT EXISTS ps_suspect_info (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    suspect_id VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100),
    id_number VARCHAR(18),
    gender ENUM('M', 'F', 'Unknown'),
    age INT,
    residence_address VARCHAR(255),
    phone VARCHAR(20),
    wanted_status ENUM('wanted', 'on_trail', 'arrested', 'released', 'not_wanted') DEFAULT 'not_wanted',
    wanted_crimes JSON,                        -- [crime1, crime2, ...]
    physical_characteristics VARCHAR(500),    -- Height, build, distinguishing marks
    known_aliases JSON,                        -- [alias1, alias2, ...]
    related_cases JSON,                        -- [case_id1, case_id2, ...]
    last_sighting_location VARCHAR(255),
    last_sighting_date TIMESTAMP,
    danger_level ENUM('low', 'medium', 'high', 'extreme') DEFAULT 'low',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_suspect_id (suspect_id),
    INDEX idx_wanted_status (wanted_status),
    INDEX idx_danger_level (danger_level)
);

-- 7. Patrol Records (巡逻记录表)
CREATE TABLE IF NOT EXISTS ps_patrol_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    patrol_id VARCHAR(20) UNIQUE NOT NULL,
    officer_id VARCHAR(20) NOT NULL,
    patrol_start_time TIMESTAMP,
    patrol_end_time TIMESTAMP,
    patrol_area_id VARCHAR(20),
    patrol_path LINESTRING,                    -- Path of patrol route
    distance_km DECIMAL(10, 2),
    duration_minutes INT,
    incidents_encountered INT,
    incidents_reported JSON,                   -- [case_id1, case_id2, ...]
    anomalies_detected TEXT,
    status ENUM('planned', 'in_progress', 'completed', 'cancelled') DEFAULT 'in_progress',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_patrol_id (patrol_id),
    INDEX idx_officer_id (officer_id),
    INDEX idx_patrol_start_time (patrol_start_time),
    SPATIAL INDEX idx_patrol_path (patrol_path)
);

-- 8. Vehicle Management (车辆管理表)
CREATE TABLE IF NOT EXISTS ps_vehicle (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    vehicle_id VARCHAR(20) UNIQUE NOT NULL,
    license_plate VARCHAR(20) NOT NULL,
    vehicle_type VARCHAR(50),                  -- patrol car, motorcycle, etc.
    model VARCHAR(100),
    station_id VARCHAR(20),
    acquisition_date DATE,
    assigned_officer_id VARCHAR(20),
    gps_device_id VARCHAR(20),
    fuel_level_percent INT,
    maintenance_due_date DATE,
    operational_status ENUM('available', 'in_use', 'maintenance', 'retired') DEFAULT 'available',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_vehicle_id (vehicle_id),
    INDEX idx_license_plate (license_plate),
    INDEX idx_station_id (station_id),
    FOREIGN KEY (station_id) REFERENCES ps_police_station(station_id)
);

-- 9. Incident Heatmap Data (事件热力数据表)
CREATE TABLE IF NOT EXISTS ps_incident_heatmap (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    heatmap_id VARCHAR(20) UNIQUE NOT NULL,
    time_period VARCHAR(50),                   -- hourly, daily, weekly, monthly
    period_start TIMESTAMP,
    period_end TIMESTAMP,
    incident_count INT,
    incident_location POINT,
    cell_size_meters INT DEFAULT 100,          -- Grid cell size
    severity_score DECIMAL(5, 2),              -- Weighted severity
    crime_types JSON,                          -- {crime_type: count, ...}
    trend ENUM('increasing', 'stable', 'decreasing'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_heatmap_id (heatmap_id),
    INDEX idx_period_start (period_start),
    SPATIAL INDEX idx_location (incident_location)
);

-- 10. Public Feedback (社会反馈表)
CREATE TABLE IF NOT EXISTS ps_public_feedback (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    feedback_id VARCHAR(20) UNIQUE NOT NULL,
    case_id VARCHAR(20),
    dispatch_id VARCHAR(20),
    feedback_date TIMESTAMP,
    rating INT,                                -- 1-5 star rating
    feedback_type VARCHAR(100),                -- complaint, praise, suggestion, etc.
    feedback_text TEXT,
    reporter_name VARCHAR(100),
    reporter_phone VARCHAR(20),
    reporter_contact VARCHAR(255),
    handled_status ENUM('pending', 'investigating', 'responded', 'closed') DEFAULT 'pending',
    handler_officer_id VARCHAR(20),
    response_date TIMESTAMP NULL,
    response_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_feedback_id (feedback_id),
    INDEX idx_handled_status (handled_status),
    INDEX idx_feedback_date (feedback_date)
);

-- Indexes for performance optimization
CREATE INDEX idx_wujiang_summary ON ps_case_record(status, created_at);
CREATE INDEX idx_dispatch_timeline ON ps_dispatch_record(dispatch_time, response_time_seconds);
CREATE INDEX idx_resident_risk ON ps_resident_profile(risk_level, area_id);
