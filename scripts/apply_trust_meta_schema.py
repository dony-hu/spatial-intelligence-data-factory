import os
import sys
from sqlalchemy import create_engine, text

def main():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    engine = create_engine(db_url)
    
    schema_sql_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'trust_meta_schema.sql')
    
    with open(schema_sql_path, 'r') as f:
        schema_sql = f.read()
    
    with engine.begin() as conn:
        conn.execute(text(schema_sql))
        print("Successfully applied trust_meta schema")

if __name__ == '__main__':
    main()
