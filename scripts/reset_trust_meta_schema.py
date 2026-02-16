import os
import sys
from sqlalchemy import create_engine, text

def main():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    engine = create_engine(db_url)
    
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS trust_meta CASCADE"))
        conn.execute(text("DROP SCHEMA IF EXISTS trust_db CASCADE"))
        print("Dropped existing schemas")
    
    schema_sql_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'trust_meta_schema.sql')
    
    with open(schema_sql_path, 'r') as f:
        schema_sql = f.read()
    
    with engine.begin() as conn:
        conn.execute(text(schema_sql))
        print("Successfully applied trust_meta schema")

if __name__ == '__main__':
    main()
