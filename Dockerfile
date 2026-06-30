# ── 构建阶段 ──
FROM python:3.12-slim AS builder
WORKDIR /build
RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/deps -r requirements.txt

# ── 运行阶段 ──
FROM python:3.12-slim
WORKDIR /app

# 从构建阶段拷贝依赖
COPY --from=builder /deps /usr/local/lib/python3.12/site-packages

# 拷贝应用代码
COPY app/ ./app/

# 数据库持久化目录
VOLUME ["/data"]
ENV DB_PATH=/data/human_manual.db

# 端口
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
