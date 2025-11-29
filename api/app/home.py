from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from .security import get_current_user
import os
import json
import urllib.request
import urllib.parse
import urllib.error

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

def normalize_cover_url(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if raw.startswith("cover/"):
        return raw
    return None

class ShelfCreate(BaseModel):
    name: str
    visibility: str = "private"
    is_default: bool = False


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


@router.get("/shelves/{shelf_id}/items")
async def get_shelf_items(
    shelf_id: str,
    limit: int = Query(100, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    headers = supabase_headers()
    
    shelf_params = {
        "select": "shelf_id,name",
        "shelf_id": f"eq.{shelf_id}",
        "user_id": f"eq.{user['id']}",
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
        print("[home.shelf_items] shelves HTTPError", e.code, body)
        raise HTTPException(
            status_code=500,
            detail=f"Supabase error while reading shelves ({e.code}): {body}",
        )
    
    except Exception as e:
        print("[home.shelf_items] shelves error:", repr(e))
        raise HTTPException(status_code=500, detail="Failed to load shelf")

    if not shelf_rows:
        raise HTTPException(status_code=404, detail="Shelf not found")

    shelf_row = shelf_rows[0]
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
        print("[home.shelf_items] shelf_items HTTPError", e.code, body)
        raise HTTPException(
            status_code=500,
            detail=f"Supabase error while reading shelf_items ({e.code}): {body}",
        )
    
    except Exception as e:
        print("[home.shelf_items] shelf_items error:", repr(e))
        raise HTTPException(status_code=500, detail="Failed to load list items")

    if not si_rows:
        return {
            "shelf_id": shelf_id,
            "name": shelf_row.get("name"),
            "items": [],
        }
    work_ids: list[str] = []
    shelf_order: dict[str, int] = {}

    for idx, row in enumerate(si_rows):
        wid = row.get("work_id")

        if not wid:
            continue
        wid_str = str(wid)

        if wid_str not in shelf_order:
            shelf_order[wid_str] = idx
            work_ids.append(wid_str)

    if not work_ids:
        return {
            "shelf_id": shelf_id,
            "name": shelf_row.get("name"),
            "items": [],
        }

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
        print("[home.shelf_items] editions HTTPError", e.code, body)
        raise HTTPException(
            status_code=500,
            detail=f"Supabase error while reading editions ({e.code}): {body}",
        )
    
    except Exception as e:
        print("[home.shelf_items] editions error:", repr(e))
        raise HTTPException(status_code=500, detail="Failed to load books for this list")

    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    if not ed_rows:
        for wid in work_ids:
            items.append(
                {
                    "work_id": wid,
                    "edition_id": None,
                    "title": f"Work {wid}",
                    "cover_url": None,
                }
            )
    else:
        for row in ed_rows:
            wid = row.get("work_id")
            if not wid:
                continue
            wid_str = str(wid)
            if wid_str in seen:
                continue
            seen.add(wid_str)

            title = (row.get("works") or {}).get("title") or f"Work {wid_str}"
            items.append(
                {
                    "work_id": wid_str,
                    "edition_id": row.get("edition_id"),
                    "title": title,
                    "cover_url": row.get("cover_url"),
                }
            )
    items.sort(key=lambda r: shelf_order.get(str(r["work_id"]), 0))

    return {
        "shelf_id": shelf_id,
        "name": shelf_row.get("name"),
        "items": items,
    }


@router.get("/shelves")
async def get_shelves(
    limit: int = Query(100, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    headers = supabase_headers()
    shelf_params = {
        "select": "shelf_id,name,is_default,visibility",
        "user_id": f"eq.{user['id']}",
        "order": "is_default.desc,name.asc",
        "limit": str(limit),
    }
    shelf_url = f"{SUPABASE_URL}/rest/v1/shelves?{urllib.parse.urlencode(shelf_params)}"

    try:
        s_req = urllib.request.Request(shelf_url, headers=headers, method="GET")
        with urllib.request.urlopen(s_req, timeout=10) as s_resp:
            s_body = s_resp.read().decode("utf-8")
        shelf_rows = json.loads(s_body)
    
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print("[home.shelves] shelves HTTPError", e.code, body)
        raise HTTPException(
            status_code=500,
            detail=f"Supabase error while reading shelves ({e.code}): {body}",
        )
    
    except Exception as e:
        print("[home.shelves] shelves error:", repr(e))
        raise HTTPException(status_code=500, detail="Failed to load shelves")

    if not shelf_rows:
        return []

    shelf_ids: List[str] = []
    for row in shelf_rows:
        sid = row.get("shelf_id")
        if sid is None:
            continue
        shelf_ids.append(str(sid))

    counts_by_id: Dict[str, int] = {}
    sample_work_by_shelf: Dict[str, str] = {}

    if shelf_ids:
        si_params = {
            "select": "shelf_id,work_id,added_at",
            "shelf_id": f"in.({','.join(shelf_ids)})",
            "order": "added_at.desc",
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
            si_rows = []

        for row in si_rows:
            sid = row.get("shelf_id")
            wid = row.get("work_id")
            
            if sid is None or wid is None:
                continue

            sid_str = str(sid)
            wid_str = str(wid)
            counts_by_id[sid_str] = counts_by_id.get(sid_str, 0) + 1

            if sid_str not in sample_work_by_shelf:
                sample_work_by_shelf[sid_str] = wid_str

    cover_by_work: Dict[str, Optional[str]] = {}
    sample_work_ids = list({wid for wid in sample_work_by_shelf.values() if wid})

    if sample_work_ids:
        ed_params = {
            "select": "work_id,cover_url,pub_date",
            "work_id": f"in.({','.join(sample_work_ids)})",
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
            print("[home.shelves] editions HTTPError", e.code, body)
            ed_rows = []
        
        except Exception as e:
            print("[home.shelves] editions error:", repr(e))
            ed_rows = []

        for row in ed_rows:
            wid = row.get("work_id")
            if wid is None:
                continue
            wid_str = str(wid)

            if wid_str in cover_by_work:
                continue

            raw_cover = row.get("cover_url")
            cover = normalize_cover_url(raw_cover)

            if cover:
                cover_by_work[wid_str] = cover

    result: List[Dict[str, Any]] = []
    for row in shelf_rows:
        sid = row.get("shelf_id")
        
        if sid is None:
            continue
        
        sid_str = str(sid)
        sample_wid = sample_work_by_shelf.get(sid_str)
        cover_url = cover_by_work.get(sample_wid) if sample_wid else None

        result.append(
            {
                "shelf_id": sid,
                "name": row.get("name"),
                "visibility": row.get("visibility"),
                "is_default": row.get("is_default", False),
                "book_count": counts_by_id.get(sid_str, 0),
                "cover_url": cover_url,
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


def count_user_rows(table: str, user_id: str, headers: Dict[str, str]) -> int:
    params = {
        "select": "work_id",
        "user_id": f"eq.{user_id}",
        "limit": "10000",
    }
    url = f"{SUPABASE_URL}/rest/v1/{table}?{urllib.parse.urlencode(params)}"
    
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        rows = json.loads(body)
        return len(rows)
    
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"[home.list_summary] HTTPError while counting {table}", e.code, body)
        return 0
    
    except Exception as e:
        print(f"[home.list_summary] error while counting {table}:", repr(e))
        return 0


def pick_cover_for_table(
    table: str,
    order_column: str,
    user_id: str,
    headers: Dict[str, str],
) -> Optional[str]:
    base_url = f"{SUPABASE_URL}/rest/v1/{table}"
    params = {
        "select": f"work_id,{order_column}",
        "user_id": f"eq.{user_id}",
        "order": f"{order_column}.desc",
        "limit": "20",
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        rows = json.loads(body)
    
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"[home.list_summary] HTTPError while fetching {table}", e.code, body)
        return None
    
    except Exception as e:
        print(f"[home.list_summary] error while fetching {table}:", repr(e))
        return None

    work_ids: List[str] = []
    for row in rows:
        wid = row.get("work_id")
        
        if not wid:
            continue
        wid_str = str(wid)
        
        if wid_str not in work_ids:
            work_ids.append(wid_str)

    if not work_ids:
        return None

    ed_params = {
        "select": "work_id,cover_url,pub_date",
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
        print(f"[home.list_summary] editions HTTPError for {table}", e.code, body)
        return None
    
    except Exception as e:
        print(f"[home.list_summary] editions error for {table}:", repr(e))
        return None

    for row in ed_rows:
        cover = normalize_cover_url(row.get("cover_url"))
        if cover:
            return cover

    return None


@router.get("/list_summary")
async def list_summary(user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    headers = supabase_headers()
    reading_count = count_user_rows("reading_progress", user["id"], headers)
    completed_count = count_user_rows("completions", user["id"], headers)
    reading_cover = pick_cover_for_table(
        "reading_progress", "updated_at", user["id"], headers
    )
    completed_cover = pick_cover_for_table(
        "completions", "finished_at", user["id"], headers
    )

    return {
        "reading_count": reading_count,
        "completed_count": completed_count,
        "reading_cover_url": reading_cover,
        "completed_cover_url": completed_cover,
    }


def user_books_from_table(
    table: str,
    order_column: str,
    user_id: str,
    limit: int,
    headers: Dict[str, str],
) -> List[Dict[str, Any]]:
    params = {
        "select": f"work_id,{order_column}",
        "user_id": f"eq.{user_id}",
        "order": f"{order_column}.desc",
        "limit": str(limit),
    }
    base_url = f"{SUPABASE_URL}/rest/v1/{table}"
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        rows = json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"[home.{table}_list] HTTPError reading {table}", e.code, body)
        raise HTTPException(
            status_code=500,
            detail=f"Supabase error while reading {table} ({e.code}): {body}",
        )
    except Exception as e:
        print(f"[home.{table}_list] error reading {table}:", repr(e))
        raise HTTPException(status_code=500, detail=f"Failed to load {table}")

    if not rows:
        return []

    work_ids: List[str] = []
    order_map: Dict[str, int] = {}

    for idx, row in enumerate(rows):
        wid = row.get("work_id")
        if not wid:
            continue
        wid_str = str(wid)
        if wid_str not in order_map:
            order_map[wid_str] = idx
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
        print(f"[home.{table}_list] editions HTTPError", e.code, body)
        raise HTTPException(
            status_code=500,
            detail=f"Supabase error while reading editions ({e.code}): {body}",
        )
    except Exception as e:
        print(f"[home.{table}_list] editions error:", repr(e))
        raise HTTPException(status_code=500, detail="Failed to load editions")

    items: List[Dict[str, Any]] = []
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
        items.append(
            {
                "work_id": wid_str,
                "edition_id": row.get("edition_id"),
                "title": title,
                "cover_url": row.get("cover_url"),
            }
        )

    items.sort(key=lambda r: order_map.get(str(r["work_id"]), 0))
    return items[:limit]


@router.get("/reading_list")
async def reading_list(
    limit: int = Query(100, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    headers = supabase_headers()
    items = user_books_from_table(
        "reading_progress", "updated_at", user["id"], limit, headers
    )

    return {
        "name": "All current reads",
        "items": items,
    }


@router.get("/completed_list")
async def completed_list(
    limit: int = Query(100, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    headers = supabase_headers()
    items = user_books_from_table(
        "completions", "finished_at", user["id"], limit, headers
    )

    return {
        "name": "All completed books",
        "items": items,
    }
