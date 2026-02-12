"""
SQLite Database Adapter - Connection and query interface
"""

import sqlite3
from typing import List, Dict, Any, Optional
from contextlib import contextmanager


class SQLiteAdapter:
    """SQLite database adapter for entity relationship graph"""

    def __init__(self, db_path: str = "database/entity_graph.db"):
        self.db_path = db_path
        self.conn = None

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def insert_admin_division(self, code: str, name: str, level: int,
                             parent_code: Optional[str], region: str) -> int:
        """Insert administrative division"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO address_admin_division (code, name, level, parent_code, region)
            VALUES (?, ?, ?, ?, ?)
            """, (code, name, level, parent_code, region))
            return cursor.lastrowid

    def insert_raw_address(self, input_id: str, raw_address: str, source: str,
                          region: str, status: str = "raw", confidence: float = 0.0) -> int:
        """Insert raw address input"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO address_raw_input
            (input_id, raw_address, source, region, status, confidence_score)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (input_id, raw_address, source, region, status, confidence))
            return cursor.lastrowid

    def insert_parsed_address(self, parsed_id: str, input_id: str, province: str,
                             city: str, district: str, street: str, building: str,
                             unit: str, floor: str, room: str, poi_name: str,
                             poi_category: str, region: str) -> int:
        """Insert parsed address"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO address_parsed
            (parsed_id, input_id, province, city, district, street, building,
             unit, floor, room, poi_name, poi_category, parsing_method, region)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (parsed_id, input_id, province, city, district, street, building,
                  unit, floor, room, poi_name, poi_category, "regex", region))
            return cursor.lastrowid

    def insert_standardized_address(self, standardized_id: str, parsed_id: str,
                                   standard_full_address: str, coordinate_x: float,
                                   coordinate_y: float, confidence: float, region: str,
                                   province: str, city: str, district: str,
                                   street: str = None, building: str = None) -> int:
        """Insert standardized address"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO address_standardized
            (standardized_id, parsed_id, standard_province, standard_city, standard_district,
             standard_street, standard_building, standard_full_address, coordinate_x,
             coordinate_y, confidence_score, region)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (standardized_id, parsed_id, province, city, district, street, building,
                  standard_full_address, coordinate_x, coordinate_y, confidence, region))
            return cursor.lastrowid

    def insert_entity_mapping(self, mapping_id: str, standardized_id: str,
                             entity_id: str, entity_type: str, entity_name: str,
                             similarity_score: float, region: str) -> int:
        """Insert entity mapping"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO address_entity_mapping
            (mapping_id, standardized_id, entity_id, entity_type, entity_name,
             similarity_score, mapping_method, match_confidence, source_db, region)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (mapping_id, standardized_id, entity_id, entity_type, entity_name,
                  similarity_score, "fuzzy_match", similarity_score, "internal", region))
            return cursor.lastrowid

    def insert_entity_node(self, node_id: str, node_type: str, name: str,
                          level: Optional[int], coordinate_x: Optional[float],
                          coordinate_y: Optional[float], confidence: float,
                          region: str) -> int:
        """Insert entity node for graph"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO entity_node
            (node_id, node_type, name, level, coordinate_x, coordinate_y,
             confidence_score, region)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (node_id, node_type, name, level, coordinate_x, coordinate_y,
                  confidence, region))
            return cursor.lastrowid

    def insert_entity_relationship(self, relationship_id: str, source_node_id: str,
                                  target_node_id: str, relationship_type: str,
                                  confidence: float) -> int:
        """Insert entity relationship for graph"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO entity_relationship
            (relationship_id, source_node_id, target_node_id, relationship_type, confidence)
            VALUES (?, ?, ?, ?, ?)
            """, (relationship_id, source_node_id, target_node_id, relationship_type, confidence))
            return cursor.lastrowid

    def get_admin_divisions_by_region(self, region: str) -> List[Dict[str, Any]]:
        """Get all administrative divisions for a region"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM address_admin_division WHERE region = ? ORDER BY level
            """, (region,))
            return [dict(row) for row in cursor.fetchall()]

    def get_standardized_addresses_by_region(self, region: str) -> List[Dict[str, Any]]:
        """Get all standardized addresses for a region"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM address_standardized WHERE region = ?
            """, (region,))
            return [dict(row) for row in cursor.fetchall()]

    def get_entity_nodes(self) -> List[Dict[str, Any]]:
        """Get all entity nodes"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entity_node")
            return [dict(row) for row in cursor.fetchall()]

    def get_entity_relationships(self) -> List[Dict[str, Any]]:
        """Get all entity relationships"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entity_relationship")
            return [dict(row) for row in cursor.fetchall()]

    def get_entity_count(self) -> Dict[str, int]:
        """Get count of entities and relationships"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as count FROM entity_node")
            node_count = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM entity_relationship")
            rel_count = cursor.fetchone()['count']

            cursor.execute("""
            SELECT relationship_type, COUNT(*) as count FROM entity_relationship
            GROUP BY relationship_type
            """)
            rel_types = {row['relationship_type']: row['count'] for row in cursor.fetchall()}

            return {
                "total_nodes": node_count,
                "total_relationships": rel_count,
                "relationship_types": rel_types
            }

    def clear_all_data(self):
        """Clear all data (for testing)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM entity_relationship")
            cursor.execute("DELETE FROM entity_node")
            cursor.execute("DELETE FROM address_entity_mapping")
            cursor.execute("DELETE FROM address_standardized")
            cursor.execute("DELETE FROM address_parsed")
            cursor.execute("DELETE FROM address_raw_input")
            cursor.execute("DELETE FROM address_admin_division")
