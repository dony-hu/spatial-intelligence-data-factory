-- Changzhou Urban Management Data Schema
-- ============================================================
-- Comprehensive data tables for Changzhou urban command and governance

-- 1. Urban Functional Zones (城市功能区表)
CREATE TABLE IF NOT EXISTS urban_functional_zone (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    zone_id VARCHAR(20) UNIQUE NOT NULL,
    zone_name VARCHAR(100) NOT NULL,
    zone_type ENUM(
        'residential',      -- 居住区
        'commercial',       -- 商业区
        'industrial',       -- 工业区
        'administrative',   -- 行政区
        'cultural',         -- 文化区
        'recreation',       -- 娱乐区
        'transportation',   -- 交通枢纽
        'mixed'             -- 混合区
    ) NOT NULL,
    zone_geometry POLYGON,                     -- Zone boundary
    area_sqkm DECIMAL(10, 2),
    population INT,
    total_businesses INT,
    primary_industries JSON,                   -- ["industry1", "industry2"]
    administrative_level VARCHAR(50),
    manager_department VARCHAR(100),
    contact_person VARCHAR(100),
    contact_phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_zone_id (zone_id),
    INDEX idx_zone_type (zone_type),
    SPATIAL INDEX idx_geometry (zone_geometry)
);

-- 2. Event Management (事件管理表)
CREATE TABLE IF NOT EXISTS urban_event_management (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    event_id VARCHAR(20) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,         -- Traffic accident, fire, weather, etc.
    severity_level ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    event_location VARCHAR(255),
    event_coordinates POINT,
    reported_time TIMESTAMP,
    report_source VARCHAR(50),                -- citizen, police, sensor, etc.
    report_channel VARCHAR(50),               -- phone, app, sensor, etc.
    event_description TEXT,
    zone_id VARCHAR(20),
    response_required BOOLEAN DEFAULT TRUE,
    assigned_department VARCHAR(100),
    assigned_team_id VARCHAR(20),
    status ENUM('reported', 'acknowledged', 'dispatched', 'handling', 'resolved', 'closed') DEFAULT 'reported',
    first_responder_id VARCHAR(20),
    arrival_time TIMESTAMP NULL,
    resolution_time TIMESTAMP NULL,
    resolution_summary TEXT,
    incident_count INT,
    affected_area_sqm DECIMAL(10, 2),
    estimated_impact_score INT,               -- 0-100
    media_attention BOOLEAN DEFAULT FALSE,
    public_notice_issued BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_event_id (event_id),
    INDEX idx_event_type (event_type),
    INDEX idx_status (status),
    INDEX idx_reported_time (reported_time),
    INDEX idx_zone_id (zone_id),
    SPATIAL INDEX idx_location (event_coordinates),
    FULLTEXT INDEX ft_description (event_description)
);

-- 3. Resource Dispatch (资源派遣表)
CREATE TABLE IF NOT EXISTS urban_resource_dispatch (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    dispatch_id VARCHAR(20) UNIQUE NOT NULL,
    event_id VARCHAR(20) NOT NULL,
    dispatch_time TIMESTAMP,
    dispatching_center_id VARCHAR(20),
    dispatching_operator_id VARCHAR(20),
    resource_type ENUM(
        'police',
        'fire',
        'ambulance',
        'hazmat',
        'rescue',
        'traffic_control',
        'utilities',
        'volunteers'
    ) NOT NULL,
    resource_count INT,
    resources_dispatched JSON,                 -- [{type, id, status}, ...]
    dispatch_instructions TEXT,
    estimated_arrival_time TIMESTAMP,
    actual_arrival_time TIMESTAMP NULL,
    deployment_location VARCHAR(255),
    mission_duration_minutes INT,
    mission_status ENUM('dispatched', 'en_route', 'on_scene', 'completed', 'cancelled') DEFAULT 'dispatched',
    priority ENUM('critical', 'high', 'medium', 'low') DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_dispatch_id (dispatch_id),
    INDEX idx_event_id (event_id),
    INDEX idx_dispatch_time (dispatch_time),
    INDEX idx_mission_status (mission_status)
);

