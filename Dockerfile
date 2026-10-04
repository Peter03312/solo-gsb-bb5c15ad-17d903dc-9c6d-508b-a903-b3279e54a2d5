# ---- 前端构建阶段 ----
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- 后端运行阶段 ----
FROM python:3.11-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/data \
    STATIC_DIR=/app/static
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
# 拷入前端构建产物，由 FastAPI 托管
COPY --from=frontend /build/dist ./static

# 数据卷：SQLite 数据库、音频、逐字稿均存放在此
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000
# 容器启动时自动初始化数据库与表结构
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
