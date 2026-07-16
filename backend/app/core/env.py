"""
Leitura de variáveis de ambiente com espaços/quebras de linha aparadas.

Colar um valor num painel de variáveis de ambiente (Render, etc.) às vezes
inclui um espaço ou "\\n" a mais sem querer. Para segredos usados em
cabeçalhos HTTP/gRPC (chave da API, client secret, JWT) ou em comparações
exatas de URL (redirect_uri, CORS), isso quebra silenciosamente — foi a causa
de um travamento real em produção (chave do Gemini com espaço colado gerando
"Illegal header value" no cliente gRPC, retry infinito sem erro visível).
"""

from __future__ import annotations

import os


def clean_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    return value.strip() if value else value
