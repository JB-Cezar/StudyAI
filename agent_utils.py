"""
Utilitários do agente StudyAI.

A IA pode incluir no final da resposta um bloco oculto [STUDYAI_CALENDAR] com JSON
de eventos sugeridos. Este módulo extrai esse JSON e remove o bloco do texto exibido.
"""
 
from __future__ import annotations

import json
import re

# Marcadores que o prompt pede para o Gemini usar
CALENDAR_START = "[STUDYAI_CALENDAR]"
CALENDAR_END = "[/STUDYAI_CALENDAR]"


def extract_calendar_actions(text: str) -> tuple[str, list[dict]]:
    """
    Separa a resposta da IA em:
    - texto_visivel: o que o estudante lê no chat (sem o JSON)
    - acoes: lista de dicts {title, start, end, description?} para os botões Criar

    Se o JSON estiver mal formatado, devolve só o texto visível e lista vazia.
    """
    pattern = re.compile(
        re.escape(CALENDAR_START) + r"(.*?)" + re.escape(CALENDAR_END),
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return text.strip(), []

    visible = (text[: match.start()] + text[match.end() :]).strip()
    raw = match.group(1).strip()
    if not raw:
        return visible, []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return visible, []

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return visible, []

    actions = []
    for item in data:
        if isinstance(item, dict) and item.get("title") and item.get("start") and item.get("end"):
            try:
                import calendar_service as cal

                # Normaliza datas antes de mostrar no botão e criar no Google
                actions.append(cal.normalize_calendar_action(item))
            except Exception:
                actions.append(item)
    return visible, actions
