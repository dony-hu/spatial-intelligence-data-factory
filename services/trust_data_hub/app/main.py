from __future__ import annotations

from fastapi import FastAPI

from services.trust_data_hub.app.routers import admin, ops, query, validation


def create_app() -> FastAPI:
    app = FastAPI(title="Trust Data Hub API", version="0.1.0")
    app.include_router(admin.router, prefix="/v1/trust/admin", tags=["trust-admin"])
    app.include_router(ops.router, prefix="/v1/trust/ops", tags=["trust-ops"])
    app.include_router(query.router, prefix="/v1/trust/query", tags=["trust-query"])
    app.include_router(validation.router, prefix="/v1/trust/validation", tags=["trust-validation"])
    return app


app = create_app()
