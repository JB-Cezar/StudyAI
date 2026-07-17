"""Endpoints REST do chat — exigem login (ver app.auth)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from google.api_core.exceptions import GoogleAPICallError
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger("studyai.chat")

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

    try:
        permitir_criar = body.permitir_criar and cal.has_write_access(db, user.id)
        texto_visivel, acoes = chat_service.send_message(
            db,
            user.id,
            texto,
            usar_calendario=body.usar_calendario,
            permitir_criar=permitir_criar,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except GoogleAPICallError as e:
        # Qualquer erro vindo da API do Gemini (limite de taxa, cota
        # esgotada, indisponibilidade momentânea etc.) — GoogleAPICallError é
        # a classe mãe de todos esses. Mensagem específica em vez do genérico
        # "erro ao gerar resposta", que já confundiu gente de verdade
        # testando o app sem entender que era passageiro.
        raise HTTPException(
            status_code=429,
            detail="A IA está sobrecarregada no momento (limite da chave gratuita do Gemini). Tente de novo em alguns segundos.",
        ) from e
    except Exception as e:
        # Traceback completo no log do servidor (Render → Logs) — sem isso,
        # só sobra a mensagem curta de str(e), que não diz em qual linha/lib
        # o erro aconteceu. Já gastamos tempo demais adivinhando por causa
        # disso; a próxima ocorrência precisa ser rápida de diagnosticar.
        logger.exception("Falha inesperada em POST /chat (user_id=%s)", user.id)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar resposta: {e}") from e

    return ChatResponse(reply=texto_visivel, actions=acoes)


@router.get("/history", response_model=list[MessageOut])
def history(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[MessageOut]:
    return [MessageOut(**m) for m in chat_service.get_history(db, user.id)]


@router.post("/reset", status_code=204, response_model=None)
def reset(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    chat_service.reset_history(db, user.id)
