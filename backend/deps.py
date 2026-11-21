"""Dependencies مشتركة: مين المستخدم الحالي؟ وعنده صلاحية ولا لأ؟"""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import services
from .database import get_db
from .security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    con=Depends(get_db),
):
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = decode_access_token(creds.credentials)
        user = services.get_user(con, int(payload["sub"]))
    except (jwt.PyJWTError, services.NotFound, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})
    if not user["is_active"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    return user


def require_roles(*roles):
    def checker(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have permission for this action")
        return user
    return checker


require_staff = require_roles("admin", "doctor")
require_admin = require_roles("admin")
