from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from services.governance_api.app.routers import lab, manual_review, observability, ops, reviews, rulesets, tasks


def create_app() -> FastAPI:
    app = FastAPI(title="Governance API", version="0.1.0")
    project_root = Path(__file__).resolve().parents[3]
    output_dir = project_root / "output"
    if output_dir.exists():
        app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")
    app.include_router(tasks.router, prefix="/v1/governance", tags=["tasks"])
    app.include_router(reviews.router, prefix="/v1/governance", tags=["reviews"])
    app.include_router(rulesets.router, prefix="/v1/governance", tags=["rulesets"])
    app.include_router(ops.router, prefix="/v1/governance", tags=["ops"])
    app.include_router(observability.router, prefix="/v1/governance", tags=["observability"])
    app.include_router(lab.router, prefix="/v1/governance", tags=["lab"])
    app.include_router(manual_review.router, prefix="/v1/governance", tags=["manual-review"])
    return app


app = create_app()
