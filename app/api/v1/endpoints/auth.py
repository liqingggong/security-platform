from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.db import models
from app.db.session import get_db
from app.schemas.user import Token, RefreshToken, UserLogin, UserCreate, User as UserSchema

router = APIRouter()


@router.post("/register", response_model=UserSchema)
def register_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
):
    """
    註冊新用戶
    """
    # 檢查郵箱是否已註冊
    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="該郵箱已被註冊",
        )

    # 創建租戶
    tenant = models.Tenant(name=f"{user_in.email}的組織")
    db.add(tenant)
    db.flush()  # 獲取 tenant.id

    # 創建用戶
    hashed_password = hash_password(user_in.password)
    user = models.User(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        tenant_id=tenant.id,
        role=models.UserRole.USER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=Token)
def login(
    *,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    OAuth2 兼容令牌登入, 返回訪問令牌和刷新令牌
    支持 OAuth2 標準格式（form-data）和 JSON 格式
    """
    # OAuth2PasswordRequestForm 使用 username 字段，我們將其作為 email
    email = form_data.username
    password = form_data.password

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="郵箱或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用戶未啟用",
        )

    # 生成訪問令牌（30分鐘過期）
    access_token = create_access_token(
        subject=user.email,
        expires_minutes=30,  # 30分鐘
    )

    # 生成刷新令牌（7天過期）
    refresh_token = create_refresh_token(subject=user.email, expires_days=7)

    # 保存刷新令牌到數據庫
    user.refresh_token = refresh_token
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 30 * 60,  # 秒
    }


@router.post("/refresh", response_model=Token)
def refresh_token(
    *,
    db: Session = Depends(get_db),
    token_in: RefreshToken,
):
    """
    使用刷新令牌獲取新的訪問令牌
    """
    try:
        payload = decode_token(token_in.refresh_token)
        email: str = payload.get("sub")
        token_type: str = payload.get("type")

        if not email or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無效的刷新令牌",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的刷新令牌",
        )

    # 驗證刷新令牌是否存在於數據庫
    user = db.query(models.User).filter(
        models.User.email == email,
        models.User.refresh_token == token_in.refresh_token
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌已失效，請重新登錄",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用戶未啟用",
        )

    # 生成新的訪問令牌
    access_token = create_access_token(subject=user.email, expires_minutes=30)

    # 也可以生成新的刷新令牌（輪換機制，提高安全性）
    new_refresh_token = create_refresh_token(subject=user.email, expires_days=7)
    user.refresh_token = new_refresh_token
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": 30 * 60,
    }


@router.get("/me", response_model=UserSchema)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    """
    獲取當前用戶信息
    """
    return current_user
