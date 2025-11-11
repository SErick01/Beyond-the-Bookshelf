import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

bearer = HTTPBearer(auto_error=False)

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


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")

    token = credentials.credentials
    jwt_secret = os.environ.get("SUPABASE_JWT_SECRET")
    jwt_iss = os.environ.get("SUPABASE_URL")

    if not jwt_secret or not jwt_iss:
        raise HTTPException(status_code=500, detail="Auth not configured")

    try:
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"], options={"verify_aud": False})
        if not str(payload.get("iss", "")).startswith(jwt_iss):
            raise HTTPException(status_code=401, detail="Invalid token issuer")

        return {"id": payload.get("sub"), "email": payload.get("email"), "role": payload.get("role")}
    
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
