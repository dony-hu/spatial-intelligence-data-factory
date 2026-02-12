"""厂长服务。"""

from typing import Any, Dict

from tools.factory_agents import FactoryDirector
from tools.factory_framework import FactoryState


class DirectorService:
    """厂长服务：工厂汇总状态。"""

    def __init__(self, factory_state: FactoryState, director: FactoryDirector):
        self.factory_state = factory_state
        self.director = director

    def get_factory_status(self) -> Dict[str, Any]:
        return self.director.execute(self.factory_state, {"action": "status"})
