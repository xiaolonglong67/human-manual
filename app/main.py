"""
FastAPI 应用入口 — 挂载路由、静态文件、启动初始化
"""

import os
import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.errors import ServerErrorMiddleware

from .database import init_db
from .routers.auth import router as auth_router
from .routers.chat import router as chat_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan, title="人类使用说明书")

# ═══ 最底层 JSON 异常兜底 ═══
# Starlette 的 ServerErrorMiddleware 会返回 HTML 错误页，
# 用一个自定义中间件包住它 —— 任何漏网的异常都返回 JSON
async def json_error_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        logger.error(f"未捕获异常: {request.url}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"detail": "服务器内部错误，请稍后重试"},
        )

app.middleware("http")(json_error_middleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 路由
app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# 静态文件 — 必须在路由之后
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
