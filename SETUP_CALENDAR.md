# Conectar o StudyAI ao Google Calendar

Este guia é para o projeto de **agentes de IA** da faculdade: o StudyAI lê sua agenda e usa provas, aulas e entregas reais nas respostas.

Desde a sub-etapa 8c da migração, **login e acesso ao Calendar acontecem juntos**: ao entrar
com Google, você já concede acesso ao Calendar na mesma tela — não existe mais um botão
separado de "Conectar Google Calendar". Cada usuário tem seu próprio token, guardado no MySQL
(não é mais um arquivo `token.json` único compartilhado).

## 1. Google Cloud — criar credenciais

1. Acesse [Google Cloud Console](https://console.cloud.google.com/).
2. Crie um projeto (ex.: `studyai-faculdade`).
3. Menu **APIs e serviços** → **Biblioteca** → busque **Google Calendar API** → **Ativar**.
4. **APIs e serviços** → **Tela de consentimento OAuth**:
   - Tipo: **Externo** (para testes com sua conta).
   - Preencha nome do app, e-mail de suporte e adicione seu e-mail como **usuário de teste**.
5. **Credenciais** → **Criar credenciais** → **ID do cliente OAuth**:
   - Tipo: **Aplicativo da Web**.
   - Origens JavaScript autorizadas: `http://localhost:5173`
   - URIs de redirecionamento autorizados: `http://localhost:8000/auth/google/callback`
6. Copie o **Client ID** e o **Client Secret** para `backend/.env` (copie de `backend/.env.example`):

```
GOOGLE_CLIENT_ID=seu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=seu-client-secret
GOOGLE_LOGIN_REDIRECT_URI=http://localhost:8000/auth/google/callback
FRONTEND_URL=http://localhost:5173
JWT_SECRET=gere-com-python3-c-import-secrets-print-secrets.token_hex(32)
```

> Não envie `backend/.env` para o Git (já está no `.gitignore`).

## 2. Chave do Gemini

No mesmo `backend/.env`:

```
GEMINI_API_KEY=sua-chave
```

## 3. Rodar o app

```bash
cd StudyAI
./backend/run.sh          # API em http://localhost:8000
```

Em outro terminal:

```bash
cd StudyAI/frontend
npm install                # só na primeira vez
npm run dev                # frontend em http://localhost:5173
```

Na **barra lateral**, clique em **Entrar com Google**. O Google sempre mostra a tela de
consentimento (mesmo se você já entrou antes) — isso é proposital, é o jeito de garantir que o
backend recebe um `refresh_token` válido para usar o Calendar depois que você fechar o navegador.

## 4. Como o agente usa o calendário

- Com a opção **Usar calendário nas respostas** ativa, o StudyAI recebe seus próximos eventos no prompt.
- Ele pode sugerir: o que estudar hoje, como dividir a semana, alertas de prova perto, etc.
- Os eventos aparecem em **Próximos compromissos** na barra lateral.

## Problemas comuns

| Erro | Solução |
|------|---------|
| `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` ausentes | Configure `backend/.env` (passo 1) |
| `access_denied` no login | Adicione seu Gmail em **Usuários de teste** na tela OAuth |
| `invalid_grant: Missing code verifier` | Bug de PKCE já corrigido — se aparecer nesse projeto, é regressão, não configuração |
| `Scope has changed` | A conta já tinha escopos concedidos a outro client_id do mesmo projeto; já mitigado (`OAUTHLIB_RELAX_TOKEN_SCOPE`) |
| `GEMINI_API_KEY` ausente | Configure `backend/.env` |

## Criar eventos no calendário

1. Na conversa, peça blocos de estudo; o StudyAI sugere horários e você confirma com **Criar: ...** antes de salvar.
2. Ou use **Criar evento manualmente** na barra lateral.
3. **Desconectar** apaga só o token do Calendar guardado no banco (você continua logado no app) — para reconectar, é só entrar com Google de novo.

## Memória da conversa

O agente lembra a conversa atual até você clicar em **Nova conversa** na barra lateral. Persiste
no MySQL, isolada por usuário — sobrevive a reinícios do backend.
