"""
Factory Database - SQLite persistence layer for factory state and operations
"""

import sqlite3
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from tools.factory_framework import (
    WorkOrder, ProductRequirement, ProcessSpec, ProductionLine,
    TaskExecution, QualityCheckResult, FactoryMetrics, generate_id
)


class FactoryDB:
    """SQLite database for factory demonstration system"""

    def __init__(self, db_path: str = "database/factory.db"):
        self.db_path = db_path
        self.init_schema()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def init_schema(self) -> None:
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Factory products table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS factory_products (
                    requirement_id TEXT PRIMARY KEY,
                    product_name TEXT NOT NULL,
                    product_type TEXT NOT NULL,
                    input_format TEXT,
                    output_format TEXT,
                    input_data_count INTEGER,
                    priority INTEGER DEFAULT 5,
                    submitted_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Factory processes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS factory_processes (
                    process_id TEXT PRIMARY KEY,
                    process_name TEXT NOT NULL,
                    steps TEXT,  -- JSON array
                    estimated_duration REAL,
                    required_workers INTEGER,
                    quality_rules TEXT,  -- JSON
                    resource_requirements TEXT,  -- JSON
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Production lines table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS production_lines (
                    line_id TEXT PRIMARY KEY,
                    line_name TEXT NOT NULL,
                    process_id TEXT,
                    max_capacity INTEGER DEFAULT 100,
                    status TEXT DEFAULT 'idle',
                    active_tasks INTEGER DEFAULT 0,
                    completed_tasks INTEGER DEFAULT 0,
                    failed_tasks INTEGER DEFAULT 0,
                    total_tokens_consumed REAL DEFAULT 0.0,
                    average_quality_score REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(process_id) REFERENCES factory_processes(process_id)
                )
            """)

            # Workers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workers (
                    worker_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    line_id TEXT NOT NULL,
                    capability_level REAL DEFAULT 1.0,
                    tokens_consumed REAL DEFAULT 0.0,
                    tasks_completed INTEGER DEFAULT 0,
                    average_quality REAL DEFAULT 1.0,
                    status TEXT DEFAULT 'available',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(line_id) REFERENCES production_lines(line_id)
                )
            """)

            # Work orders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS work_orders (
                    work_order_id TEXT PRIMARY KEY,
                    requirement_id TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    process_id TEXT NOT NULL,
                    assigned_line_id TEXT,
                    status TEXT DEFAULT 'pending',
                    priority INTEGER DEFAULT 5,
                    expected_completion TIMESTAMP,
                    quality_checks_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY(requirement_id) REFERENCES factory_products(requirement_id),
                    FOREIGN KEY(process_id) REFERENCES factory_processes(process_id),
                    FOREIGN KEY(assigned_line_id) REFERENCES production_lines(line_id)
                )
            """)

            # Task executions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_executions (
                    execution_id TEXT PRIMARY KEY,
                    work_order_id TEXT NOT NULL,
                    worker_id TEXT NOT NULL,
                    process_step TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    token_consumed REAL DEFAULT 0.0,
                    duration_minutes REAL DEFAULT 0.0,
                    quality_score REAL DEFAULT 1.0,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(work_order_id) REFERENCES work_orders(work_order_id),
                    FOREIGN KEY(worker_id) REFERENCES workers(worker_id)
                )
            """)

            # Quality checks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quality_checks (
                    check_id TEXT PRIMARY KEY,
                    work_order_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    inspector_id TEXT NOT NULL,
                    quality_score REAL NOT NULL,
                    passed BOOLEAN DEFAULT 0,
                    issues TEXT,  -- JSON array
                    recommendations TEXT,
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(work_order_id) REFERENCES work_orders(work_order_id),
                    FOREIGN KEY(execution_id) REFERENCES task_executions(execution_id)
                )
            """)

            # Factory metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS factory_metrics (
                    metric_id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_products_processed INTEGER DEFAULT 0,
                    total_tasks_completed INTEGER DEFAULT 0,
                    total_tasks_failed INTEGER DEFAULT 0,
                    quality_rate REAL DEFAULT 1.0,
                    total_tokens_consumed REAL DEFAULT 0.0,
                    average_turnaround_minutes REAL DEFAULT 0.0,
                    active_production_lines INTEGER DEFAULT 0,
                    busy_workers INTEGER DEFAULT 0
                )
            """)

            # Graph nodes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    node_id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    properties TEXT,  -- JSON
                    source_address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Graph relationships table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS graph_relationships (
                    relationship_id TEXT PRIMARY KEY,
                    source_node_id TEXT NOT NULL,
                    target_node_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    properties TEXT,  -- JSON
                    source_address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(source_node_id) REFERENCES graph_nodes(node_id),
                    FOREIGN KEY(target_node_id) REFERENCES graph_nodes(node_id)
                )
            """)

            # Create indexes for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_orders_status ON work_orders(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_worker ON task_executions(worker_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_line ON task_executions(work_order_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_checks_status ON quality_checks(passed)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON graph_nodes(node_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_rels_type ON graph_relationships(relationship_type)")

            conn.commit()

    # Product requirement operations
    def save_product_requirement(self, requirement: ProductRequirement) -> None:
        """Save a product requirement"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO factory_products
                (requirement_id, product_name, product_type, input_format, output_format,
                 input_data_count, priority, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                requirement.requirement_id,
                requirement.product_name,
                requirement.product_type.value,
                requirement.input_format,
                requirement.output_format,
                len(requirement.input_data),
                requirement.priority,
                requirement.submitted_at.isoformat()
            ))

    def get_product_requirement(self, requirement_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a product requirement"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM factory_products WHERE requirement_id = ?", (requirement_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # Process specification operations
    def save_process_spec(self, spec: ProcessSpec) -> None:
        """Save a process specification"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO factory_processes
                (process_id, process_name, steps, estimated_duration, required_workers,
                 quality_rules, resource_requirements)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                spec.process_id,
                spec.process_name,
                json.dumps([step.value for step in spec.steps]),
                spec.estimated_duration,
                spec.required_workers,
                json.dumps(spec.quality_rules),
                json.dumps(spec.resource_requirements)
            ))

    def get_process_spec(self, process_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a process specification"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM factory_processes WHERE process_id = ?", (process_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # Production line operations
    def save_production_line(self, line: ProductionLine) -> None:
        """Save a production line"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO production_lines
                (line_id, line_name, process_id, max_capacity, status,
                 active_tasks, completed_tasks, failed_tasks, total_tokens_consumed,
                 average_quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                line.line_id,
                line.line_name,
                line.process_spec.process_id if line.process_spec else None,
                line.max_capacity,
                line.status.value,
                line.active_tasks,
                line.completed_tasks,
                line.failed_tasks,
                line.total_tokens_consumed,
                line.average_quality_score
            ))

            # Save workers
            for worker in line.workers:
                cursor.execute("""
                    INSERT OR REPLACE INTO workers
                    (worker_id, name, line_id, capability_level, tokens_consumed,
                     tasks_completed, average_quality, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    worker.worker_id,
                    worker.name,
                    worker.assigned_line_id,
                    worker.capability_level,
                    worker.tokens_consumed,
                    worker.tasks_completed,
                    worker.average_quality,
                    worker.status
                ))

    def get_production_line(self, line_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a production line"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM production_lines WHERE line_id = ?", (line_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_production_lines(self) -> List[Dict[str, Any]]:
        """Retrieve all production lines"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM production_lines ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    # Work order operations
    def save_work_order(self, order: WorkOrder) -> None:
        """Save a work order"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO work_orders
                (work_order_id, requirement_id, product_name, process_id,
                 assigned_line_id, status, priority, expected_completion,
                 quality_checks_count, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.work_order_id,
                order.requirement_id,
                order.product_name,
                order.process_spec.process_id if order.process_spec else None,
                order.assigned_line_id,
                order.status.value,
                order.priority,
                order.expected_completion.isoformat() if order.expected_completion else None,
                len(order.quality_checks),
                order.completed_at.isoformat() if order.completed_at else None
            ))

    def get_work_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a work order"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM work_orders WHERE work_order_id = ?", (order_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_work_orders_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Retrieve work orders by status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM work_orders WHERE status = ? ORDER BY created_at DESC", (status,))
            return [dict(row) for row in cursor.fetchall()]

    # Task execution operations
    def save_task_execution(self, execution: TaskExecution) -> None:
        """Save a task execution"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO task_executions
                (execution_id, work_order_id, worker_id, process_step, status,
                 token_consumed, duration_minutes, quality_score,
                 started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution.execution_id,
                execution.work_order_id,
                execution.worker_id,
                execution.process_step.value,
                execution.status.value,
                execution.token_consumed,
                execution.duration_minutes,
                execution.quality_score,
                execution.started_at.isoformat() if execution.started_at else None,
                execution.completed_at.isoformat() if execution.completed_at else None
            ))

    def get_task_executions_by_worker(self, worker_id: str) -> List[Dict[str, Any]]:
        """Get all task executions for a worker"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM task_executions WHERE worker_id = ? ORDER BY created_at DESC",
                (worker_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_task_executions_by_order(self, order_id: str) -> List[Dict[str, Any]]:
        """Get all task executions for a work order"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM task_executions WHERE work_order_id = ? ORDER BY created_at DESC",
                (order_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # Quality check operations
    def save_quality_check(self, check: QualityCheckResult) -> None:
        """Save a quality check result"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO quality_checks
                (check_id, work_order_id, execution_id, inspector_id, quality_score,
                 passed, issues, recommendations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                check.check_id,
                check.work_order_id,
                check.execution_id,
                check.inspector_id,
                check.quality_score,
                1 if check.passed else 0,
                json.dumps(check.issues),
                check.recommendations
            ))

    def get_quality_checks(self, work_order_id: str = None) -> List[Dict[str, Any]]:
        """Retrieve quality checks"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if work_order_id:
                cursor.execute(
                    "SELECT * FROM quality_checks WHERE work_order_id = ? ORDER BY checked_at DESC",
                    (work_order_id,)
                )
            else:
                cursor.execute("SELECT * FROM quality_checks ORDER BY checked_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    # Metrics operations
    def save_metrics(self, metrics: FactoryMetrics) -> None:
        """Save factory metrics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO factory_metrics
                (metric_id, total_products_processed, total_tasks_completed,
                 total_tasks_failed, quality_rate, total_tokens_consumed,
                 average_turnaround_minutes, active_production_lines, busy_workers)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                generate_id('metric'),
                metrics.total_products_processed,
                metrics.total_tasks_completed,
                metrics.total_tasks_failed,
                metrics.overall_quality_rate,
                metrics.total_tokens_consumed,
                metrics.average_turnaround_minutes,
                metrics.active_production_lines,
                metrics.busy_workers
            ))

    def get_latest_metrics(self) -> Optional[Dict[str, Any]]:
        """Get latest factory metrics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM factory_metrics ORDER BY timestamp DESC LIMIT 1"
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    # Statistics and reporting
    def get_statistics(self) -> Dict[str, Any]:
        """Get factory statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Count by status
            cursor.execute("""
                SELECT status, COUNT(*) as count FROM work_orders GROUP BY status
            """)
            status_counts = {row['status']: row['count'] for row in cursor.fetchall()}

            # Total tokens
            cursor.execute("SELECT SUM(token_consumed) as total FROM task_executions")
            total_tokens = cursor.fetchone()['total'] or 0.0

            # Quality stats
            cursor.execute("""
                SELECT COUNT(*) as total, SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) as passed
                FROM quality_checks
            """)
            quality_stats = dict(cursor.fetchone())

            # Worker stats
            cursor.execute("""
                SELECT COUNT(*) as total_workers, SUM(tasks_completed) as total_tasks,
                       AVG(tokens_consumed) as avg_tokens
                FROM workers
            """)
            worker_stats = dict(cursor.fetchone())

            return {
                'work_orders_by_status': status_counts,
                'total_tokens_consumed': total_tokens,
                'quality_checks': quality_stats,
                'workers': worker_stats
            }

    # Graph operations
    def save_graph_node(self, node) -> None:
        """Save a graph node"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO graph_nodes
                (node_id, node_type, name, properties, source_address)
                VALUES (?, ?, ?, ?, ?)
            """, (
                node.node_id,
                node.node_type,
                node.name,
                json.dumps(node.properties),
                node.source_address
            ))

    def save_graph_relationship(self, relationship) -> None:
        """Save a graph relationship"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO graph_relationships
                (relationship_id, source_node_id, target_node_id, relationship_type, properties, source_address)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                relationship.relationship_id,
                relationship.source_node_id,
                relationship.target_node_id,
                relationship.relationship_type,
                json.dumps(relationship.properties),
                relationship.source_address
            ))

    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get knowledge graph statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Count nodes by type
            cursor.execute("""
                SELECT node_type, COUNT(*) as count FROM graph_nodes GROUP BY node_type
            """)
            nodes_by_type = {row['node_type']: row['count'] for row in cursor.fetchall()}

            # Total nodes and relationships
            cursor.execute("SELECT COUNT(*) as total FROM graph_nodes")
            total_nodes = cursor.fetchone()['total'] or 0

            cursor.execute("SELECT COUNT(*) as total FROM graph_relationships")
            total_relationships = cursor.fetchone()['total'] or 0

            # Relationships by type
            cursor.execute("""
                SELECT relationship_type, COUNT(*) as count FROM graph_relationships GROUP BY relationship_type
            """)
            relationships_by_type = {row['relationship_type']: row['count'] for row in cursor.fetchall()}

            return {
                'total_nodes': total_nodes,
                'total_relationships': total_relationships,
                'nodes_by_type': nodes_by_type,
                'relationships_by_type': relationships_by_type
            }
