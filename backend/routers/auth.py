"""تسجيل حساب / تسجيل دخول / بيانات المستخدم الحالي / إدارة المستخدمين (للأدمن)."""
from fastapi import APIRouter, Depends, HTTPException, status

from .. import services
from ..database import get_db
from ..deps import get_current_user, require_admin
from ..schemas import LoginIn, RegisterIn, TokenOut, UserCreateIn, UserOut
from ..security import create_access_token

router = APIRouter(prefix="/api/auth", tags=["Auth"])
users_router = APIRouter(prefix="/api/users", tags=["Users (admin)"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, con=Depends(get_db)):
    """التسجيل العام بيعمل حساب طالب. حسابات الدكاترة بيعملها الأدمن من /api/users."""
    try:
        return services.create_user(con, body.full_name, body.email, body.password, role="student")
    except services.Conflict as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, con=Depends(get_db)):
    user = services.authenticate(con, body.email, body.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")
    return {"access_token": create_access_token(user["id"], user["role"]), "user": user}


@router.get("/me", response_model=UserOut)
def me(user=Depends(get_current_user)):
    return user


@users_router.get("", response_model=list[UserOut])
def list_users(_=Depends(require_admin), con=Depends(get_db)):
    return services.list_users(con)


@users_router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreateIn, _=Depends(require_admin), con=Depends(get_db)):
    try:
        return services.create_user(con, body.full_name, body.email, body.password, role=body.role)
    except services.Conflict as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
