-- Shanghai Public Security Address Governance - 24 Level Address System
-- ============================================================
-- This schema supports the full 24-level hierarchical address structure
-- Used for standardization and entity mapping in address governance

-- 1. Base Administrative Division (行政划分基础表)
CREATE TABLE IF NOT EXISTS address_admin_division (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(12) UNIQUE NOT NULL,           -- Administrative code (GB/T 2260)
    name VARCHAR(100) NOT NULL,                 -- Division name
    level INT NOT NULL,                         -- Level (1-24)
    parent_code VARCHAR(12),                    -- Parent division code
    region VARCHAR(50) NOT NULL,                -- Region: Shanghai
    geometry POINT,                             -- Spatial geometry
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    version INT DEFAULT 1,
    status ENUM('active', 'deprecated', 'pending') DEFAULT 'active',
    INDEX idx_code (code),
    INDEX idx_parent_code (parent_code),
    INDEX idx_level (level),
    INDEX idx_status (status)
);

-- 2. Address Component Library (地址成分库)
CREATE TABLE IF NOT EXISTS address_component (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    component_id VARCHAR(20) UNIQUE NOT NULL,   -- Component ID
    component_type ENUM(
        'province',      -- 省
        'city',          -- 城市
        'district',      -- 区
        'street',        -- 街道
        'lane',          -- 弄
        'building',      -- 楼
        'unit',          -- 单元
        'floor',         -- 层
        'room',          -- 房间
        'poi_category'   -- POI类别
    ) NOT NULL,
    name VARCHAR(100) NOT NULL,
    parent_id VARCHAR(20),
    level INT,
    region VARCHAR(50) NOT NULL,
    synonyms JSON,                              -- {["别名1", "别名2"]}
    abbreviations JSON,                         -- {["缩写1", "缩写2"]}
    standardized_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    version INT DEFAULT 1,
    INDEX idx_component_id (component_id),
    INDEX idx_type (component_type),
    INDEX idx_parent_id (parent_id)
);

-- 3. Address Standardization Rules (地址标准化规则表)
CREATE TABLE IF NOT EXISTS address_standardization_rule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    rule_id VARCHAR(20) UNIQUE NOT NULL,
    rule_type ENUM(
        'component_mapping',  -- 成分映射
        'separator_handling', -- 分隔符处理
        'number_format',      -- 号码格式化
        'abbreviation',       -- 缩写规范化
        'special_char'        -- 特殊字符处理
    ) NOT NULL,
    source_pattern VARCHAR(255),                -- Input pattern (regex)
    target_pattern VARCHAR(255),                -- Output pattern
    region VARCHAR(50) NOT NULL,
    priority INT DEFAULT 100,                   -- Lower = higher priority
    is_active BOOLEAN DEFAULT TRUE,
    rule_description TEXT,
    examples JSON,                              -- [{"input": "...", "output": "..."}]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    INDEX idx_rule_id (rule_id),
    INDEX idx_type (rule_type),
    INDEX idx_active (is_active)
);

-- 4. Raw Address Input (原始地址输入表)
CREATE TABLE IF NOT EXISTS address_raw_input (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    input_id VARCHAR(30) UNIQUE NOT NULL,
    raw_address TEXT NOT NULL,
    source VARCHAR(50) NOT NULL,                -- Source: public_security, real_estate, poi, etc.
    source_id VARCHAR(100),
    input_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    region VARCHAR(50) NOT NULL,
    metadata JSON,                              -- {source_system, original_id, etc}
    status ENUM('raw', 'parsing', 'standardizing', 'mapped', 'validated', 'error') DEFAULT 'raw',
    error_message TEXT,
    confidence_score DECIMAL(3, 2),             -- 0-1 confidence
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_input_id (input_id),
    INDEX idx_source (source),
    INDEX idx_status (status),
    INDEX idx_region (region),
    FULLTEXT INDEX ft_raw_address (raw_address)
);

-- 5. Parsed Address Components (已解析的地址成分表)
CREATE TABLE IF NOT EXISTS address_parsed (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    parsed_id VARCHAR(30) UNIQUE NOT NULL,
    input_id VARCHAR(30) NOT NULL,
    province VARCHAR(50),
    city VARCHAR(50),
    district VARCHAR(50),
    street VARCHAR(100),
    lane VARCHAR(100),
    building VARCHAR(50),
    unit VARCHAR(20),
    floor VARCHAR(20),
    room VARCHAR(50),
    poi_name VARCHAR(100),
    poi_category VARCHAR(50),
    component_confidence JSON,                  -- {province: 0.95, city: 0.98, ...}
    parsing_method VARCHAR(50),                 -- regex, ml_model, manual, etc
    region VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_parsed_id (parsed_id),
    INDEX idx_input_id (input_id),
    INDEX idx_district (district),
    INDEX idx_street (street),
    FULLTEXT INDEX ft_components (province, city, district, street)
);