-- 4. Command Center Operations (指挥中心运营表)
CREATE TABLE IF NOT EXISTS urban_command_center_ops (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    operation_id VARCHAR(20) UNIQUE NOT NULL,
    center_id VARCHAR(20) NOT NULL,
    date_shift DATE,
    shift_type ENUM('morning', 'afternoon', 'evening', 'night') DEFAULT 'morning',
    duty_officer_id VARCHAR(20),
    duty_start_time TIMESTAMP,
    duty_end_time TIMESTAMP,
    events_received INT,
    events_processed INT,
    average_response_time_sec INT,
    max_response_time_sec INT,
    critical_events INT,
    dispatch_count INT,
    false_alarms INT,
    system_uptime_percent DECIMAL(5, 2),
    communication_channels_active INT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_operation_id (operation_id),
    INDEX idx_center_id (center_id),
    INDEX idx_date_shift (date_shift)
);

-- 5. Public Service Requests (公众服务请求表)
CREATE TABLE IF NOT EXISTS urban_public_service_request (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    request_id VARCHAR(20) UNIQUE NOT NULL,
    request_type VARCHAR(100),                 -- pot hole report, street cleaning, etc.
    request_category ENUM(
        'infrastructure',
        'cleanliness',
        'safety',
        'utilities',
        'landscaping',
        'other'
    ) NOT NULL,
    request_location VARCHAR(255),
    request_coordinates POINT,
    requestor_name VARCHAR(100),
    requestor_phone VARCHAR(20),
    requestor_contact VARCHAR(255),
    request_date TIMESTAMP,
    request_details TEXT,
    photo_urls JSON,                          -- [url1, url2, ...]
    assigned_department VARCHAR(100),
    assigned_team_id VARCHAR(20),
    priority ENUM('low', 'medium', 'high', 'urgent') DEFAULT 'medium',
    status ENUM('submitted', 'acknowledged', 'assigned', 'in_progress', 'completed', 'closed') DEFAULT 'submitted',
    completion_date TIMESTAMP NULL,
    completion_notes TEXT,
    satisfaction_rating INT,                  -- 1-5
    feedback_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_request_id (request_id),
    INDEX idx_request_type (request_type),
    INDEX idx_status (status),
    INDEX idx_request_date (request_date),
    SPATIAL INDEX idx_location (request_coordinates)
);

-- 6. Traffic Management (交通管理表)
CREATE TABLE IF NOT EXISTS urban_traffic_management (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    traffic_id VARCHAR(20) UNIQUE NOT NULL,
    event_id VARCHAR(20),
    incident_type VARCHAR(100),                -- accident, congestion, disabled vehicle
    incident_location VARCHAR(255),
    incident_coordinates POINT,
    incident_time TIMESTAMP,
    road_segment_id VARCHAR(20),
    estimated_duration_min INT,
    affected_lanes INT,
    estimated_vehicles_affected INT,
    congestion_level ENUM('free', 'smooth', 'moderate', 'heavy', 'gridlock') DEFAULT 'free',
    traffic_signal_adjustment BOOLEAN DEFAULT FALSE,
    police_dispatch BOOLEAN DEFAULT FALSE,
    alternate_route_suggested BOOLEAN DEFAULT FALSE,
    alternate_route TEXT,
    public_alert_issued BOOLEAN DEFAULT FALSE,
    status ENUM('active', 'clearing', 'cleared') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    cleared_time TIMESTAMP NULL,
    INDEX idx_traffic_id (traffic_id),
    INDEX idx_incident_time (incident_time),
    INDEX idx_congestion_level (congestion_level),
    SPATIAL INDEX idx_location (incident_coordinates)
);

