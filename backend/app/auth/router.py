"""Endpoints de login com Google."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.calendar import service as calendar_service
from app.db.models import User
from app.db.session import get_db

from . import service
from .dependencies import SESSION_COOKIE, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
STATE_COOKIE = "studyai_oauth_state"
VERIFIER_COOKIE = "studyai_oauth_verifier"

# Em produção, frontend (Vercel) e backend (Render) são domínios diferentes
# de verdade — não só portas do localhost — então o cookie de sessão é
# cross-site: precisa de SameSite=None (o browser só manda em fetch
# cross-site com isso) + Secure (exigido pelo browser junto de SameSite=None,
# e só funciona sobre HTTPS, que é o que produção usa).
_IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"


def _cookie_security() -> dict:
    if _IS_PRODUCTION:
        return {"secure": True, "samesite": "none"}
    return {"secure": False, "samesite": "lax"}


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    picture: str | None = None


@router.get("/google/login")
def google_login() -> RedirectResponse:
    try:
        auth_url, state, code_verifier = service.build_authorization_url()
    except service.AuthNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    response = RedirectResponse(auth_url)
    response.set_cookie(STATE_COOKIE, state, httponly=True, max_age=600, **_cookie_security())
    response.set_cookie(
        VERIFIER_COOKIE, code_verifier, httponly=True, max_age=600, **_cookie_security()
    )
    return response


@router.get("/google/callback")
def google_callback(
    request: Request,
    code: str,
    state: str,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    saved_state = request.cookies.get(STATE_COOKIE)
    if not saved_state or saved_state != state:
        raise HTTPException(status_code=400, detail="State OAuth inválido (CSRF?). Tente entrar de novo.")

    code_verifier = request.cookies.get(VERIFIER_COOKIE)
    if not code_verifier:
        raise HTTPException(
            status_code=400,
            detail="Cookie de verificação PKCE ausente/expirado. Tente entrar de novo.",
        )

    try:
        info, credentials = service.exchange_code(code, state, code_verifier)
    except service.AuthNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Falha no login com Google: {e}") from e

    user = service.get_or_create_user(
        db,
        google_id=info["sub"],
        email=info["email"],
        name=info.get("name", info["email"]),
        picture=info.get("picture"),
    )
    # Mesmo consentimento já inclui o escopo do Calendar (ver auth/service.py) —
    # salva o token aqui pra não exigir uma segunda tela de permissão depois.
    calendar_service.store_credentials(db, user.id, credentials)

    token = service.create_session_token(user.id)

    redirect = RedirectResponse(FRONTEND_URL)
    redirect.delete_cookie(STATE_COOKIE, **_cookie_security())
    redirect.delete_cookie(VERIFIER_COOKIE, **_cookie_security())
    redirect.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        max_age=60 * 60 * 24 * service.JWT_EXPIRE_DAYS,
        **_cookie_security(),
    )
    return redirect


@router.post("/logout", status_code=204, response_model=None)
def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, **_cookie_security())


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email, name=user.name, picture=user.picture)
