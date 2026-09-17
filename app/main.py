import asyncio
from contextlib import asynccontextmanager
import logging
from pathlib import Path
import sys
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Windows asyncio Proactor policy (required for Playwright on Windows)
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

from app.api.auth import router as auth_router
from app.api.jobs import router as jobs_router
from app.api.tunnel import router as tunnel_router
from app.api.upload import router as upload_router
from app.config import settings
from app.services.auth import get_current_user

# Configure root and application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("visibility_tracker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    settings.JOBS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Initialized {settings.APP_NAME}")
    logger.info(f"Uploads dir: {settings.UPLOADS_DIR}")
    logger.info(f"Jobs dir: {settings.JOBS_DIR}")
    logger.info(f"Browser Headless: {settings.BROWSER_HEADLESS}")
    yield
    # Shutdown actions
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Automated Amazon and Flipkart Sponsored Product & Display Visibility Checker",
    lifespan=lifespan,
)

# CORS middleware for local usage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Mount static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Include routers
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(jobs_router)
app.include_router(tunnel_router)


@app.get("/", response_class=HTMLResponse, summary="Main visibility tracker dashboard")
async def get_index_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.APP_NAME,
            "default_top_n": settings.DEFAULT_TOP_N,
            "current_user": user,
        },
    )


@app.get("/api/health", summary="Health check endpoint")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "headless": settings.BROWSER_HEADLESS,
    }
