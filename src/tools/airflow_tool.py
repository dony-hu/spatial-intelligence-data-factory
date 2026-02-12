from pathlib import Path
from typing import Dict


class AirflowTool:
    """Generate a minimal Airflow DAG artifact for inspection/review."""

    def generate_dag(self, dag_id: str, schedule: str, output_dir: str) -> Dict:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{dag_id}.py"

        content = f'''from airflow import DAG
from airflow.operators.empty import EmptyOperator
from datetime import datetime

with DAG(
    dag_id="{dag_id}",
    start_date=datetime(2025, 1, 1),
    schedule="{schedule}",
    catchup=False,
    tags=["agent-demo"],
) as dag:
    start = EmptyOperator(task_id="start")
    done = EmptyOperator(task_id="done")
    start >> done
'''
        path.write_text(content, encoding="utf-8")
        return {"pass": True, "artifact": str(path)}
