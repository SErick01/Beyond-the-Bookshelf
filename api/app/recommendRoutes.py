from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from .recommendML.service import (recommend_for_user, recommend_newest_works)

router = APIRouter(prefix="/api/recommend", tags=["recommendations"])

class WorkOut(BaseModel):
    work_id: str
    title: str
    publish_year: int | None = None
    authors: list[str] = []
    cover_url: str | None = None
    page_count: int | None = None
    summary: str | None = None


@router.get("/user", response_model=List[WorkOut])
def recommend_for_user_public(limit: int = 10):
    demo_user_id = "1"
    return recommend_for_user(user_id=demo_user_id, limit=limit)


@router.get("/newest", response_model=List[WorkOut])
def recommend_newest(limit: int = 10):
    return recommend_newest_works(limit = limit)
