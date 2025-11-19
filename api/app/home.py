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
    edition_id: Optional[str] = None
    title: str
    author: Optional[str] = None
    cover_url: Optional[str] = None
    page_count: Optional[int] = None
    progress_percent: float

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
    except Exception:
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

    if progress_percent is None:
        progress_percent = compute_progress_percent(current_page, page_count)

    if progress_percent is not None:
        progress_percent = max(0.0, min(100.0, float(progress_percent)))

    supabase_row = {
        "user_id": user["id"], "work_id": payload.work_id,
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),}
    
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
