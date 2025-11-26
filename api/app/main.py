from fastapi import FastAPI, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from .security import get_current_user
from . import home
from . import recommendRoutes
from . import readingChallenge
from . import profileStats

app = FastAPI(title="Beyond the Bookshelf - API", version="0.1.0")
api = APIRouter()

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://beyond-the-bookshelf.vercel.app",
]

app.include_router(recommendRoutes.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\\.vercel\\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@api.get("/users/me")
async def users_me(user=Depends(get_current_user)):
    return user


app.include_router(api, prefix="/api")
app.include_router(home.router)
app.include_router(readingChallenge.router)
app.include_router(profileStats.router)
