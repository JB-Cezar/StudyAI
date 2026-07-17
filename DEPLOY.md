# Deploy em produção

Caminho escolhido: **Vercel** (frontend) + **Render** (backend) + **Aiven** (MySQL), todos com
plano gratuito. Ordem importa — cada peça depende da URL da anterior.

## 1. Banco de dados (Aiven MySQL)

1. Crie conta em [aiven.io](https://aiven.io/) (tem plano "Free" sem cartão).
2. Crie um serviço **MySQL** (o Free tier já vem selecionado num desses planos).
3. Espere o serviço ficar "Running" e copie a **Service URI** (formato
   `mysql://usuario:senha@host:porta/defaultdb`).
4. Rode o schema contra esse banco (do seu computador):
   ```bash
   mysql -h <host> -P <porta> -u <usuario> -p<senha> < database/schema.sql
   ```

## 2. Backend (Render)

1. Crie conta em [render.com](https://render.com/) (dá pra logar com GitHub).
2. **New** → **Web Service** → conecte o repositório `StudyAI`.
3. Configurações:
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Variáveis de ambiente (aba **Environment**):
   ```
   GEMINI_API_KEY=...
   DATABASE_URL=mysql+pymysql://usuario:senha@host:porta/defaultdb   # do Aiven, troca mysql:// por mysql+pymysql://
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   GOOGLE_LOGIN_REDIRECT_URI=https://SEU-APP.onrender.com/auth/google/callback
   FRONTEND_URL=https://SEU-APP.vercel.app   # ainda não existe — volte aqui depois do passo 3
   JWT_SECRET=...
   ENVIRONMENT=production
   ```
5. Deploy. Anote a URL que o Render gerar (algo como `https://studyai-backend.onrender.com`).

## 3. Frontend (Vercel)

1. Crie conta em [vercel.com](https://vercel.com/) (login com GitHub).
2. **Add New** → **Project** → importe o repositório `StudyAI`.
3. **Root Directory:** `frontend` (a Vercel detecta Vite automaticamente).
4. Variável de ambiente: `VITE_API_BASE_URL=https://SEU-APP.onrender.com` (URL do Render, passo 2).
5. Deploy. Anote a URL (`https://studyai-xxxx.vercel.app`).

## 4. Fechar o círculo

1. No **Google Cloud Console** → Credenciais → seu Client OAuth "Aplicativo da Web":
   - Origens JavaScript autorizadas: adicione `https://SEU-APP.vercel.app`
   - URIs de redirecionamento: adicione `https://SEU-APP.onrender.com/auth/google/callback`
2. No **Render**, atualize `FRONTEND_URL` com a URL real da Vercel (passo 3) e `GOOGLE_LOGIN_REDIRECT_URI` se necessário. Redeploy.
3. Abra a URL da Vercel, clique em **Entrar com Google**, confirme que o fluxo completo funciona.

## Observações

- Plano gratuito do Render "dorme" o serviço depois de inatividade — a primeira requisição depois
  de um tempo pode demorar ~30s.
- **O Aiven Free também desliga sozinho por inatividade** (aconteceu em produção: login parou de
  funcionar com "Internal Server Error" cru, sem pista nenhuma). Diagnóstico: `dig
  <host-do-aiven>` não resolve nada quando o serviço está desligado. Solução: painel do Aiven →
  o serviço → botão **"Power on"**/"Start" — demora alguns minutos pra voltar (recria a máquina),
  os dados continuam intactos. Depois disso, teste com
  `mysql -h <host> -P <porta> -u avnadmin -p<senha> --ssl-mode=REQUIRED -e "SELECT 1;"` antes de
  assumir que voltou.
- `ENVIRONMENT=production` no backend ativa CORS restrito ao `FRONTEND_URL` exato e cookies
  `Secure` + `SameSite=None` (necessário porque Vercel e Render são domínios diferentes).
- **Limite de taxa da chave gratuita do Gemini**: poucas requisições por minuto já derrubam com
  `429 TooManyRequests`. Com vários usuários testando ao mesmo tempo, isso aparece como erro no
  chat. Ativar faturamento no projeto do Google Cloud aumenta bastante o limite (a cota gratuita
  mensal geralmente cobre o uso, mesmo com faturamento ativo).
