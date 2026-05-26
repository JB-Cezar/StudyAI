"""
StudyAI — aplicativo principal (app2.py).

Interface Streamlit + agente conversacional (Gemini) + Google Calendar.
A conversa fica em st.session_state (memória da sessão), não em banco de dados.
"""

import os
from datetime import datetime

import google.generativeai as genai
import streamlit as st

import agent_utils as agent
import calendar_service as cal

# Data de hoje injetada nos prompts para a IA não sugerir anos passados
HOJE = datetime.now().strftime("%Y-%m-%d")

# Instruções fixas do agente (personalidade e formato de resposta)
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

# Texto extra enviado à IA quando o usuário autorizou criar eventos no calendário
CALENDAR_WRITE_INSTRUCTIONS = f"""
O estudante autorizou CRIAR eventos no Google Calendar.
Data de hoje: {HOJE}. Use SEMPRE o ano e datas corretos (futuro próximo), nunca anos passados.
Quando combinar blocos de estudo concretos (datas e horários), inclua NO FINAL da resposta
(exatamente neste formato, JSON válido):
[STUDYAI_CALENDAR]
[{{"title": "Estudar Cálculo", "start": "{HOJE}T10:00:00-03:00", "end": "{HOJE}T12:00:00-03:00", "description": "Revisão"}}]
[/STUDYAI_CALENDAR]
Regras do bloco:
- Só inclua quando sugerir eventos novos para criar (máximo 5);
- Formato obrigatório: AAAA-MM-DDTHH:MM:SS-03:00 (com T, nunca espaço entre data e hora);
- Use fuso -03:00 (America/Sao_Paulo);
- O texto visível para o estudante deve fazer sentido sem mencionar o bloco JSON;
- Não inclua o bloco em toda mensagem — só quando houver agendamento concreto."""

st.set_page_config(
    page_title="StudyAI",
    page_icon="🧠",
    layout="centered",
)


# =============================================================================
# CONFIGURAÇÃO DA API GEMINI
# =============================================================================


def obter_chave_gemini() -> str | None:
    """Lê a chave da API: primeiro secrets.toml, depois variável de ambiente."""
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.getenv("GEMINI_API_KEY")


def configurar_gemini() -> genai.GenerativeModel | None:
    """Cria o modelo Gemini com o prompt de sistema (StudyAI)."""
    chave = obter_chave_gemini()
    if not chave:
        return None
    genai.configure(api_key=chave)
    return genai.GenerativeModel(
        "gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )


# =============================================================================
# MEMÓRIA DA CONVERSA E INTEGRAÇÃO COM A IA
# =============================================================================


def historico_para_gemini(mensagens: list[dict]) -> list[dict]:
    """
    Converte mensagens do Streamlit para o formato do chat do Gemini.
    role: 'user' ou 'model' (assistente).
    """
    history = []
    for msg in mensagens:
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [msg["content"]]})
    return history


def montar_contexto_calendario(usar: bool, permitir_criar: bool) -> str:
    """
    Monta texto com a agenda do Google e, se permitido, instruções para a IA
    sugerir eventos no bloco [STUDYAI_CALENDAR].
    Esse texto é anexado à mensagem do usuário antes de enviar ao Gemini.
    """
    if not usar or not st.session_state.calendario_conectado:
        return ""

    partes = []
    if st.session_state.eventos_calendario:
        partes.append(
            "--- AGENDA ATUAL (Google Calendar) ---\n"
            + cal.format_events_for_prompt(st.session_state.eventos_calendario)
            + "\n--- FIM DA AGENDA ---"
        )
    else:
        partes.append(
            "O Google Calendar está conectado, mas não há eventos nos próximos dias."
        )

    if permitir_criar and cal.has_write_access():
        partes.append(CALENDAR_WRITE_INSTRUCTIONS)

    return "\n\n".join(partes)


def enviar_mensagem(
    modelo: genai.GenerativeModel,
    texto_usuario: str,
    *,
    usar_calendario: bool,
    permitir_criar: bool,
) -> str:
    """
    Envia a mensagem ao Gemini com histórico da sessão + contexto do calendário.
    A memória da conversa vem de st.session_state.mensagens (não é banco SQL).
    """
    extra = montar_contexto_calendario(usar_calendario, permitir_criar)
    mensagem_api = texto_usuario
    if extra:
        mensagem_api = f"{extra}\n\nMensagem do estudante:\n{texto_usuario}"

    # Todas as mensagens exceto a última (ainda sendo enviada) formam o histórico
    history = historico_para_gemini(st.session_state.mensagens[:-1])
    chat = modelo.start_chat(history=history)
    resposta = chat.send_message(mensagem_api)
    return resposta.text


