from fastapi import FastAPI

from services.governance_api.app.routers import ops, reviews, rulesets, tasks


def create_app() -> FastAPI:
    app = FastAPI(title="Governance API", version="0.1.0")
    app.include_router(tasks.router, prefix="/v1/governance", tags=["tasks"])
    app.include_router(reviews.router, prefix="/v1/governance", tags=["reviews"])
    app.include_router(rulesets.router, prefix="/v1/governance", tags=["rulesets"])
    app.include_router(ops.router, prefix="/v1/governance", tags=["ops"])
    return app


app = create_app()