-- 6. Standardized Address (标准化地址表)
CREATE TABLE IF NOT EXISTS address_standardized (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    standardized_id VARCHAR(30) UNIQUE NOT NULL,
    parsed_id VARCHAR(30) NOT NULL,
    standard_province VARCHAR(50),
    standard_city VARCHAR(50),
    standard_district VARCHAR(50),
    standard_street VARCHAR(100),
    standard_lane VARCHAR(100),
    standard_building VARCHAR(50),
    standard_unit VARCHAR(20),
    standard_floor VARCHAR(20),
    standard_room VARCHAR(50),
    standard_full_address VARCHAR(500),        -- Full standardized address
    coordinate_x DECIMAL(10, 6),               -- Latitude
    coordinate_y DECIMAL(10, 6),               -- Longitude
    geometry POINT,                            -- Spatial geometry
    confidence_score DECIMAL(3, 2),
    region VARCHAR(50) NOT NULL,
    standardization_rules_applied JSON,        -- [rule_id1, rule_id2, ...]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    version INT DEFAULT 1,
    INDEX idx_standardized_id (standardized_id),
    INDEX idx_parsed_id (parsed_id),
    INDEX idx_standard_full_address (standard_full_address),
    SPATIAL INDEX idx_geometry (geometry)
);

-- 7. Address to Entity Mapping (地址到实体映射表)
CREATE TABLE IF NOT EXISTS address_entity_mapping (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    mapping_id VARCHAR(30) UNIQUE NOT NULL,
    standardized_id VARCHAR(30) NOT NULL,
    entity_id VARCHAR(30) NOT NULL,            -- POI or building entity ID
    entity_type ENUM('poi', 'building', 'landmark', 'institution', 'unknown') NOT NULL,
    entity_name VARCHAR(200),
    similarity_score DECIMAL(3, 2),            -- 0-1 similarity
    mapping_method VARCHAR(50),                -- fuzzy_match, exact_match, spatial, ml_model
    match_confidence DECIMAL(3, 2),
    source_db VARCHAR(50),                     -- Which entity database
    region VARCHAR(50) NOT NULL,
    is_confirmed BOOLEAN DEFAULT FALSE,
    confirmed_by VARCHAR(100),
    confirmed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_mapping_id (mapping_id),
    INDEX idx_standardized_id (standardized_id),
    INDEX idx_entity_id (entity_id),
    INDEX idx_entity_type (entity_type),
    INDEX idx_is_confirmed (is_confirmed)
);

-- 8. Multi-Source Entity Fusion (多源实体融合表)
CREATE TABLE IF NOT EXISTS entity_multi_source_fusion (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    fusion_id VARCHAR(30) UNIQUE NOT NULL,
    canonical_entity_id VARCHAR(30) NOT NULL,  -- Master entity ID
    source_entity_id VARCHAR(30),               -- Source entity ID
    source_db VARCHAR(50) NOT NULL,            -- public_security, real_estate, baidu, amap, etc
    fusion_score DECIMAL(3, 2),
    conflict_resolution_method VARCHAR(100),   -- How conflicts were resolved
    metadata_merged JSON,                      -- Merged metadata from all sources
    region VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_fusion_id (fusion_id),
    INDEX idx_canonical_entity_id (canonical_entity_id),
    INDEX idx_source_db (source_db)
);

-- 9. Quality Metrics (质量指标表)
CREATE TABLE IF NOT EXISTS address_quality_metrics (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    metric_id VARCHAR(30) UNIQUE NOT NULL,
    metric_type ENUM(
        'completeness',       -- 完整性
        'accuracy',          -- 准确性
        'consistency',       -- 一致性
        'timeliness'        -- 及时性
    ) NOT NULL,
    standardized_id VARCHAR(30),
    entity_id VARCHAR(30),
    metric_value DECIMAL(5, 2),
    metric_unit VARCHAR(50),
    threshold_warning DECIMAL(5, 2),
    threshold_critical DECIMAL(5, 2),
    region VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_metric_id (metric_id),
    INDEX idx_type (metric_type),
    INDEX idx_standardized_id (standardized_id)
);

-- 10. Address Library Version Control (地址库版本控制表)
CREATE TABLE IF NOT EXISTS address_library_version (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    version_id VARCHAR(30) UNIQUE NOT NULL,
    version_number INT NOT NULL,               -- v1, v2, v3, etc
    release_date TIMESTAMP,
    region VARCHAR(50) NOT NULL,
    total_addresses INT,
    total_entities INT,
    quality_score DECIMAL(3, 2),
    changelog TEXT,
    approved_by VARCHAR(100),
    status ENUM('draft', 'testing', 'approved', 'released', 'deprecated') DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_version_id (version_id),
    INDEX idx_status (status)
);

-- Indexes for performance optimization
CREATE INDEX idx_shanghai_region ON address_raw_input(region, status);
CREATE INDEX idx_standardized_lookup ON address_standardized(standard_full_address, region);
CREATE INDEX idx_entity_mapping_lookup ON address_entity_mapping(standardized_id, entity_type);
