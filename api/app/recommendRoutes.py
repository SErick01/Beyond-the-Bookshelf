from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from .security import get_current_user
from .recommendML.service import (recommend_for_user, recommend_similar_works,)

router = APIRouter(prefix="/api/recommend", tags=["recommendations"])

class WorkOut(BaseModel):
    work_id: int
    title: str
    publish_year: int | None = None
    authors: list[str] = []
    cover_url: str | None = None
    page_count: int | None = None
    summary: str | None = None


@router.get("/user", response_model=List[WorkOut])
def recommend_for_logged_in_user(
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = current_user["id"]
    return recommend_for_user(user_id=user_id, limit=limit)


@router.get("/similar/{work_id}", response_model=List[WorkOut])
def similar_works(work_id: int, limit: int = 10):
    return recommend_similar_works(work_id=work_id, limit=limit)
