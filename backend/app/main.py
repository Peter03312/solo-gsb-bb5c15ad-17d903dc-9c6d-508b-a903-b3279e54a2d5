"""FastAPI 入口：API 路由 + 前端静态资源 + SPA 回退。"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .database import init_db
from .routers import audios, events, publications


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动即初始化：创建数据目录、WAL 数据库与全部表结构
    init_db()
    yield


app = FastAPI(title="地方博物馆口述史编年工作台", lifespan=lifespan)

app.include_router(events.router)
app.include_router(audios.router)
app.include_router(publications.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


if config.STATIC_DIR.exists():
    assets_dir = config.STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def index():
        return FileResponse(config.STATIC_DIR / "index.html")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        # API 路径不回退（交由路由自身 404）
        if full_path.startswith("api/"):
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not Found")
        target = config.STATIC_DIR / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        # 其余路径一律返回 SPA 入口，交由前端渲染
        return FileResponse(config.STATIC_DIR / "index.html")
