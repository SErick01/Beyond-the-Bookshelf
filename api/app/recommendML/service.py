from typing import List, Dict
import os
from supabase import create_client, Client
from .weightedcombov2 import recommend_works_for_user

SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Supabase env vars SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY are missing")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def _fetch_works_with_details(work_ids: List[int]) -> List[dict]:
    if not work_ids:
        return []

    works_resp = (
        supabase.table("works")
        .select("work_id, title, publish_year, summary")
        .in_("work_id", work_ids)
        .execute()
    )
    works = works_resp.data or []

    work_map: Dict[int, dict] = {
        w["work_id"]: {
            "work_id": w["work_id"],
            "title": w["title"],
            "publish_year": w.get("publish_year"),
            "summary": w.get("summary"),
            "authors": [],
            "cover_url": None,
            "page_count": None,
        }
        for w in works
    }

    if not work_map:
        return []

    found_ids = list(work_map.keys())
    editions_resp = (
        supabase.table("editions")
        .select("edition_id, work_id, page_count, cover_url")
        .in_("work_id", found_ids)
        .execute()
    )
    editions = editions_resp.data or []
    
    for ed in editions:
        wid = ed["work_id"]
        if wid in work_map and work_map[wid]["cover_url"] is None:
            work_map[wid]["cover_url"] = ed.get("cover_url")
            work_map[wid]["page_count"] = ed.get("page_count")

    wa_resp = (
        supabase.table("work_authors")
        .select("work_id, author_id, order_index")
        .in_("work_id", found_ids)
        .execute()
    )
    wa_rows = wa_resp.data or []

    author_ids = sorted({wa["author_id"] for wa in wa_rows}) if wa_rows else []
    if author_ids:
        authors_resp = (
            supabase.table("authors")
            .select("author_id, sort_name, name")
            .in_("author_id", author_ids)
            .execute()
        )
        authors = authors_resp.data or []
        author_name_map = {
            a["author_id"]: a.get("sort_name") or a.get("name")
            for a in authors
        }
    else:
        author_name_map = {}

    wa_by_work: Dict[int, List[dict]] = {}
    for wa in wa_rows:
        wa_by_work.setdefault(wa["work_id"], []).append(wa)

    for wid, wa_list in wa_by_work.items():
        wa_list.sort(key=lambda x: x.get("order_index", 0))
        names = [
            author_name_map.get(wa["author_id"])
            for wa in wa_list
            if author_name_map.get(wa["author_id"])
        ]
        if wid in work_map:
            work_map[wid]["authors"] = names

    order_map = {wid: idx for idx, wid in enumerate(work_ids)}
    ordered = sorted(
        work_map.values(),
        key=lambda row: order_map.get(row["work_id"], 10**9),
    )
    return ordered


def _titles_to_work_ids(titles: List[str]) -> List[int]:
    if not titles:
        return []

    unique_titles = list(dict.fromkeys(titles))
    resp = (
        supabase.table("works")
        .select("work_id, title")
        .in_("title", unique_titles)
        .execute()
    )
    rows = resp.data or []

    by_title: Dict[str, int] = {}
    for row in rows:
        t = row["title"]
        if t not in by_title:
            by_title[t] = row["work_id"]

    result_ids: List[int] = []
    seen: set[int] = set()
    for t in titles:
        wid = by_title.get(t)
        if wid is not None and wid not in seen:
            result_ids.append(wid)
            seen.add(wid)

    return result_ids


def _similar_work_ids_from_seed(work_id: int, limit: int = 20) -> List[int]:
    resp = (
        supabase.table("works")
        .select("title, summary")
        .eq("work_id", work_id)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return []

    seed = rows[0]
    title = seed.get("title") or ""
    description = seed.get("summary") or ""
    top_n_internal = max(limit * 3, limit + 5)
    df = recommend_content(
        title=title,
        description=description,
        genres=None,
        author=None,
        top_n=top_n_internal,
    )

    if df is None or df.empty:
        return []

    rec_titles = df["title"].tolist()
    rec_titles = [t for t in rec_titles if t != title]
    work_ids = _titles_to_work_ids(rec_titles)

    return work_ids[:limit]


def _fallback_popular_work_ids(limit: int) -> List[int]:
    resp = supabase.table("works").select("work_id").limit(limit).execute()
    rows = resp.data or []
    return [r["work_id"] for r in rows]


def _get_user_recent_work_id(user_id: str) -> int | None:
    resp = (
        supabase.table("completions")
        .select("work_id, finished_at")
        .eq("user_id", user_id)
        .order("finished_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if rows:
        return rows[0]["work_id"]

    resp2 = (
        supabase.table("reading_progress")
        .select("work_id, updated_at")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )
    rows2 = resp2.data or []
    if rows2:
        return rows2[0]["work_id"]
    return None


def recommend_for_user(user_id: str, limit: int = 10) -> List[dict]:
    work_ids = recommend_works_for_user(user_id=user_id, top_n=limit)
    if not work_ids:
        work_ids = _fallback_popular_work_ids(limit)
    return _fetch_works_with_details(work_ids[:limit])


def recommend_similar_works(work_id: int, limit: int = 10) -> List[dict]:
    work_ids = _fallback_popular_work_ids(limit)
    return _fetch_works_with_details(work_ids)
