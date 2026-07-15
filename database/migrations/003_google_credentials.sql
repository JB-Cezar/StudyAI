-- Sub-etapa 8c: Google Calendar por usuário.
-- Substitui o token único em backend/token.json (fluxo Desktop) por um token
-- OAuth por usuário, obtido no mesmo login (fluxo Web, escopo já inclui
-- Calendar). Guarda o JSON de credenciais completo (como o
-- Credentials.to_json() do google-auth) — mais simples que espalhar cada
-- campo em colunas, e casa com o que o SDK já sabe reconstruir.

USE studyai;

CREATE TABLE IF NOT EXISTS google_credentials (
    user_id INT PRIMARY KEY,
    credentials_json TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;
