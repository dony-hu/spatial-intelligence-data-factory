"""兼容层：角色服务已拆分到 tools.factory_roles 包。"""

from tools.factory_roles import (  # noqa: F401
    DirectorService,
    ProcessExpertService,
    ProductionLineLeaderService,
    WorkerExecutionService,
)
