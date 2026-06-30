"""
认证路由 — 注册 / 登录
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..auth import create_token, hash_password, verify_password
from ..database import create_user, get_db, get_user

router = APIRouter(prefix="/api", tags=["auth"])


class AuthRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=20, pattern=r"^[a-zA-Z0-9_一-鿿]+$")
    password: str = Field(..., min_length=4, max_length=64)


class AuthResponse(BaseModel):
    token: str
    username: str


@router.post("/register", response_model=AuthResponse)
async def register(body: AuthRequest):
    """注册新用户，成功后直接返回 token"""
    async with get_db() as db:
        hashed = hash_password(body.password)
        user_id = await create_user(db, body.username, hashed)
        if user_id is None:
            raise HTTPException(status_code=409, detail="用户名已存在")
        token = create_token(user_id, body.username)
        return AuthResponse(token=token, username=body.username)


@router.post("/login", response_model=AuthResponse)
async def login(body: AuthRequest):
    """登录，验证密码后返回 token"""
    async with get_db() as db:
        user = await get_user(db, body.username)
        if user is None or not verify_password(body.password, user["password"]):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        token = create_token(user["id"], body.username)
        return AuthResponse(token=token, username=body.username)
