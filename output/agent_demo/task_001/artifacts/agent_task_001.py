from airflow import DAG
from airflow.operators.empty import EmptyOperator
from datetime import datetime

with DAG(
    dag_id="agent_task_001",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["agent-demo"],
) as dag:
    start = EmptyOperator(task_id="start")
    done = EmptyOperator(task_id="done")
    start >> done
