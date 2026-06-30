"""
JWT 认证 — 生成/验证 token，密码 bcrypt 哈希
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

# 密钥：优先用环境变量，否则用固定值（生产环境务必设定环境变量）
SECRET_KEY = os.environ.get("JWT_SECRET", "human-manual-secret-key-change-me")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 168  # 7 天


def hash_password(password: str) -> str:
    """bcrypt 哈希密码"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_token(user_id: int, username: str) -> str:
    """生成 JWT token"""
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict | None:
    """验证 token，返回 payload 或 None"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
