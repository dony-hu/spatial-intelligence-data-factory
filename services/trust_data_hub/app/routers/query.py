from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from services.trust_data_hub.app.repositories.trust_repository import trust_repository

router = APIRouter()


@router.get("/namespaces/{namespace}/admin-division")
def query_admin_division(namespace: str, name: str = Query(...), parent_hint: Optional[str] = Query(default=None)) -> dict:
    return {"candidates": trust_repository.query_admin_division(namespace, name, parent_hint)}


@router.get("/namespaces/{namespace}/road")
def query_road(namespace: str, name: str = Query(...), adcode_hint: Optional[str] = Query(default=None)) -> dict:
    return {"candidates": trust_repository.query_road(namespace, name, adcode_hint)}


@router.get("/namespaces/{namespace}/poi")
def query_poi(
    namespace: str,
    name: str = Query(...),
    adcode_hint: Optional[str] = Query(default=None),
    top_k: int = Query(default=5),
) -> dict:
    return {"candidates": trust_repository.query_poi(namespace, name, adcode_hint, top_k)}
