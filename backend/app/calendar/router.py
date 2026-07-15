"""
Endpoints REST para a integração com Google Calendar.

Sem endpoint de "conectar" — o consentimento do Calendar acontece junto do
login (GET /auth/google/login). Reconectar (depois de Desconectar, ou pra
quem logou antes da sub-etapa 8c) é entrar com Google de novo.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db

from . import service as cal

router = APIRouter(prefix="/calendar", tags=["calendar"])


class CalendarStatus(BaseModel):
    configured: bool
    authenticated: bool
    write_access: bool


class EventOut(BaseModel):
    raw: dict
    label: str


class CreateEventRequest(BaseModel):
    title: str
    start: str
    end: str
    description: str | None = None


@router.get("/status", response_model=CalendarStatus)
def get_status(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> CalendarStatus:
    return CalendarStatus(
        configured=cal.credentials_configured(),
        authenticated=cal.is_authenticated(db, user.id),
        write_access=cal.has_write_access(db, user.id),
    )


@router.post("/disconnect", response_model=CalendarStatus)
def disconnect(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> CalendarStatus:
    cal.disconnect(db, user.id)
    return get_status(db=db, user=user)


@router.get("/events", response_model=list[EventOut])
def list_events(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[EventOut]:
    try:
        events = cal.list_upcoming_events(db, user.id)
    except cal.CalendarNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except cal.CalendarAuthError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    return [EventOut(raw=e, label=cal.format_event_line(e)) for e in events]


@router.post("/events", status_code=201)
def create_event(
    body: CreateEventRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        return cal.create_event(
            db,
            user.id,
            title=body.title,
            start=body.start,
            end=body.end,
            description=body.description,
        )
    except cal.CalendarAuthError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
