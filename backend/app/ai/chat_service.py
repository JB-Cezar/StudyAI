"""
Orquestração do chat do StudyAI: histórico + contexto do calendário + Gemini.

O histórico persiste no MySQL (tabelas `conversations`/`messages`), isolado
por usuário logado (`conversations.user_id`) — cada usuário só vê e continua
a própria conversa.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calendar import service as cal
from app.chat.parser import extract_calendar_actions
from app.db.models import Conversation, Message

from . import gemini_client as gemini

_model: object | None = None
_active_conversation_ids: dict[int, int] = {}


def get_model():
    """Cria o modelo Gemini uma vez e reaproveita nas chamadas seguintes."""
    global _model
    if _model is None:
        _model = gemini.configurar_gemini()
        if _model is None:
            raise RuntimeError(
                "GEMINI_API_KEY não configurada. Defina a variável de ambiente "
                "ou crie backend/.env."
            )
    return _model


def _get_active_conversation_id(db: Session, user_id: int) -> int:
    """
    Devolve o id da conversa ativa deste usuário, retomando a mais recente do
    banco após um reinício do backend (em vez de sempre começar do zero).
    """
    if user_id in _active_conversation_ids:
        return _active_conversation_ids[user_id]

    ultima = db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if ultima is None:
        ultima = Conversation(user_id=user_id)
        db.add(ultima)
        db.commit()
        db.refresh(ultima)

    _active_conversation_ids[user_id] = ultima.id
    return ultima.id


def get_history(db: Session, user_id: int) -> list[dict[str, str]]:
    conversation_id = _get_active_conversation_id(db, user_id)
    mensagens = db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)
    ).scalars()
    return [{"role": m.role, "content": m.content} for m in mensagens]


def reset_history(db: Session, user_id: int) -> None:
    """Cria uma nova conversa para o usuário (a anterior continua salva no banco)."""
    nova = Conversation(user_id=user_id)
    db.add(nova)
    db.commit()
    db.refresh(nova)
    _active_conversation_ids[user_id] = nova.id


def montar_contexto_calendario(db: Session, user_id: int, usar: bool, permitir_criar: bool) -> str:
    """
    Monta texto com a agenda do Google e, se permitido, instruções para a IA
    sugerir eventos no bloco [STUDYAI_CALENDAR]. Anexado à mensagem do
    usuário antes de enviar ao Gemini.
    """
    if not usar or not cal.is_authenticated(db, user_id):
        return ""

    try:
        eventos = cal.list_upcoming_events(db, user_id)
    except Exception:
        eventos = []

    partes = []
    if eventos:
        partes.append(
            "--- AGENDA ATUAL (Google Calendar) ---\n"
            + cal.format_events_for_prompt(eventos)
            + "\n--- FIM DA AGENDA ---"
        )
    else:
        partes.append(
            "O Google Calendar está conectado, mas não há eventos nos próximos dias."
        )

    if permitir_criar and cal.has_write_access(db, user_id):
        partes.append(gemini.calendar_write_instructions())

    return "\n\n".join(partes)


def send_message(
    db: Session,
    user_id: int,
    texto_usuario: str,
    *,
    usar_calendario: bool,
    permitir_criar: bool,
) -> tuple[str, list[dict]]:
    """
    Envia a mensagem ao Gemini com histórico da conversa deste usuário +
    contexto do calendário. Levanta a exceção original em caso de falha (sem
    gravar a mensagem do usuário no histórico).

    Retorna (texto_visivel, acoes) — o bloco [STUDYAI_CALENDAR], se houver,
    já vem extraído e nunca é salvo no histórico nem devolvido no texto: o
    Gemini só deve ver o texto visível nas próximas rodadas, do contrário o
    JSON cru poluiria o contexto da conversa.
    """
    modelo = get_model()
    conversation_id = _get_active_conversation_id(db, user_id)

    extra = montar_contexto_calendario(db, user_id, usar_calendario, permitir_criar)
    mensagem_api = texto_usuario
    if extra:
        mensagem_api = f"{extra}\n\nMensagem do estudante:\n{texto_usuario}"

    history = gemini.historico_para_gemini(get_history(db, user_id))

    chat = modelo.start_chat(history=history)
    resposta = chat.send_message(mensagem_api)

    texto_visivel, acoes = extract_calendar_actions(resposta.text)

    db.add(Message(conversation_id=conversation_id, role="user", content=texto_usuario))
    db.add(Message(conversation_id=conversation_id, role="assistant", content=texto_visivel))
    db.commit()

    if acoes and not cal.has_write_access(db, user_id):
        acoes = []
    return texto_visivel, acoes
