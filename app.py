import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="StudyAI",
    page_icon="📚",
    layout="centered"
)

# Título
st.title("📚 StudyAI")
st.subheader("Assistente Inteligente para Organização de Estudos")

st.write("Adicione suas tarefas acadêmicas abaixo.")

# Matéria
materia = st.text_input("📖 Matéria")

# Tarefa
tarefa = st.text_input("📝 Atividades")

# Data
st.write("📅 Data de entrega")

col1, col2, col3 = st.columns(3)

with col1:
    dia = st.selectbox("Dia", range(1, 32))

with col2:
    mes = st.selectbox("Mês", range(1, 13))

with col3:
    ano = st.selectbox("Ano", range(2025, 2031))

# Formatação da data
data_formatada = f"{dia:02d}/{mes:02d}/{ano}"

# Prioridade
prioridade = st.selectbox(
    "⚠️ Prioridade",
    ["Baixa", "Média", "Alta"]
)

# Botão
if st.button("Adicionar tarefa"):

    # Data atual
    hoje = datetime.now()

    # Data da tarefa
    data_tarefa = datetime(ano, mes, dia)

    # Verificação de data
    if data_tarefa.date() < hoje.date():

        st.error("❌ Não é possível cadastrar tarefas em datas que já passaram.")

    else:

        st.success("✅ Tarefa adicionada com sucesso!")

        st.write("## 📋 Informações da tarefa")

        st.write(f"📖 Matéria: {materia}")
        st.write(f"📝 Atividade: {tarefa}")
        st.write(f"📅 Data: {data_formatada}")
        st.write(f"⚠️ Prioridade: {prioridade}")

        # Organização inteligente
        st.write("## 🧠 Organização Inteligente")

        if prioridade == "Alta":
            st.error("⚠️ Esta tarefa possui prioridade ALTA. Recomenda-se iniciar os estudos imediatamente.")

        elif prioridade == "Média":
            st.warning("📚 Esta tarefa possui prioridade MÉDIA. Organize um horário de estudo nos próximos dias.")

        else:
            st.info("✅ Esta tarefa possui prioridade BAIXA. Planeje os estudos com tranquilidade.")