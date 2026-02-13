"""
持久化工具模板
"""

from typing import Dict, Any


def generate_db_persister(domain: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """生成数据库持久化工具"""

    code = f'''"""
数据库持久化器 - 自动生成
Domain: {domain}
参数: {parameters}
"""

import sqlite3
import json
from typing import List, Dict, Any


class DBPersister:
    """数据库持久化器"""

    def __init__(self, db_path: str = None, **config):
        self.db_path = db_path or config.get('db_path', 'process_results.db')
        self.table_name = config.get('table_name', 'process_results')
        self.batch_size = config.get('batch_size', 1000)

    def persist(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        持久化数据到数据库

        Args:
            records: 数据记录列表

        Returns:
            {{
                'success': bool,
                'inserted': int,
                'failed': int,
                'errors': list
            }}
        """

        inserted = 0
        failed = 0
        errors = []

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 创建表（如果不存在）
            self._create_table(cursor)

            # 批量插入
            for i in range(0, len(records), self.batch_size):
                batch = records[i:i+self.batch_size]
                try:
                    for record in batch:
                        self._insert_record(cursor, record)
                    conn.commit()
                    inserted += len(batch)
                except Exception as e:
                    errors.append(f'批次 {{i//self.batch_size}} 插入失败: {{str(e)}}')
                    failed += len(batch)

            conn.close()

        except Exception as e:
            errors.append(f'数据库操作错误: {{str(e)}}')
            return {{'success': False, 'inserted': 0, 'failed': len(records), 'errors': errors}}

        return {{
            'success': failed == 0,
            'inserted': inserted,
            'failed': failed,
            'errors': errors
        }}

    def _create_table(self, cursor):
        """创建表"""
        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        cursor.execute(create_sql)

    def _insert_record(self, cursor, record):
        """插入单条记录"""
        data_json = json.dumps(record, ensure_ascii=False)
        insert_sql = f"INSERT INTO {self.table_name} (data) VALUES (?)"
        cursor.execute(insert_sql, (data_json,))


def persist_to_db(records: List[Dict[str, Any]], **config) -> Dict[str, Any]:
    """快速持久化函数"""
    persister = DBPersister(**config)
    return persister.persist(records)
'''

    return {
        'status': 'generated',
        'tool_name': 'db_persister',
        'code': code,
        'message': '持久化工具已生成'
    }
