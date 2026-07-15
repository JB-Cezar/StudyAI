# StudyAI

Assistente de estudos com chat (Gemini) e integração com Google Calendar.

Arquitetura: **React + Vite** (frontend) e **FastAPI** (backend). O antigo protótipo em
Streamlit foi migrado e removido — toda a lógica (chat, calendário, parsing de sugestões de
evento) vive agora em `backend/app/`.

## Como rodar

Use o ambiente virtual em `~/.venvs/studyai` (fora da pasta do projeto, que está sincronizada
pelo iCloud Drive — manter o venv dentro do iCloud deixa a instalação e a inicialização muito
lentas, pois cada arquivo é baixado sob demanda). Se rodar só `python3` do Mac, dá erro de
biblioteca faltando.

### Banco de dados (MySQL)

Precisa do MySQL rodando localmente (`brew install mysql && brew services start mysql`). Depois,
uma vez só:

```bash
cd /Users/furyos02/Documents/mindustry/StudyAI
mysql -u root < database/create_user.sql   # cria o usuário studyai (não usar root no app)
mysql -u root < database/schema.sql        # cria o banco e as tabelas
```

### Backend (FastAPI)

```bash
cd /Users/furyos02/Documents/mindustry/StudyAI
./backend/run.sh
```
Sobe em `http://localhost:8000` (`/health` para checar; `/docs` para a documentação interativa).

### Frontend (React + Vite)

```bash
cd /Users/furyos02/Documents/mindustry/StudyAI/frontend
npm install   # só na primeira vez
npm run dev
```
Sobe em `http://localhost:5173`.

## Arquivos que você precisa ter

| Arquivo | Onde |
|---------|------|
| `backend/.env` | `GEMINI_API_KEY`, `DATABASE_URL`, `GOOGLE_CLIENT_ID`/`SECRET`, `JWT_SECRET` (copie de `backend/.env.example`) |

Não existe mais `credentials.json`/`token.json` — login e Google Calendar usam o mesmo cliente
OAuth Web (`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`), e o token de cada usuário fica no MySQL.

## Recursos do agente

- **Login:** obrigatório para usar o chat — "Entrar com Google" já pede acesso ao Calendar na
  mesma tela de consentimento.
- **Multiusuário:** cada usuário tem seu próprio histórico de conversa e seu próprio calendário.
- **Memória:** a conversa persiste no MySQL (`conversations`/`messages`), isolada por usuário, e
  sobrevive a reinícios do backend. *Nova conversa* (barra lateral) começa uma conversa nova — a
  anterior continua salva no banco.
- **Calendário:** ative *Usar calendário nas respostas* para o StudyAI ler sua agenda, e *IA pode
  sugerir eventos para criar* para poder confirmar sugestões com o botão *Criar*.

Guia completo do Google Calendar: `SETUP_CALENDAR.md`
