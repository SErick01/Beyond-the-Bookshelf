from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body
from pydantic import BaseModel
import os
import json
import urllib.request
import urllib.parse

router = APIRouter(
    prefix="/api/home",
    tags=["home"],
)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://swfkspdirzdqotywgvop.supabase.co",)
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

class CurrentRead(BaseModel):
    work_id: int
    edition_id: Optional[int] = None
    title: str
    author: Optional[str] = None
    cover_url: Optional[str] = None
    page_count: Optional[int] = None
    progress_percent: float

def _stub_current_reads(limit: int) -> List[CurrentRead]:
    sample_books = [
        CurrentRead(
            work_id=1,
            edition_id=None,
            title="Stub Book One",
            author="Demo Author",
            cover_url=None,
            page_count=400,
            progress_percent=30.0,
        ),
        CurrentRead(
            work_id=2,
            edition_id=None,
            title="Stub Book Two",
            author="Another Author",
            cover_url=None,
            page_count=250,
            progress_percent=60.0,
        ),
    ]
    return sample_books[:limit]

@router.get("/current-reads", response_model=List[CurrentRead])
async def get_current_reads(limit: int = 2) -> List[CurrentRead]:
    if not SUPABASE_KEY:
        return _stub_current_reads(limit)

    try:
        base = SUPABASE_URL.rstrip("/")
        url = f"{base}/rest/v1/editions"

        params = {
            "select": "edition_id,work_id,page_count,cover_url,works!inner(title)",
            "order": "pub_date.desc",
            "limit": str(limit),
        }

        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",}
        req = urllib.request.Request(full_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            rows = json.loads(resp.read().decode("utf-8"))

        books: List[CurrentRead] = []
        for row in rows:
            works = row.get("works") or {}
            title = works.get("title") or "Unknown title"

            books.append(
                CurrentRead(
                    work_id=row["work_id"],
                    edition_id=row.get("edition_id"),
                    title=title,
                    author=None,
                    cover_url=row.get("cover_url"),
                    page_count=row.get("page_count"),
                    progress_percent=30.0,
                )
            )
        return books or _stub_current_reads(limit)
    except Exception as exc:
        return _stub_current_reads(limit)

@router.post("/progress")
async def update_progress(payload: Dict[str, Any] = Body(...)):
    return {"status": "ok"}
