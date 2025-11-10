import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

bearer = HTTPBearer(auto_error=True)

def get_environment(name: str) -> str:
    val = os.getenv(name)
    
    if not val:
        raise HTTPException(status_code=500, detail="Authorization not configured (missing environment variables).")
    return val


def decode_supabase_jwt(token: str) -> dict:
    secret = get_environment("SUPABASE_JWT_SECRET")
    baseUrl = get_environment("SUPABASE_URL")

    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_aud": False})

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    
    expectedIss = f"{baseUrl.rstrip('/')}/auth/v1"
    iss = str(claims.get("iss", "")).rstrip("/")

    if iss != expectedIss:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token issuer")
    return claims


def get_current_user(creds:HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")
    
    claims = decode_supabase_jwt(creds.credentials)
    uid = claims.get("sub")

    if not uid:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return {"id":uid, "email":claims.get("email"), "role":claims.get("role")}
