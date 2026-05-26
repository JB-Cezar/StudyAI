#!/bin/bash
# Sempre usa o ambiente virtual do projeto (evita erro de biblioteca faltando)
cd "$(dirname "$0")"
source .venv/bin/activate
python3 -m streamlit run app2.py