-- 7. Environmental Monitoring (环境监测表)
CREATE TABLE IF NOT EXISTS urban_environmental_monitoring (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    monitor_id VARCHAR(20) UNIQUE NOT NULL,
    station_id VARCHAR(20),
    monitor_type VARCHAR(100),                 -- air_quality, water_quality, noise, etc.
    monitor_location VARCHAR(255),
    monitor_coordinates POINT,
    measurement_time TIMESTAMP,
    air_quality_aqi INT,
    air_quality_level ENUM('excellent', 'good', 'moderate', 'poor', 'hazardous') DEFAULT 'good',
    pm25_level INT,                            -- μg/m³
    pm10_level INT,
    no2_level INT,
    so2_level INT,
    o3_level INT,
    noise_level_db INT,                       -- decibels
    water_quality_score DECIMAL(3, 2),
    temperature_c DECIMAL(5, 2),
    humidity_percent INT,
    alert_triggered BOOLEAN DEFAULT FALSE,
    alert_type VARCHAR(100),
    alert_severity ENUM('info', 'warning', 'critical') DEFAULT 'info',
    action_taken TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_monitor_id (monitor_id),
    INDEX idx_measurement_time (measurement_time),
    INDEX idx_alert_triggered (alert_triggered),
    SPATIAL INDEX idx_location (monitor_coordinates)
);

-- 8. Emergency Shelter (应急避难所表)
CREATE TABLE IF NOT EXISTS urban_emergency_shelter (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    shelter_id VARCHAR(20) UNIQUE NOT NULL,
    shelter_name VARCHAR(100) NOT NULL,
    shelter_type VARCHAR(100),                 -- school, stadium, gym, etc.
    location VARCHAR(255),
    location_coordinates POINT,
    capacity INT,
    current_occupancy INT,
    available_beds INT,
    has_medical_facility BOOLEAN DEFAULT FALSE,
    has_food_supply BOOLEAN DEFAULT FALSE,
    accessibility_compliant BOOLEAN DEFAULT FALSE,
    manager_id VARCHAR(20),
    contact_phone VARCHAR(20),
    is_operational BOOLEAN DEFAULT TRUE,
    last_inspection_date DATE,
    supplies_status JSON,                      -- {supply_type: quantity, ...}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_shelter_id (shelter_id),
    INDEX idx_is_operational (is_operational),
    SPATIAL INDEX idx_location (location_coordinates)
);

-- 9. City Dashboard Metrics (城市仪表板指标表)
CREATE TABLE IF NOT EXISTS urban_dashboard_metrics (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    metric_id VARCHAR(20) UNIQUE NOT NULL,
    metric_date DATE,
    metric_hour INT,                          -- 0-23
    total_events_today INT,
    critical_events_today INT,
    average_response_time_sec INT,
    resources_deployed_count INT,
    citizen_complaints_today INT,
    public_service_requests_pending INT,
    traffic_incidents_active INT,
    environmental_alerts_active INT,
    system_status VARCHAR(50),                -- operational, degraded, critical
    dashboard_availability_percent DECIMAL(5, 2),
    data_freshness_sec INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_metric_id (metric_id),
    INDEX idx_metric_date (metric_date),
    INDEX idx_metric_hour (metric_hour)
);

-- 10. Operational KPIs (运营关键指标表)
CREATE TABLE IF NOT EXISTS urban_operational_kpi (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    kpi_id VARCHAR(20) UNIQUE NOT NULL,
    kpi_type VARCHAR(100),                    -- response_time, resolution_rate, etc.
    kpi_name VARCHAR(255) NOT NULL,
    measurement_period VARCHAR(50),           -- daily, weekly, monthly, yearly
    period_start_date DATE,
    period_end_date DATE,
    target_value DECIMAL(10, 2),
    actual_value DECIMAL(10, 2),
    achievement_percent DECIMAL(5, 2),
    status ENUM('on_track', 'at_risk', 'failed', 'exceeded') DEFAULT 'on_track',
    responsible_department VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_kpi_id (kpi_id),
    INDEX idx_kpi_type (kpi_type),
    INDEX idx_period_start_date (period_start_date)
);

-- Indexes for performance optimization
CREATE INDEX idx_changzhou_summary ON urban_event_management(status, created_at);
CREATE INDEX idx_zone_resource_dispatch ON urban_resource_dispatch(dispatch_time, resource_type);
CREATE INDEX idx_traffic_timeline ON urban_traffic_management(incident_time, congestion_level);
