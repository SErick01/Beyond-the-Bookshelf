from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from app.security import get_current_user
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

@router.post("/progress")
async def update_progress(
    payload: Dict[str, Any] = Body(...),
    user: Dict[str, Any] = Depends(get_current_user),
):
    if not SUPABASE_KEY:
        return {"status": "ok", "saved": False}

    work_id = payload.get("work_id")
    if not work_id:
        raise HTTPException(status_code=400, detail="work_id is required")

    current_page = (
        payload.get("current_page")
        or payload.get("page")
        or payload.get("pages_read")
    )

    if current_page is None:
        raise HTTPException(status_code=400, detail="current_page is required")

    page_count = payload.get("page_count")

    try:
        current_page = int(current_page)
    except Exception as e:
        print("[home.progress] error:", repr(e))
        return {"status": "error", "saved": False, "detail": str(e),}

    if "progress_percent" in payload and payload["progress_percent"] is not None:
        try:
            progress_percent = float(payload["progress_percent"])
        except (TypeError, ValueError):
            progress_percent = compute_progress_percent(current_page, page_count)
    else:
        progress_percent = compute_progress_percent(current_page, page_count)

    if isinstance(user, dict):
        user_id = user.get("id") or user.get("user_id")
    else:
        user_id = getattr(user, "id", None) or getattr(user, "user_id", None)

    if not user_id:
        raise HTTPException(status_code=401, detail="Could not determine user id")

    user_id = str(user_id)
    work_id = str(work_id)

    base = SUPABASE_URL.rstrip("/")
    url = f"{base}/rest/v1/reading_progress?on_conflict=user_id,work_id"

    row = {
        "user_id": user_id,
        "work_id": work_id,
        "progress_percent": progress_percent,
    }

    data = json.dumps(row).encode("utf-8")
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        return {"status": "ok", "saved": True, "progress_percent": progress_percent,}

    except Exception as e:
        print("[home.progress] error:", repr(e))
        return {"status": "error", "saved": False, "detail": str(e),}
