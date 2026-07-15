"""Dependency do FastAPI para proteger rotas com a sessão do cookie."""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db

from . import service

SESSION_COOKIE = "studyai_session"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    try:
        user_id = service.decode_session_token(token)
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada.") from e

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Igual a get_current_user, mas devolve None em vez de 401 (rotas que funcionam com ou sem login)."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        user_id = service.decode_session_token(token)
    except jwt.PyJWTError:
        return None
    return db.get(User, user_id)
