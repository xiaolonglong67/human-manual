"""
聊天路由 — POST /api/chat  意图识别 → DeepSeek → 数据库 → 回复
"""

import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..auth import verify_token
from ..database import (
    format_person_card,
    get_db,
    get_person_full,
    list_people,
    lookup_person,
    upsert_person,
)
from ..deepseek import call_deepseek

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str


async def get_current_user(request: Request):
    """从 Authorization header 提取并验证 JWT"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="请先登录")
    payload = verify_token(auth[7:])
    if payload is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return payload


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    content = body.message.strip()

    # ── 记录说明书 ──
    if content.startswith("记录说明书："):
        raw = content[len("记录说明书："):].strip()
        if not raw:
            return ChatResponse(
                reply="💡 请这样写：\n记录说明书：张三，不吃香菜，生日是5月12日"
            )

        try:
            parsed = await call_deepseek(raw)
        except Exception as e:
            logger.error(f"DeepSeek 调用失败: {traceback.format_exc()}")
            return ChatResponse(reply=f"❌ AI 解析失败：{e}")

        async with get_db() as db:
            is_new = await upsert_person(db, user_id, parsed)

        name = parsed["name"]
        return ChatResponse(
            reply=f"✅ 已{'创建' if is_new else '更新'}「{name}」的说明书！"
        )

    # ── 查询说明书 ──
    if content.startswith("查询说明书："):
        query = content[len("查询说明书："):].strip()
        if not query:
            return ChatResponse(reply="💡 请这样写：\n查询说明书：张三")

        async with get_db() as db:
            row = await lookup_person(db, user_id, query)
            if row:
                full = await get_person_full(db, row["id"])
                text = format_person_card(full)
            else:
                text = (
                    f"🔍 未找到「{query}」的说明书。\n"
                    f"发送「记录说明书：{query}，...」来创建。"
                )

        return ChatResponse(reply=text)

    # ── 说明书列表 ──
    if content == "说明书列表":
        async with get_db() as db:
            rows = await list_people(db, user_id)

        if not rows:
            return ChatResponse(
                reply="📭 还未记录任何人的说明书。\n发送「记录说明书：人名，描述...」来添加第一条！"
            )

        lines = ["📚 【已记录的说明书】"]
        for i, row in enumerate(rows, 1):
            label = f"  {row['name']}"
            if row["alias"]:
                label += f"（{row['alias']}）"
            lines.append(f"{i}.{label}")
        lines.append(f"\n共 {len(rows)} 条记录。发送「查询说明书：姓名」查看详情。")

        return ChatResponse(reply="\n".join(lines))

    # ── 其他 → 引导 ──
    return ChatResponse(
        reply=(
            "👋 你好！你可以这样使用：\n\n"
            "📝 记录说明书：张三，不吃香菜，喜欢辣的\n"
            "🔍 查询说明书：张三\n"
            "📋 说明书列表"
        )
    )


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return {"username": user["username"]}
