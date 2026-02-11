"""
SQLite Database Initialization for Spatial Entity Relationship Graph
Converts MySQL schema to SQLite and creates local database
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime


class SQLiteInitializer:
    """Initialize SQLite database for entity relationship graph"""

    def __init__(self, db_path: str = "database/entity_graph.db"):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Create database connection"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def execute(self, sql: str, params=None):
        """Execute SQL statement"""
        if params:
            self.conn.execute(sql, params)
        else:
            self.conn.execute(sql)

    def commit(self):
        """Commit transactions"""
        self.conn.commit()

    def create_tables(self):
        """Create all required tables"""
        print("Creating SQLite tables...")

        # 1. Address administrative division (行政划分表)
        self.execute("""
        CREATE TABLE IF NOT EXISTS address_admin_division (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            level INTEGER NOT NULL,
            parent_code TEXT,
            region TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            version INTEGER DEFAULT 1,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (parent_code) REFERENCES address_admin_division(code)
        )
        """)
        self.execute("CREATE INDEX IF NOT EXISTS idx_code ON address_admin_division(code)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_parent_code ON address_admin_division(parent_code)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_level ON address_admin_division(level)")

        # 2. Address component library (地址成分库)
        self.execute("""
        CREATE TABLE IF NOT EXISTS address_component (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component_id TEXT UNIQUE NOT NULL,
            component_type TEXT NOT NULL,
            name TEXT NOT NULL,
            parent_id TEXT,
            level INTEGER,
            region TEXT NOT NULL,
            standardized_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            version INTEGER DEFAULT 1
        )
        """)
        self.execute("CREATE INDEX IF NOT EXISTS idx_component_id ON address_component(component_id)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_component_type ON address_component(component_type)")

        # 3. Standardization rules (标准化规则表)
        self.execute("""
        CREATE TABLE IF NOT EXISTS address_standardization_rule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id TEXT UNIQUE NOT NULL,
            rule_type TEXT NOT NULL,
            source_pattern TEXT,
            target_pattern TEXT,
            region TEXT NOT NULL,
            priority INTEGER DEFAULT 100,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 4. Raw address input (原始地址表)
        self.execute("""
        CREATE TABLE IF NOT EXISTS address_raw_input (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            input_id TEXT UNIQUE NOT NULL,
            raw_address TEXT NOT NULL,
            source TEXT NOT NULL,
            source_id TEXT,
            input_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            region TEXT NOT NULL,
            status TEXT DEFAULT 'raw',
            error_message TEXT,
            confidence_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.execute("CREATE INDEX IF NOT EXISTS idx_raw_input_id ON address_raw_input(input_id)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_raw_status ON address_raw_input(status)")

        # 5. Parsed address (解析地址表)
        self.execute("""
        CREATE TABLE IF NOT EXISTS address_parsed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parsed_id TEXT UNIQUE NOT NULL,
            input_id TEXT NOT NULL,
            province TEXT,
            city TEXT,
            district TEXT,
            street TEXT,
            lane TEXT,
            building TEXT,
            unit TEXT,
            floor TEXT,
            room TEXT,
            poi_name TEXT,
            poi_category TEXT,
            parsing_method TEXT,
            region TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (input_id) REFERENCES address_raw_input(input_id)
        )
        """)
        self.execute("CREATE INDEX IF NOT EXISTS idx_parsed_id ON address_parsed(parsed_id)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_input_id ON address_parsed(input_id)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_district ON address_parsed(district)")

        # 6. Standardized address (标准化地址表)
        self.execute("""
        CREATE TABLE IF NOT EXISTS address_standardized (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            standardized_id TEXT UNIQUE NOT NULL,
            parsed_id TEXT NOT NULL,
            standard_province TEXT,
            standard_city TEXT,
            standard_district TEXT,
            standard_street TEXT,
            standard_lane TEXT,
            standard_building TEXT,
            standard_unit TEXT,
            standard_floor TEXT,
            standard_room TEXT,
            standard_full_address TEXT,
            coordinate_x REAL,
            coordinate_y REAL,
            confidence_score REAL,
            region TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            version INTEGER DEFAULT 1,
            FOREIGN KEY (parsed_id) REFERENCES address_parsed(parsed_id)
        )
        """)
        self.execute("CREATE INDEX IF NOT EXISTS idx_std_id ON address_standardized(standardized_id)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_std_address ON address_standardized(standard_full_address)")

        # 7. Address entity mapping (地址实体映射表)
        self.execute("""
        CREATE TABLE IF NOT EXISTS address_entity_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mapping_id TEXT UNIQUE NOT NULL,
            standardized_id TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_name TEXT,
            similarity_score REAL,
            mapping_method TEXT,
            match_confidence REAL,
            source_db TEXT,
            region TEXT NOT NULL,
            is_confirmed INTEGER DEFAULT 0,
            confirmed_by TEXT,
            confirmed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (standardized_id) REFERENCES address_standardized(standardized_id)
        )
        """)
        self.execute("CREATE INDEX IF NOT EXISTS idx_mapping_id ON address_entity_mapping(mapping_id)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_entity_type ON address_entity_mapping(entity_type)")

        # 8. Entity node (实体节点表 - 图谱节点)
        self.execute("""
        CREATE TABLE IF NOT EXISTS entity_node (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT UNIQUE NOT NULL,
            node_type TEXT NOT NULL,
            name TEXT NOT NULL,
            level INTEGER,
            coordinate_x REAL,
            coordinate_y REAL,
            metadata TEXT,
            confidence_score REAL,
            region TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.execute("CREATE INDEX IF NOT EXISTS idx_node_id ON entity_node(node_id)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_node_type ON entity_node(node_type)")

        # 9. Entity relationship (实体关系表 - 图谱边)
        self.execute("""
        CREATE TABLE IF NOT EXISTS entity_relationship (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            relationship_id TEXT UNIQUE NOT NULL,
            source_node_id TEXT NOT NULL,
            target_node_id TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            confidence REAL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_node_id) REFERENCES entity_node(node_id),
            FOREIGN KEY (target_node_id) REFERENCES entity_node(node_id)
        )
        """)
        self.execute("CREATE INDEX IF NOT EXISTS idx_rel_id ON entity_relationship(relationship_id)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_rel_type ON entity_relationship(relationship_type)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_source_node ON entity_relationship(source_node_id)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_target_node ON entity_relationship(target_node_id)")

        # 10. Multi-source entity fusion (多源融合表)
        self.execute("""
        CREATE TABLE IF NOT EXISTS entity_multi_source_fusion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fusion_id TEXT UNIQUE NOT NULL,
            canonical_entity_id TEXT NOT NULL,
            source_entity_id TEXT,
            source_db TEXT NOT NULL,
            fusion_score REAL,
            region TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.execute("CREATE INDEX IF NOT EXISTS idx_fusion_id ON entity_multi_source_fusion(fusion_id)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_canonical_id ON entity_multi_source_fusion(canonical_entity_id)")

        self.commit()
        print("✓ All tables created successfully")

    def initialize(self):
        """Complete initialization process"""
        print(f"\n{'='*70}")
        print("SQLite Database Initialization")
        print(f"{'='*70}\n")

        self.connect()
        self.create_tables()
        self.disconnect()

        print(f"\n✓ Database initialized at: {os.path.abspath(self.db_path)}")
        return self.db_path


if __name__ == "__main__":
    initializer = SQLiteInitializer()
    initializer.initialize()
