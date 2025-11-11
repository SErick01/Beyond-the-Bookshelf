from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.security import get_current_user

app = FastAPI(title="Beyond the Bookshelf - API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/users/me")
async def users_me(user = Depends(get_current_user)):
    return user
