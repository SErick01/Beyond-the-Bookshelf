from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from .security import get_current_user
import os
import json
import urllib.request
import urllib.parse
import urllib.error
import datetime as dt

router = APIRouter(prefix="/api/home", tags=["home"],)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

class CurrentRead(BaseModel):
    work_id: str
    edition_id: str | None = None
    title: str
    author: str | None = None
    cover_url: str | None = None
    page_count: int | None = None
    progress_percent: float = 0.0

class ShelfCreate(BaseModel):
    name: str
    visibility: str = "private"
    is_default: bool = False

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


@router.get("/favorites")
async def get_favorites(
    limit: int = Query(21, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    headers = supabase_headers()

    shelf_params = {
        "select": "shelf_id",
        "user_id": f"eq.{user['id']}",
        "name": "eq.favorites",
        "limit": "1",
    }
    shelf_url = f"{SUPABASE_URL}/rest/v1/shelves?{urllib.parse.urlencode(shelf_params)}"

    try:
        s_req = urllib.request.Request(shelf_url, headers=headers, method="GET")
        with urllib.request.urlopen(s_req, timeout=10) as s_resp:
            s_body = s_resp.read().decode("utf-8")
        shelf_rows = json.loads(s_body)
    
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print("[home.favorites] shelves HTTPError", e.code, body)
        raise HTTPException(
            status_code=500,
            detail=f"Supabase error while reading shelves ({e.code}): {body}",
        )
    
    except Exception as e:
        print("[home.favorites] shelves error:", repr(e))
        raise HTTPException(status_code=500, detail="Failed to load favorites shelf")

    if not shelf_rows:
        return []

    shelf_id = shelf_rows[0].get("shelf_id")
    if shelf_id is None:
        return []

    si_params = {
        "select": "work_id,added_at",
        "shelf_id": f"eq.{shelf_id}",
        "order": "added_at.desc",
        "limit": str(limit),
    }
    si_url = f"{SUPABASE_URL}/rest/v1/shelf_items?{urllib.parse.urlencode(si_params)}"

    try:
        si_req = urllib.request.Request(si_url, headers=headers, method="GET")
        with urllib.request.urlopen(si_req, timeout=10) as si_resp:
            si_body = si_resp.read().decode("utf-8")
        si_rows = json.loads(si_body)
    
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print("[home.favorites] shelf_items HTTPError", e.code, body)
        raise HTTPException(
            status_code=500,
            detail=f"Supabase error while reading shelf_items ({e.code}): {body}",
        )
    
    except Exception as e:
        print("[home.favorites] shelf_items error:", repr(e))
        raise HTTPException(status_code=500, detail="Failed to load favorites")

    if not si_rows:
        return []

    work_ids: List[str] = []
    shelf_order: Dict[str, int] = {}

    for idx, row in enumerate(si_rows):
        wid = row.get("work_id")
        if not wid:
            continue
        
        wid_str = str(wid)
        if wid_str not in shelf_order:
            shelf_order[wid_str] = idx
            work_ids.append(wid_str)

    if not work_ids:
        return []

    ed_params = {
        "select": "edition_id,work_id,cover_url,works!inner(title)",
        "work_id": f"in.({','.join(work_ids)})",
        "order": "pub_date.desc",
    }
    ed_url = f"{SUPABASE_URL}/rest/v1/editions?{urllib.parse.urlencode(ed_params)}"

    try:
        ed_req = urllib.request.Request(ed_url, headers=headers, method="GET")
        with urllib.request.urlopen(ed_req, timeout=10) as ed_resp:
            ed_body = ed_resp.read().decode("utf-8")
        ed_rows = json.loads(ed_body)
    
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print("[home.favorites] editions HTTPError", e.code, body)
        raise HTTPException(
            status_code=500,
            detail=f"Supabase error while reading editions ({e.code}): {body}",
        )
    
    except Exception as e:
        print("[home.favorites] editions error:", repr(e))
        raise HTTPException(status_code=500, detail="Failed to load favorite books")

    if not ed_rows:
        return [
            {
                "work_id": wid,
                "edition_id": None,
                "title": f"Work {wid}",
                "cover_url": None,
            }
            for wid in work_ids
        ][:limit]

    favorites: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for row in ed_rows:
        wid = row.get("work_id")
        if not wid:
            continue
        
        wid_str = str(wid)
        if wid_str in seen:
            continue
        seen.add(wid_str)

        title = (row.get("works") or {}).get("title") or f"Work {wid_str}"
        favorites.append(
            {
                "work_id": wid_str,
                "edition_id": row.get("edition_id"),
                "title": title,
                "cover_url": row.get("cover_url"),
            }
        )
    favorites.sort(key=lambda r: shelf_order.get(str(r["work_id"]), 0))
    return favorites[:limit]


@router.get("/current-reads", response_model=List[CurrentRead])
async def get_current_reads(
    limit: int = 2,
    user: dict = Depends(get_current_user),
) -> List[CurrentRead]:
    
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    headers = supabase_headers()
    base_url = f"{SUPABASE_URL}/rest/v1/reading_progress"
    params = {
        "select": "work_id,page_count,progress_percent,updated_at",
        "user_id": f"eq.{user['id']}",
        "order": "updated_at.desc",
        "limit": str(limit),
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        progress_rows = json.loads(body)
    
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        print("[home.current_reads] Supabase HTTPError", e.code, error_body)
        raise HTTPException(
            status_code=500,
            detail=f"Supabase error while reading progress ({e.code}): {error_body}",
        )
    
    except Exception as e:
        print("[home.current_reads] Unexpected error fetching reading_progress:", repr(e))
        raise HTTPException(status_code=500, detail="Failed to fetch reading progress")

    if not progress_rows:
        return _stub_current_reads(limit)

    current_reads: List[CurrentRead] = []
    for row in progress_rows:
        work_id = row.get("work_id")
        
        if not work_id:
            continue
        work_id_str = str(work_id)

        page_count = row.get("page_count")
        progress_percent = row.get("progress_percent")
        if progress_percent is not None:
            progress_percent = max(0.0, min(100.0, float(progress_percent)))
        else:
            progress_percent = 0.0

        title: str = f"Work {work_id_str}"
        author: Optional[str] = "Unknown author"
        cover_url: Optional[str] = None
        edition_id: Optional[int] = None

        try:
            ed_base = f"{SUPABASE_URL}/rest/v1/editions"
            ed_params = {
                "select": "edition_id,page_count,cover_url,author",
                "work_id": f"eq.{work_id_str}",
                "order": "pub_date.desc",
                "limit": "1",
            }

            ed_url = f"{ed_base}?{urllib.parse.urlencode(ed_params)}"
            ed_req = urllib.request.Request(ed_url, headers=headers, method="GET")
            
            with urllib.request.urlopen(ed_req, timeout=10) as ed_resp:
                ed_body = ed_resp.read().decode("utf-8")
            ed_rows = json.loads(ed_body)

            if ed_rows:
                ed = ed_rows[0]
                edition_id = ed.get("edition_id") or edition_id
                cover_url = ed.get("cover_url") or cover_url
                
                if not page_count:
                    page_count = ed.get("page_count")
                author = ed.get("author") or author
        
        except Exception as e:
            print("[home.current_reads] Warning: editions fetch failed:", repr(e))

        try:
            w_base = f"{SUPABASE_URL}/rest/v1/works"
            w_params = {
                "select": "title",
                "work_id": f"eq.{work_id_str}",
                "limit": "1",
            }

            w_url = f"{w_base}?{urllib.parse.urlencode(w_params)}"
            w_req = urllib.request.Request(w_url, headers=headers, method="GET")
            
            with urllib.request.urlopen(w_req, timeout=10) as w_resp:
                w_body = w_resp.read().decode("utf-8")
            w_rows = json.loads(w_body)

            if w_rows:
                title = w_rows[0].get("title") or title
        
        except Exception as e:
            print("[home.current_reads] Warning: works fetch failed:", repr(e))

        current_reads.append(
            CurrentRead(
                work_id=work_id,
                edition_id=edition_id,
                title=title,
                author=author,
                cover_url=cover_url,
                page_count=page_count,
                progress_percent=progress_percent,
            )
        )

    if not current_reads:
        return _stub_current_reads(limit)
    return current_reads

@router.get("/shelves")
async def get_shelves(
    limit: int = Query(100, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    headers = supabase_headers()
    params = {
        "select": "shelf_id,name,is_default,visibility",
        "user_id": f"eq.{user['id']}",
        "order": "is_default.desc,name.asc",
        "limit": str(limit),
    }
    url = f"{SUPABASE_URL}/rest/v1/shelves?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        shelf_rows = json.loads(body)
    
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        print("[home.shelves] shelves HTTPError", e.code, error_body)
        raise HTTPException(
            status_code=500,
            detail=f"Supabase error while reading shelves ({e.code}): {error_body}",
        )
    
    except Exception as e:
        print("[home.shelves] shelves error:", repr(e))
        raise HTTPException(status_code=500, detail="Failed to load shelves")

    if not shelf_rows:
        return []

    shelf_ids = [
        str(row["shelf_id"])
        for row in shelf_rows
        if row.get("shelf_id") is not None
    ]

    counts_by_id: Dict[str, int] = {}
    if shelf_ids:
        si_params = {
            "select": "shelf_id",
            "shelf_id": f"in.({','.join(shelf_ids)})",
            "limit": "10000",
        }
        si_url = f"{SUPABASE_URL}/rest/v1/shelf_items?{urllib.parse.urlencode(si_params)}"

        try:
            si_req = urllib.request.Request(si_url, headers=headers, method="GET")
            with urllib.request.urlopen(si_req, timeout=10) as si_resp:
                si_body = si_resp.read().decode("utf-8")
            si_rows = json.loads(si_body)

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            print("[home.shelves] shelf_items HTTPError", e.code, body)
            si_rows = []

        except Exception as e:
            print("[home.shelves] shelf_items error:", repr(e))
            print("[home.shelves] falling back to zero counts")
            si_rows = []

        for row in si_rows:
            sid = row.get("shelf_id")
            if sid is None:
                continue
            sid_str = str(sid)
            counts_by_id[sid_str] = counts_by_id.get(sid_str, 0) + 1

    result = []
    for row in shelf_rows:
        sid = row.get("shelf_id")
        if sid is None:
            continue
        sid_str = str(sid)
        
        result.append(
            {
                "shelf_id": sid,
                "name": row.get("name"),
                "visibility": row.get("visibility"),
                "is_default": row.get("is_default", False),
                "book_count": counts_by_id.get(sid_str, 0),
            }
        )
    return result

@router.post("/shelves")
async def create_shelf(
    payload: ShelfCreate,
    user: dict = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    headers = supabase_headers()
    headers["Prefer"] = "return=representation"
    supabase_row = {
        "user_id": user["id"],
        "name": name,
        "visibility": payload.visibility,
        "is_default": payload.is_default,
    }
    url = f"{SUPABASE_URL}/rest/v1/shelves"
    data = json.dumps(supabase_row).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        rows = json.loads(body)
        row = rows[0] if isinstance(rows, list) and rows else rows

        return {
            "shelf_id": row.get("shelf_id"),
            "name": row.get("name"),
            "visibility": row.get("visibility"),
            "is_default": row.get("is_default", False),
            "book_count": 0,
        }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        print("[home.shelves] create HTTPError", e.code, error_body)
        
        if e.code == 409:
            raise HTTPException(
                status_code=400,
                detail="You already have a list with that name.",
            )
        
        raise HTTPException(
            status_code=500,
            detail=f"Supabase error while creating shelf ({e.code}): {error_body}",
        )
    
    except Exception as e:
        print("[home.shelves] create error:", repr(e))
        raise HTTPException(status_code=500, detail="Failed to create shelf")

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
        "page_count": page_count,
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
