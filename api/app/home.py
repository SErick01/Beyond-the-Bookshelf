from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from app.security import get_current_user
import os
import json
import urllib.request
import urllib.parse
import urllib.error
import datetime as dt

router = APIRouter(
    prefix="/api/home",
    tags=["home"],
)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://swfkspdirzdqotywgvop.supabase.co",)
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

class CurrentRead(BaseModel):
    work_id: str
    edition_id: str | None = None
    title: str
    author: str | None = None
    cover_url: str | None = None
    page_count: int | None = None
    progress_percent: float = 0.0

def compute_progress_percent(current_page: int, page_count: Optional[int]) -> float:
    if not page_count or page_count <= 0:
        return 0.0

    pct = (current_page / page_count) * 100.0
    if pct < 0:
        pct = 0.0
    if pct > 100:
        pct = 100.0

    return round(pct, 1)

def _stub_current_reads(limit: int) -> List[CurrentRead]:
    sample_books = [
        CurrentRead(
            work_id="stub-1",
            edition_id="stub-ed-1",
            title="Stub Book One",
            author="Demo Author",
            cover_url=None,
            page_count=400,
            progress_percent=30,
        ),
        CurrentRead(
            work_id="stub-2",
            edition_id="stub-ed-2",
            title="Stub Book Two",
            author="Another Author",
            cover_url=None,
            page_count=250,
            progress_percent=60,
        ),
    ]
    return sample_books[:limit]

@router.get("/current-reads", response_model=List[CurrentRead])
async def get_current_reads(
    limit: int = 2,
    user: dict = Depends(get_current_user),
) -> List[CurrentRead]:

    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    return _stub_current_reads(limit)

class ProgressUpdate(BaseModel):
    work_id: str
    current_page: int
    page_count: int
    progress_percent: Optional[float] = None

@router.post("/progress")
async def update_progress(
    payload: ProgressUpdate,
    user: dict = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    if not payload.work_id:
        raise HTTPException(status_code=400, detail="work_id is required")

    current_page = payload.current_page
    page_count = payload.page_count
    progress_percent = payload.progress_percent

    if progress_percent is None and current_page is not None and page_count:
        progress_percent = (current_page / page_count) * 100

    if progress_percent is not None:
        progress_percent = max(0.0, min(100.0, float(progress_percent)))
        progress_percent = int(round(progress_percent))

    supabase_row = {
        "user_id": user["id"],
        "work_id": payload.work_id,
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }

    if progress_percent is not None:
        supabase_row["progress_percent"] = progress_percent

    base_url = f"{SUPABASE_URL}/rest/v1/reading_progress"
    query = urllib.parse.urlencode({"on_conflict": "user_id,work_id"})
    url = f"{base_url}?{query}"

    data = json.dumps(supabase_row).encode("utf-8")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            print("[home.progress] Supabase OK:", resp.status, body)

        return {"status": "ok", "saved": True,
            "progress_percent": progress_percent,}

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        print("[home.progress] Supabase HTTPError:", e.code, error_body)
        return {"status": "error", "saved": False,
            "detail": f"Supabase {e.code}: {error_body}",}

    except Exception as e:
        print("[home.progress] Unexpected error:", repr(e))
        return {"status": "error", "saved": False, "detail": str(e),}
