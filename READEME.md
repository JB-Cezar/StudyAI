# StudyAI

## Como rodar (importante)

Use o ambiente virtual `.venv`. Se rodar só `python3` do Mac, dá erro de biblioteca faltando.

```bash
cd /Users/furyos02/Documents/mindustry/StudyAI
source .venv/bin/activate
python3 -m streamlit run app2.py
```

Ou:

```bash
chmod +x run.sh
./run.sh
```

## Arquivos que você precisa ter

| Arquivo | Onde |
|---------|------|
| `.streamlit/secrets.toml` | Chave `GEMINI_API_KEY` |
| `credentials.json` | Raiz do projeto (Google Cloud) |

`token.json` aparece sozinho depois de conectar o calendário no app.

## Recursos do agente

- **Memória:** a conversa continua até clicar em *Nova conversa* (barra lateral).
- **Calendário leitura:** conectar e marcar *Usar calendário nas respostas*.
- **Calendário escrita:** reconectar com *Pedir permissão para criar/alterar eventos*; confirme sugestões com o botão *Criar*.

Guia completo: `SETUP_CALENDAR.md`
