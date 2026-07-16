"""
Integração com Google Calendar para o StudyAI — por usuário.

Sub-etapa 8c: o token de cada usuário vem do mesmo login OAuth Web (escopo
Calendar incluso, ver app/auth/service.py) e fica salvo no banco
(`google_credentials`), não mais num único `token.json` compartilhado.

Responsável por:
- Carregar/renovar as credenciais de um usuário a partir do banco
- Ler eventos da agenda
- Criar/atualizar eventos
- Normalizar datas que a IA envia em formatos inválidos
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.core.env import clean_env
from app.db.models import GoogleCredential

# Fuso horário usado nos eventos (Brasil)
TZ_SP = ZoneInfo("America/Sao_Paulo")

GOOGLE_CLIENT_ID = clean_env("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = clean_env("GOOGLE_CLIENT_SECRET")


class CalendarNotConfiguredError(Exception):
    """GOOGLE_CLIENT_ID/SECRET ausentes no .env (o app inteiro, não um usuário)."""


class CalendarAuthError(Exception):
    """Usuário não conectou o Google Calendar (ou o token não pôde ser renovado)."""


def credentials_configured() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def store_credentials(db: Session, user_id: int, credentials: Credentials) -> None:
    """Salva (ou atualiza) o token OAuth do usuário — chamado no callback do login."""
    row = db.get(GoogleCredential, user_id)
    if row is None:
        row = GoogleCredential(user_id=user_id, credentials_json=credentials.to_json())
        db.add(row)
    else:
        row.credentials_json = credentials.to_json()
    db.commit()


def _load_credentials(db: Session, user_id: int) -> Credentials | None:
    row = db.get(GoogleCredential, user_id)
    if row is None:
        return None
    try:
        return Credentials.from_authorized_user_info(json.loads(row.credentials_json))
    except Exception:
        return None


def has_write_access(db: Session, user_id: int) -> bool:
    creds = _load_credentials(db, user_id)
    if not creds:
        return False
    return "https://www.googleapis.com/auth/calendar" in set(creds.scopes or [])


def is_authenticated(db: Session, user_id: int) -> bool:
    creds = _load_credentials(db, user_id)
    if not creds:
        return False
    return creds.valid or bool(creds.refresh_token)


def get_credentials(db: Session, user_id: int) -> Credentials:
    """Carrega o token do usuário, renovando (e regravando no banco) se necessário."""
    if not credentials_configured():
        raise CalendarNotConfiguredError(
            "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET ausentes em backend/.env."
        )

    creds = _load_credentials(db, user_id)
    if not creds:
        raise CalendarAuthError(
            "Google Calendar não conectado. Entre com Google novamente para conceder acesso."
        )

    if creds.valid:
        return creds

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        store_credentials(db, user_id, creds)
        return creds

    raise CalendarAuthError(
        "Sessão do Google Calendar expirou. Entre com Google novamente."
    )


def get_calendar_service(db: Session, user_id: int):
    """Retorna o cliente da API Google Calendar v3 para este usuário."""
    creds = get_credentials(db, user_id)
    return build("calendar", "v3", credentials=creds)


def _parse_event_start(event: dict) -> datetime | None:
    """Extrai data/hora de início de um evento retornado pela API."""
    start = event.get("start", {})
    raw = start.get("dateTime") or start.get("date")
    if not raw:
        return None
    if "T" in raw:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    return datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)


def list_upcoming_events(
    db: Session,
    user_id: int,
    *,
    days_ahead: int = 14,
    max_results: int = 20,
) -> list[dict]:
    """Lista eventos do calendário principal do usuário nos próximos N dias."""
    service = get_calendar_service(db, user_id)
    now = datetime.now(timezone.utc)
    time_max = now + timedelta(days=days_ahead)

    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return result.get("items", [])


def normalize_datetime_iso(iso_str: str) -> str:
    """
    Corrige formatos que a IA envia (espaço em vez de T, sem fuso, ano errado).
    A API do Google rejeita datas como '2024-05-23 10:00:00' — precisa de 'T' e fuso.
    """
    raw = (iso_str or "").strip()
    if not raw:
        raise ValueError("Data/hora vazia.")

    if " " in raw and "T" not in raw:
        raw = raw.replace(" ", "T", 1)

    if "T" in raw:
        date_part, time_part = raw.split("T", 1)
        time_part = time_part.split("→")[0].strip()
        if len(time_part) == 5:
            time_part += ":00"
        if time_part.count(":") == 1:
            time_part += ":00"
        raw = f"{date_part}T{time_part}"

    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    if "+" not in raw[10:] and "-" not in raw[10:]:
        raw += "-03:00"

    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_SP)

    # Se a data estiver no passado, ajusta para o ano atual ou +7 dias
    agora = datetime.now(TZ_SP)
    if dt < agora - timedelta(hours=1):
        dt = dt.replace(year=agora.year)
    if dt < agora - timedelta(hours=1):
        dt = dt + timedelta(days=7)

    return dt.isoformat()


def _event_datetime_payload(iso_str: str) -> dict:
    """Monta o objeto start/end no formato exigido pela Google Calendar API."""
    dt = datetime.fromisoformat(normalize_datetime_iso(iso_str))
    local = dt.astimezone(TZ_SP)
    return {
        "dateTime": local.strftime("%Y-%m-%dT%H:%M:%S"),
        "timeZone": "America/Sao_Paulo",
    }


def normalize_calendar_action(action: dict) -> dict:
    """Prepara uma sugestão da IA (title, start, end) antes de criar o evento."""
    return {
        **action,
        "start": normalize_datetime_iso(str(action["start"])),
        "end": normalize_datetime_iso(str(action["end"])),
    }


def create_event(
    db: Session,
    user_id: int,
    *,
    title: str,
    start: str,
    end: str,
    description: str | None = None,
) -> dict:
    """Insere um novo evento no calendário principal do usuário."""
    start_norm = normalize_datetime_iso(start)
    end_norm = normalize_datetime_iso(end)
    if datetime.fromisoformat(end_norm) <= datetime.fromisoformat(start_norm):
        raise ValueError("O horário de término deve ser depois do início.")

    service = get_calendar_service(db, user_id)
    body: dict = {
        "summary": title,
        "start": _event_datetime_payload(start_norm),
        "end": _event_datetime_payload(end_norm),
    }
    if description:
        body["description"] = description

    return service.events().insert(calendarId="primary", body=body).execute()


def update_event(
    db: Session,
    user_id: int,
    event_id: str,
    *,
    title: str | None = None,
    start: str | None = None,
    end: str | None = None,
    description: str | None = None,
) -> dict:
    """Atualiza um evento existente (disponível na API; a UI ainda não usa)."""
    service = get_calendar_service(db, user_id)
    existing = service.events().get(calendarId="primary", eventId=event_id).execute()

    if title:
        existing["summary"] = title
    if description is not None:
        existing["description"] = description
    if start:
        existing["start"] = _event_datetime_payload(start)
    if end:
        existing["end"] = _event_datetime_payload(end)

    return (
        service.events()
        .update(calendarId="primary", eventId=event_id, body=existing)
        .execute()
    )


def format_event_line(event: dict) -> str:
    """Uma linha legível para exibir na barra lateral ou no prompt da IA."""
    start_dt = _parse_event_start(event)
    if start_dt:
        if start_dt.tzinfo:
            start_dt = start_dt.astimezone()
        when = start_dt.strftime("%d/%m/%Y %H:%M")
        if event.get("start", {}).get("date") and not event.get("start", {}).get("dateTime"):
            when = start_dt.strftime("%d/%m/%Y") + " (dia inteiro)"
    else:
        when = "data não informada"

    title = event.get("summary", "(sem título)")
    location = event.get("location")
    description = (event.get("description") or "").strip()
    line = f"- {when}: {title}"
    if location:
        line += f" | Local: {location}"
    if description:
        short = description[:120] + ("..." if len(description) > 120 else "")
        line += f" | Detalhe: {short}"
    return line


def format_events_for_prompt(events: list[dict]) -> str:
    """Texto com todos os eventos para o Gemini usar como contexto."""
    if not events:
        return "Nenhum compromisso encontrado nos próximos dias no Google Calendar."

    lines = [format_event_line(e) for e in events]
    return "Compromissos do Google Calendar (próximos dias):\n" + "\n".join(lines)


def format_action_label(action: dict) -> str:
    """Texto curto para o botão 'Criar: ...' na interface."""
    title = action.get("title", "Evento")
    start = action.get("start", "")[:16].replace("T", " ")
    end = action.get("end", "")[:16].replace("T", " ")
    return f"{title} ({start} → {end})"


def disconnect(db: Session, user_id: int) -> None:
    """Remove o token salvo do usuário — precisa entrar com Google de novo pra reconectar."""
    row = db.get(GoogleCredential, user_id)
    if row is not None:
        db.delete(row)
        db.commit()