def atualizar_agenda() -> None:
    """Busca na API os próximos eventos e guarda em session_state (cache da sessão)."""
    st.session_state.eventos_calendario = cal.list_upcoming_events(interactive=False)


def criar_evento_pendente(indice: int) -> None:
    """
    Callback do botão 'Criar: ...'.
    Roda quando o usuário confirma uma sugestão da IA; grava no Google Calendar.
    """
    acoes = st.session_state.get("acoes_pendentes", [])
    if indice < 0 or indice >= len(acoes):
        st.session_state.calendario_feedback = (
            "error",
            "Sugestão não encontrada. Peça ao StudyAI de novo.",
        )
        return
 
    acao = acoes[indice]
    try:
        evento = cal.create_event(
            title=acao["title"],
            start=acao["start"],
            end=acao["end"],
            description=acao.get("description"),
            interactive=False,
        )
        acoes.pop(indice)
        st.session_state.acoes_pendentes = acoes
        atualizar_agenda()
        link = evento.get("htmlLink", "")
        quando = cal.format_action_label(acao)
        st.session_state.calendario_feedback = (
            "success",
            f"Evento criado: {acao['title']} ({quando})",
            link,
        )
    except Exception as e:
        st.session_state.calendario_feedback = (
            "error",
            f"Não foi possível criar o evento: {e}",
        )


# =============================================================================
# ESTADO DA SESSÃO (memória temporária — como “sessão/cookie” no servidor)
# =============================================================================
# Some ao fechar o navegador, reiniciar o Streamlit ou clicar em Nova conversa.

if "mensagens" not in st.session_state:
    st.session_state.mensagens = []  # histórico do chat [{role, content}, ...]
if "acoes_pendentes" not in st.session_state:
    st.session_state.acoes_pendentes = []  # eventos sugeridos pela IA aguardando clique
if "calendario_feedback" not in st.session_state:
    st.session_state.calendario_feedback = None  # mensagem após criar evento (sucesso/erro)
if "eventos_calendario" not in st.session_state:
    st.session_state.eventos_calendario = []  # cópia dos eventos lidos da API
if "calendario_conectado" not in st.session_state:
    st.session_state.calendario_conectado = cal.is_authenticated()

usar_calendario = False
permitir_criar_eventos = False

# =============================================================================
# BARRA LATERAL — conversa e Google Calendar
# =============================================================================

with st.sidebar:
    st.header("💬 Conversa")
    if st.button("Nova conversa", use_container_width=True):
        # Zera a memória do chat nesta sessão
        st.session_state.mensagens = []
        st.session_state.acoes_pendentes = []
        st.rerun()

    st.caption(
        f"{len(st.session_state.mensagens)} mensagem(ns) nesta sessão. "
        "O agente lembra o que você disse até clicar em Nova conversa."
    )

    st.divider()
    st.header("📅 Google Calendar")

    if not cal.credentials_configured():
        st.warning("Arquivo `credentials.json` não encontrado. Veja SETUP_CALENDAR.md.")
    else:
        if st.session_state.calendario_conectado or cal.is_authenticated():
            st.success("Calendário conectado")
            if cal.has_write_access():
                st.caption("Permissão de leitura e escrita ativa.")
            else:
                st.caption("Somente leitura. Ative criar eventos e reconecte.")

            if st.button("🔄 Atualizar eventos"):
                try:
                    atualizar_agenda()
                    st.session_state.calendario_conectado = True
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

            if st.button("Desconectar"):
                # Apaga token.json — exige novo login OAuth
                cal.disconnect()
                st.session_state.calendario_conectado = False
                st.session_state.eventos_calendario = []
                st.rerun()
        else:
            permitir_criar_eventos = st.checkbox(
                "Pedir permissão para criar/alterar eventos",
                value=True,
                help="Marque antes de conectar. Exige novo login no Google.",
            )
            if st.button("🔗 Conectar Google Calendar"):
                try:
                    # Abre o navegador para OAuth; salva token.json
                    cal.get_credentials(
                        interactive=True,
                        write=permitir_criar_eventos,
                    )
                    st.session_state.eventos_calendario = cal.list_upcoming_events(
                        interactive=False
                    )
                    st.session_state.calendario_conectado = True
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        if st.session_state.calendario_conectado:
            usar_calendario = st.checkbox(
                "Usar calendário nas respostas",
                value=True,
            )
            permitir_criar_eventos = st.checkbox(
                "IA pode sugerir eventos para criar",
                value=cal.has_write_access(),
                disabled=not cal.has_write_access(),
            )
            if permitir_criar_eventos and not cal.has_write_access():
                st.warning(
                    "Desconecte e conecte de novo com a opção de criar eventos "
                    "marcada **antes** de clicar em Conectar."
                )

            if not st.session_state.eventos_calendario:
                try:
                    atualizar_agenda()
                except Exception:
                    pass

            if st.session_state.eventos_calendario:
                with st.expander("Próximos compromissos"):
                    for evento in st.session_state.eventos_calendario:
                        st.markdown(cal.format_event_line(evento))

            # Formulário alternativo: criar evento sem passar pela sugestão da IA
            if cal.has_write_access():
                with st.expander("Criar evento manualmente"):
                    titulo = st.text_input("Título", key="evt_titulo")
                    col1, col2 = st.columns(2)
                    with col1:
                        data = st.date_input("Data", key="evt_data")
                        hora_inicio = st.time_input("Início", key="evt_ini")
                    with col2:
                        hora_fim = st.time_input("Fim", key="evt_fim")
                    desc = st.text_area("Descrição (opcional)", key="evt_desc")
                    if st.button("Criar no calendário"):
                        if not titulo.strip():
                            st.warning("Informe um título.")
                        else:
                            start = (
                                f"{data.isoformat()}T{hora_inicio.isoformat()}-03:00"
                            )
                            end = f"{data.isoformat()}T{hora_fim.isoformat()}-03:00"
                            try:
                                cal.create_event(
                                    title=titulo.strip(),
                                    start=start,
                                    end=end,
                                    description=desc.strip() or None,
                                )
                                atualizar_agenda()
                                st.success("Evento criado.")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

