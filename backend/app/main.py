from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .database import init_db
from .errors import DomainError
from .routers import events, files, media, releases


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="地方博物馆口述史编年工作台", version="1.0.0", lifespan=lifespan)

# Local single-machine tool: permissive CORS so the Vite dev server works.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    # Pydantic v2 errors embed ValueError objects in ctx; jsonable_encoder
    # turns them into plain strings.
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
    msg = first.get("msg", "请求参数不合法")
    return JSONResponse(
        status_code=422,
        content={
            "detail": f"输入不合法（{loc}）：{msg}" if loc else f"输入不合法：{msg}",
            "problems": jsonable_encoder(exc.errors()),
        },
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(media.router)
app.include_router(files.router)
app.include_router(events.router)
app.include_router(releases.router)


# ---- Static frontend (production image) -------------------------------------

if config.STATIC_DIR.exists():
    assets_dir = config.STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def index():
        return FileResponse(config.STATIC_DIR / "index.html")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        # Never shadow API routes or real files; everything else returns
        # index.html so client-side routing works on refresh/deep links.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = config.STATIC_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(config.STATIC_DIR / "index.html")
