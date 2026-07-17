"""Endpoints REST do chat — exigem login (ver app.auth)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from google.api_core.exceptions import TooManyRequests
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.calendar import service as cal
from app.db.models import User
from app.db.session import get_db

from . import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    usar_calendario: bool = False
    permitir_criar: bool = False


class CalendarActionOut(BaseModel):
    title: str
    start: str
    end: str
    description: str | None = None


class ChatResponse(BaseModel):
    reply: str
    actions: list[CalendarActionOut] = []


class MessageOut(BaseModel):
    role: str
    content: str


@router.post("", response_model=ChatResponse)
def send(
    body: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatResponse:
    texto = body.message.strip()
    if not texto:
        raise HTTPException(status_code=422, detail="Mensagem vazia.")

    permitir_criar = body.permitir_criar and cal.has_write_access(db, user.id)
    try:
        texto_visivel, acoes = chat_service.send_message(
            db,
            user.id,
            texto,
            usar_calendario=body.usar_calendario,
            permitir_criar=permitir_criar,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except TooManyRequests as e:
        # Limite de taxa da chave gratuita do Gemini (poucas requisições por
        # minuto). Mensagem específica em vez do genérico "erro ao gerar
        # resposta" — isso já confundiu gente de verdade testando o app.
        raise HTTPException(
            status_code=429,
            detail="Muitas mensagens ao mesmo tempo (limite da chave gratuita do Gemini). Tente de novo em alguns segundos.",
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar resposta: {e}") from e

    return ChatResponse(reply=texto_visivel, actions=acoes)


@router.get("/history", response_model=list[MessageOut])
def history(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[MessageOut]:
    return [MessageOut(**m) for m in chat_service.get_history(db, user.id)]


@router.post("/reset", status_code=204, response_model=None)
def reset(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    chat_service.reset_history(db, user.id)