# =============================================================================
# ÁREA PRINCIPAL — chat e envio de mensagens
# =============================================================================

modelo = configurar_gemini()
if modelo is None:
    st.error(
        "Configure `GEMINI_API_KEY` em `.streamlit/secrets.toml` ou variável de ambiente."
    )
    st.stop()

st.title("🧠 StudyAI")
st.subheader("Assistente Inteligente para Organização de Estudos")
st.caption(
    "Conversa contínua + integração com Google Calendar. "
    "Peça ajuda para organizar a semana ou agendar blocos de estudo."
)

# Feedback de criação de evento (uma exibição após o clique em Criar)
if st.session_state.calendario_feedback:
    nivel, texto, *extra = st.session_state.calendario_feedback
    if nivel == "success":
        st.success(texto)
        if extra and extra[0]:
            st.link_button("Abrir no Google Calendar", extra[0])
    else:
        st.error(texto)
    st.session_state.calendario_feedback = None

# Redesenha todas as mensagens salvas na sessão
for msg in st.session_state.mensagens:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Botões para confirmar sugestões de eventos vindas da última resposta da IA
if st.session_state.acoes_pendentes:
    st.subheader("📅 Sugestões para o calendário")
    st.caption(
        "Confirme antes de criar — nada é salvo sem seu clique. "
        "Os eventos vão para o calendário principal da sua conta Google."
    )
    for i, acao in enumerate(st.session_state.acoes_pendentes):
        label = cal.format_action_label(acao)
        st.button(
            f"Criar: {label}",
            key=f"criar_evt_{i}_{acao.get('title', '')[:20]}",
            on_click=criar_evento_pendente,
            args=(i,),
            use_container_width=True,
        )

prompt_usuario = st.chat_input("Digite sua mensagem...")

if prompt_usuario:
    # 1) Guarda mensagem do usuário na memória da sessão
    st.session_state.mensagens.append(
        {"role": "user", "content": prompt_usuario.strip()}
    )

    try:
        # 2) Chama o Gemini com histórico + calendário
        with st.spinner("StudyAI está pensando..."):
            texto_bruto = enviar_mensagem(
                modelo,
                prompt_usuario.strip(),
                usar_calendario=usar_calendario,
                permitir_criar=permitir_criar_eventos and cal.has_write_access(),
            )

        # 3) Separa texto visível do bloco JSON de eventos (se houver)
        texto_visivel, acoes = agent.extract_calendar_actions(texto_bruto)
        st.session_state.mensagens.append(
            {"role": "assistant", "content": texto_visivel}
        )
        if acoes and cal.has_write_access():
            st.session_state.acoes_pendentes = acoes

        # 4) Recarrega a página para mostrar a nova mensagem no chat
        st.rerun()

    except Exception as erro:
        # Remove a mensagem do usuário se a API falhou
        st.session_state.mensagens.pop()
        st.error("❌ Erro ao gerar resposta.")
        st.exception(erro)
