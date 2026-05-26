# Conectar o StudyAI ao Google Calendar

Este guia é para o projeto de **agentes de IA** da faculdade: o StudyAI lê sua agenda e usa provas, aulas e entregas reais nas respostas.

## 1. Google Cloud — criar credenciais

1. Acesse [Google Cloud Console](https://console.cloud.google.com/).
2. Crie um projeto (ex.: `studyai-faculdade`).
3. Menu **APIs e serviços** → **Biblioteca** → busque **Google Calendar API** → **Ativar**.
4. **APIs e serviços** → **Tela de consentimento OAuth**:
   - Tipo: **Externo** (para testes com sua conta).
   - Preencha nome do app, e-mail de suporte e adicione seu e-mail como **usuário de teste**.
5. **Credenciais** → **Criar credenciais** → **ID do cliente OAuth**:
   - Tipo: **Aplicativo para computador** (Desktop).
6. Baixe o JSON e renomeie para `credentials.json` na pasta do projeto:

```
StudyAI/
  credentials.json   ← aqui
  app2.py
  calendar_service.py
```

> Não envie `credentials.json` nem `token.json` para o Git (já estão no `.gitignore`).

## 2. Chave do Gemini

Crie o arquivo `.streamlit/secrets.toml` (copie de `.streamlit/secrets.toml.example`):

```toml
GEMINI_API_KEY = "sua-chave"
```

Ou no terminal:

```bash
export GEMINI_API_KEY="sua-chave"
```

## 3. Rodar o app

```bash
cd StudyAI
source .venv/bin/activate
streamlit run app2.py
```

Na **barra lateral**, clique em **Conectar Google Calendar**. O navegador abre para você autorizar o acesso. Depois disso, o arquivo `token.json` é salvo e você não precisa logar de novo sempre.

## 4. Como o agente usa o calendário

- Com a opção **Usar calendário nas respostas da IA** ativa, o StudyAI recebe seus próximos eventos no prompt.
- Ele pode sugerir: o que estudar hoje, como dividir a semana, alertas de prova perto, etc.
- Os eventos aparecem em **Próximos compromissos** na barra lateral.

## Problemas comuns

| Erro | Solução |
|------|---------|
| `credentials.json` não encontrado | Siga o passo 1 e coloque o arquivo na raiz do projeto |
| `access_denied` no login | Adicione seu Gmail em **Usuários de teste** na tela OAuth |
| `GEMINI_API_KEY` ausente | Configure `secrets.toml` ou variável de ambiente |
| Navegador não abre | Rode `streamlit run app2.py` no terminal local (não só no cloud) |

## Criar eventos no calendário

1. Antes de **Conectar**, marque **Pedir permissão para criar/alterar eventos**.
2. Se você já conectou só com leitura: **Desconectar** → marque a opção → **Conectar** de novo.
3. Na conversa, peça blocos de estudo; o StudyAI sugere horários e você confirma com **Criar: ...** antes de salvar.
4. Ou use **Criar evento manualmente** na barra lateral.

## Memória da conversa

O agente lembra a conversa atual até você clicar em **Nova conversa** na barra lateral.
