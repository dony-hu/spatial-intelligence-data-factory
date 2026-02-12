"""组长服务。"""

from typing import Any, Dict

from database.factory_db import FactoryDB
from tools.factory_agents import ProductionLineLeader, Worker
from tools.factory_framework import FactoryState, ProcessSpec, ProductionLine


class ProductionLineLeaderService:
    """组长服务：产线创建、工人登记、产线状态。"""

    def __init__(
        self,
        factory_state: FactoryState,
        db: FactoryDB,
        leader: ProductionLineLeader,
        workers: Dict[str, Worker],
    ):
        self.factory_state = factory_state
        self.db = db
        self.leader = leader
        self.workers = workers

    def create_line(self, process_spec: ProcessSpec, line_name: str, line_id: str, worker_count: int = 2) -> ProductionLine:
        line = self.leader.execute(
            self.factory_state,
            {
                "action": "create",
                "process_spec": process_spec,
                "worker_count": worker_count,
                "line_name": line_name,
            },
        )["production_line"]
        line.line_id = line_id
        self.factory_state.add_production_line(line)
        self.db.save_production_line(line)

        for worker in line.workers:
            self.workers[worker.worker_id] = Worker(worker.worker_id)

        return line

    def get_line_status(self, line_id: str) -> Dict[str, Any]:
        line = self.factory_state.get_production_line(line_id)
        if not line:
            return {"error": "Production line not found"}
        progress = self.leader.execute(
            self.factory_state,
            {
                "action": "monitor",
                "production_line": line,
            },
        )
        return progress["progress"]
