#!/bin/bash
# Sobe a API FastAPI (nova arquitetura) em paralelo ao Streamlit legado.
# Usa o venv em ~/.venvs/studyai (fora do iCloud Drive — evita lentidão de sincronização)
cd "$(dirname "$0")"
source ~/.venvs/studyai/bin/activate
python3 -m uvicorn app.main:app --reload --port 8000
