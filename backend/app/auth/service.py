"""
Login com Google (fluxo OAuth Web) + sessão via JWT.

O mesmo login já pede acesso ao Google Calendar (escopo incluso) — por
decisão do usuário, para não exigir um segundo consentimento separado depois.
access_type="offline" + prompt="consent" garantem um refresh_token em todo
login, mesmo para quem já autorizou antes — sem isso o backend não consegue
usar o Calendar depois que o usuário fecha o navegador.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import jwt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.env import clean_env
from app.db.models import User

# oauthlib recusa o token por padrão se o Google devolver escopos diferentes
# dos pedidos — o que acontece na prática, porque a mesma conta/projeto do
# Google Cloud já tem o escopo do Calendar concedido para outro client_id, e
# o Google inclui isso na resposta. Não nos importa (só lemos o id_token
# aqui), então relaxamos essa checagem em vez de deixar o login quebrar.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

GOOGLE_CLIENT_ID = clean_env("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = clean_env("GOOGLE_CLIENT_SECRET")
GOOGLE_LOGIN_REDIRECT_URI = clean_env(
    "GOOGLE_LOGIN_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
)

JWT_SECRET = clean_env("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 7

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar",
]


class AuthNotConfiguredError(Exception):
    """GOOGLE_CLIENT_ID/SECRET ou JWT_SECRET ausentes no .env."""


def _client_config() -> dict:
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise AuthNotConfiguredError(
            "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET ausentes em backend/.env."
        )
    return {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GOOGLE_LOGIN_REDIRECT_URI],
        }
    }


def build_flow(*, state: str | None = None, code_verifier: str | None = None) -> Flow:
    return Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        state=state,
        redirect_uri=GOOGLE_LOGIN_REDIRECT_URI,
        code_verifier=code_verifier,
    )


def build_authorization_url() -> tuple[str, str, str]:
    """
    Devolve (url_de_consentimento, state, code_verifier).

    O Flow usa PKCE por padrão (autogenerate_code_verifier=True): gera o
    code_verifier e manda o code_challenge derivado dele na URL. Esse
    verifier só existe nesta instância do Flow, que morre no fim da função —
    por isso ele também precisa ir num cookie (como o state) e ser reaplicado
    explicitamente no Flow usado no callback, senão a troca do code por
    token falha com "invalid_grant: Missing code verifier".
    """
    flow = build_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )
    return auth_url, state, flow.code_verifier


def exchange_code(code: str, state: str, code_verifier: str) -> tuple[dict, Credentials]:
    """
    Troca o code pelo token. Devolve (info_do_usuario, credentials) — info
    vem do id_token (sub/email/name/picture), credentials é o objeto do
    google-auth com access_token + refresh_token, para o app.calendar.service
    guardar e usar depois.
    """
    flow = build_flow(state=state, code_verifier=code_verifier)
    flow.fetch_token(code=code)
    credentials = flow.credentials
    info = google_id_token.verify_oauth2_token(
        credentials.id_token, google_requests.Request(), GOOGLE_CLIENT_ID
    )
    return info, credentials


def get_or_create_user(db: Session, *, google_id: str, email: str, name: str, picture: str | None) -> User:
    user = db.execute(select(User).where(User.google_id == google_id)).scalar_one_or_none()
    if user:
        return user
    user = User(google_id=google_id, email=email, name=name, picture=picture)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_session_token(user_id: int) -> str:
    if not JWT_SECRET:
        raise AuthNotConfiguredError("JWT_SECRET ausente em backend/.env.")
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_session_token(token: str) -> int:
    if not JWT_SECRET:
        raise AuthNotConfiguredError("JWT_SECRET ausente em backend/.env.")
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    return int(payload["sub"])
