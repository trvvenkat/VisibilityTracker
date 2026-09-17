import logging
from pathlib import Path
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.auth import (
    check_credentials,
    create_session_token,
    get_current_user,
    require_authenticated_user,
)

logger = logging.getLogger("visibility_tracker.api.auth")

router = APIRouter(tags=["auth"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/login", response_class=HTMLResponse, summary="Login page")
async def login_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None, "app_name": settings.APP_NAME},
    )


@router.post("/login", summary="Process user login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if check_credentials(username, password):
        token = create_session_token(username.strip())
        logger.info(f"User '{username.strip()}' logged in successfully.")
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=token,
            max_age=settings.SESSION_MAX_AGE_SECS,
            httponly=True,
            samesite="lax",
        )
        return response

    logger.warning(f"Failed login attempt for username '{username.strip()}'.")
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": "Invalid username or password. Please verify your credentials.",
            "app_name": settings.APP_NAME,
            "username": username,
        },
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@router.get("/logout", summary="Logout user and clear session")
@router.post("/logout", summary="Logout user and clear session")
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key=settings.SESSION_COOKIE_NAME)
    return response


@router.get("/api/auth/me", summary="Check current authenticated user")
async def auth_me(user: str = Depends(require_authenticated_user)):
    return {"username": user, "authenticated": True}
