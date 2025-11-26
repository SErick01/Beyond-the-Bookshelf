from fastapi import FastAPI, Depends, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .security import get_current_user
from . import home
from . import recommendRoutes
import os
import json
import urllib.request
import urllib.parse
import urllib.error

app = FastAPI(title="Beyond the Bookshelf - API", version="0.1.0")
api = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://beyond-the-bookshelf.vercel.app"
]

app.include_router(recommendRoutes.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/health")
async def health():
    return {"status": "ok"}

@api.get("/users/me")
async def users_me(user=Depends(get_current_user)):
    return user

@api.get("/reading-challenge/current")
async def reading_challenge_current(
    year: int,
    user: dict = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    headers = supabase_headers()
    user_id = user["id"]
    chal_params = {
        "select": "target_count",
        "user_id": f"eq.{user_id}",
        "year": f"eq.{year}",
        "limit": "1",
    }
    chal_url = f"{SUPABASE_URL}/rest/v1/reading_challenges?{urllib.parse.urlencode(chal_params)}"
    target_count = None

    try:
        chal_req = urllib.request.Request(chal_url, headers=headers, method="GET")
        with urllib.request.urlopen(chal_req, timeout=10) as resp:
            chal_body = resp.read().decode("utf-8")
        chal_rows = json.loads(chal_body)
        if chal_rows:
            target_count = chal_rows[0].get("target_count")
    
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print("[reading_challenge] reading_challenges HTTPError", e.code, body)
        raise HTTPException(
            status_code=500,
            detail=f"Supabase error while reading reading_challenges ({e.code}): {body}",
        )
    
    except Exception as e:
        print("[reading_challenge] reading_challenges error:", repr(e))
        raise HTTPException(status_code=500, detail="Failed to load reading challenge")

    start = f"{year}-01-01"
    end = f"{year + 1}-01-01"
    comp_params = [
        ("select", "work_id,finished_at"),
        ("user_id", f"eq.{user_id}"),
        ("finished_at", f"gte.{start}"),
        ("finished_at", f"lt.{end}"),
        ("limit", "10000"),
    ]
    comp_url = f"{SUPABASE_URL}/rest/v1/completions?{urllib.parse.urlencode(comp_params)}"
    completed_count = 0
    
    try:
        comp_req = urllib.request.Request(comp_url, headers=headers, method="GET")
        with urllib.request.urlopen(comp_req, timeout=10) as resp:
            comp_body = resp.read().decode("utf-8")
        comp_rows = json.loads(comp_body)
        completed_count = len(comp_rows)
        
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print("[reading_challenge] completions HTTPError", e.code, body)
        raise HTTPException(
            status_code=500,
            detail=f"Supabase error while reading completions ({e.code}): {body}",
        )
    
    except Exception as e:
        print("[reading_challenge] completions error:", repr(e))
        raise HTTPException(status_code=500, detail="Failed to load completions")

    return {
        "year": year,
        "target_count": target_count,
        "completed_count": completed_count,
    }

@api.put("/reading-challenge/current")
async def update_reading_challenge_current(
    payload: dict,
    user: dict = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    year = payload.get("year")
    target_count = payload.get("target_count")

    if not isinstance(year, int) or not isinstance(target_count, int):
        raise HTTPException(status_code=400, detail="year and target_count must be integers")

    if target_count <= 0:
        raise HTTPException(status_code=400, detail="target_count must be positive")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }
    supabase_row = {
        "user_id": user["id"],
        "year": year,
        "target_count": target_count,
    }
    base_url = f"{SUPABASE_URL}/rest/v1/reading_challenges"
    query = urllib.parse.urlencode({"on_conflict": "user_id,year"})
    url = f"{base_url}?{query}"
    data = json.dumps(supabase_row).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            print("[reading_challenge] upsert OK:", resp.status, body)
    
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        print("[reading_challenge] upsert HTTPError:", e.code, error_body)
        raise HTTPException(
            status_code=500,
            detail=f"Supabase error while saving reading_challenges ({e.code}): {error_body}",
        )
    
    except Exception as e:
        print("[reading_challenge] upsert error:", repr(e))
        raise HTTPException(status_code=500, detail="Failed to save reading challenge")
    return await reading_challenge_current(year=year, user=user)

app.include_router(api, prefix="/api")
app.include_router(home.router)