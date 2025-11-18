from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/home",
    tags=["home"],
)

class CurrentRead(BaseModel):
    work_id: int
    edition_id: Optional[int] = None
    title: str
    author: Optional[str] = None
    cover_url: Optional[str] = None
    page_count: Optional[int] = None
    progress_percent: float

@router.get("/current-reads", response_model=List[CurrentRead])
async def get_current_reads(limit: int = 2):
    sample_books = [
        CurrentRead(
            work_id=1, edition_id=101,
            title="Stub Book One",
            author="Demo Author",
            cover_url=None,
            page_count=400,
            progress_percent=30.0,
        ),
        CurrentRead(
            work_id=2,
            edition_id=202,
            title="Stub Book Two",
            author="Another Author",
            cover_url=None,
            page_count=250,
            progress_percent=60.0,
        ),
    ]
    return sample_books[:limit]

class ProgressUpdate(BaseModel):
    work_id: str
    pages_read: int
    page_count: int

@router.post("/progress")
async def update_progress(payload: ProgressUpdate):
    return {"status": "ok"}
