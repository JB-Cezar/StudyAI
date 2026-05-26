"""
Integração com Google Calendar para o StudyAI.
 
Responsável por:
- Login OAuth (credentials.json + token.json)
- Ler eventos da agenda
- Criar/atualizar eventos (com permissão de escrita)
- Normalizar datas que a IA envia em formatos inválidos
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Fuso horário usado nos eventos (Brasil)
TZ_SP = ZoneInfo("America/Sao_Paulo")

# Caminhos dos arquivos na pasta do projeto
BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"  # baixado do Google Cloud Console
TOKEN_FILE = BASE_DIR / "token.json"  # gerado após o usuário autorizar no navegador

# Escopos OAuth: só leitura ou leitura + escrita
SCOPES_READONLY = ["https://www.googleapis.com/auth/calendar.readonly"]
SCOPES_WRITE = ["https://www.googleapis.com/auth/calendar"]


class CalendarNotConfiguredError(Exception):
    """credentials.json ausente ou inválido."""


class CalendarAuthError(Exception):
    """Falha na autenticação OAuth."""


def credentials_configured() -> bool:
    """Verifica se o arquivo credentials.json existe na pasta do projeto."""
    return CREDENTIALS_FILE.is_file()


def _load_token_creds() -> Credentials | None:
    """Carrega o token salvo após o login (sem forçar escopo na leitura)."""
    if not TOKEN_FILE.is_file():
        return None
    try:
        return Credentials.from_authorized_user_file(str(TOKEN_FILE))
    except Exception:
        return None


def has_write_access() -> bool:
    """True se o usuário autorizou criar/editar eventos (não só ler)."""
    creds = _load_token_creds()
    if not creds:
        return False
    scopes = set(creds.scopes or [])
    return "https://www.googleapis.com/auth/calendar" in scopes


def is_authenticated() -> bool:
    """True se já existe token.json válido ou renovável."""
    creds = _load_token_creds()
    if not creds:
        return False
    return creds.valid or bool(creds.refresh_token)


def get_credentials(*, interactive: bool = True, write: bool = False) -> Credentials:
    """
    Obtém credenciais Google: usa token.json, renova se expirou ou abre o navegador (OAuth).
    write=True pede permissão para criar eventos; pode exigir reconectar se o token antigo
    foi criado só com leitura.
    """
    if not credentials_configured():
        raise CalendarNotConfiguredError(
            "Coloque o arquivo credentials.json na pasta do projeto. "
            "Veja SETUP_CALENDAR.md para instruções."
        )

    scopes = SCOPES_WRITE if write else SCOPES_READONLY
    creds = None
    if TOKEN_FILE.is_file():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), scopes)
        except Exception:
            creds = None

    if creds and creds.valid:
        if write and not has_write_access():
            if not interactive:
                raise CalendarAuthError(
                    "Permissão de escrita ausente. Desconecte e conecte de novo "
                    "com a opção de criar eventos ativada."
                )
        elif not write or has_write_access():
            return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        if not write or has_write_access():
            return creds

    if not interactive:
        raise CalendarAuthError(
            "Calendário não conectado. Clique em 'Conectar Google Calendar' na barra lateral."
        )

    # Primeira vez ou token inválido: login no navegador
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), scopes)
    creds = flow.run_local_server(port=0)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds


def get_calendar_service(*, interactive: bool = True, write: bool = False):
    """Retorna o cliente da API Google Calendar v3."""
    creds = get_credentials(interactive=interactive, write=write)
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
    *,
    days_ahead: int = 14,
    max_results: int = 20,
    interactive: bool = True,
) -> list[dict]:
    """Lista eventos do calendário principal nos próximos N dias."""
    service = get_calendar_service(interactive=interactive, write=False)
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
    *,
    title: str,
    start: str,
    end: str,
    description: str | None = None,
    interactive: bool = True,
) -> dict:
    """Insere um novo evento no calendário principal do usuário."""
    start_norm = normalize_datetime_iso(start)
    end_norm = normalize_datetime_iso(end)
    if datetime.fromisoformat(end_norm) <= datetime.fromisoformat(start_norm):
        raise ValueError("O horário de término deve ser depois do início.")

    service = get_calendar_service(interactive=interactive, write=True)
    body: dict = {
        "summary": title,
        "start": _event_datetime_payload(start_norm),
        "end": _event_datetime_payload(end_norm),
    }
    if description:
        body["description"] = description

    return (
        service.events()
        .insert(calendarId="primary", body=body)
        .execute()
    )


def update_event(
    event_id: str,
    *,
    title: str | None = None,
    start: str | None = None,
    end: str | None = None,
    description: str | None = None,
    interactive: bool = True,
) -> dict:
    """Atualiza um evento existente (disponível na API; a UI ainda não usa)."""
    service = get_calendar_service(interactive=interactive, write=True)
    existing = (
        service.events().get(calendarId="primary", eventId=event_id).execute()
    )

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


def disconnect() -> None:
    """Remove token.json — força novo login na próxima conexão."""
    if TOKEN_FILE.is_file():
        TOKEN_FILE.unlink()
