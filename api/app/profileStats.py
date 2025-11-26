from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from .userMatplotlib import create_yearly_charts
from .security import get_current_user

router = APIRouter(prefix="/api/home", tags=["profile-stats"])


@router.get("/stats/{year}/pages")
async def get_pages_chart(year: int, user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    charts = create_yearly_charts(user_id=user["id"], year=year)

    if not charts or "pages" not in charts:
        raise HTTPException(status_code=404, detail="No reading data for that year")

    return FileResponse(charts["pages"], media_type="image/png")


@router.get("/stats/{year}/genres")
async def get_genres_chart(year: int, user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    charts = create_yearly_charts(user_id=user["id"], year=year)

    if not charts or "genres" not in charts:
        raise HTTPException(status_code=404, detail="No genre data for that year")

    return FileResponse(charts["genres"], media_type="image/png")


@router.get("/stats/{year}/timeline")
async def get_timeline_chart(year: int, user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    charts = create_yearly_charts(user_id=user["id"], year=year)

    if not charts or "timeline" not in charts:
        raise HTTPException(status_code=404, detail="No completion data for that year")

    return FileResponse(charts["timeline"], media_type="image/png")
