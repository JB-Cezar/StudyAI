"""
Configuração e prompts do agente StudyAI (Gemini).

Portado de backend/legacy/app2.py — mesma personalidade e mesmas regras do
bloco [STUDYAI_CALENDAR], só decoupled do Streamlit (chave vem só de variável
de ambiente, já que o backend não tem st.secrets) e a data de hoje passou a
ser calculada a cada chamada, não uma vez só na importação do módulo — o
processo do backend fica de pé por dias, e "hoje" fixo no import ficaria
desatualizado.
"""

from __future__ import annotations

from datetime import datetime

import google.generativeai as genai

from app.core.env import clean_env

SYSTEM_PROMPT = """Você é o StudyAI, um agente de IA acadêmico para estudantes que se
perdem nos estudos e nos trabalhos.

Especialidades:
- organização de estudos e cronogramas realistas;
- priorização de tarefas e provas;
- produtividade acadêmica;
- motivação e técnicas de aprendizagem;
- preparação para provas e gestão de prazos.

Diretrizes:
- Mantenha continuidade com o que o estudante já disse na conversa;
- Seja amigável, claro, organizado e motivador;
- Dê passos práticos (o que fazer hoje, amanhã e esta semana);
- Quando houver agenda, cruze compromissos com a mensagem do estudante;
- Avise sobre sobrecarga ou prazos apertados;
- Use listas e tópicos quando ajudar a leitura."""


def _hoje() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def calendar_write_instructions() -> str:
    """Texto extra enviado à IA quando o usuário autorizou criar eventos no calendário."""
    hoje = _hoje()
    return f"""
O estudante autorizou CRIAR eventos no Google Calendar.
Data de hoje: {hoje}. Use SEMPRE o ano e datas corretos (futuro próximo), nunca anos passados.
Quando combinar blocos de estudo concretos (datas e horários), inclua NO FINAL da resposta
(exatamente neste formato, JSON válido):
[STUDYAI_CALENDAR]
[{{"title": "Estudar Cálculo", "start": "{hoje}T10:00:00-03:00", "end": "{hoje}T12:00:00-03:00", "description": "Revisão"}}]
[/STUDYAI_CALENDAR]
Regras do bloco:
- Só inclua quando sugerir eventos novos para criar (máximo 5);
- Formato obrigatório: AAAA-MM-DDTHH:MM:SS-03:00 (com T, nunca espaço entre data e hora);
- Use fuso -03:00 (America/Sao_Paulo);
- O texto visível para o estudante deve fazer sentido sem mencionar o bloco JSON;
- Não inclua o bloco em toda mensagem — só quando houver agendamento concreto."""


def obter_chave_gemini() -> str | None:
    """Lê a chave da API da variável de ambiente GEMINI_API_KEY (já sem espaços/quebras de linha)."""
    return clean_env("GEMINI_API_KEY")


def configurar_gemini() -> genai.GenerativeModel | None:
    """
    Cria o modelo Gemini com o prompt de sistema (StudyAI).

    transport="rest": a biblioteca usa gRPC por padrão, mas isso causou um
    incidente real em produção (Render) — o canal gRPC falhava a validação
    de metadata (`plugin_credentials.cc: Illegal header value`) e ficava
    tentando de novo silenciosamente por minutos, sem erro visível nem pra
    quem estava usando o chat nem nos logs de erro do FastAPI. REST evita
    esse código de transporte problemático inteiramente.
    """
    chave = obter_chave_gemini()
    if not chave:
        return None
    genai.configure(api_key=chave, transport="rest")
    return genai.GenerativeModel(
        "gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )


def historico_para_gemini(mensagens: list[dict]) -> list[dict]:
    """
    Converte mensagens no formato interno ({role: 'user'|'assistant', content})
    para o formato do chat do Gemini (role: 'user'|'model').
    """
    history = []
    for msg in mensagens:
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [msg["content"]]})
    return history
