-- Isola conversas por usuário (sub-etapa 8b).
-- Limpa as conversas de teste da Etapa 7 (sem usuário associado, sem valor)
-- e adiciona user_id NOT NULL, já que o chat passa a exigir login.

USE studyai;

DELETE FROM conversations;

ALTER TABLE conversations
    ADD COLUMN user_id INT NOT NULL AFTER id,
    ADD FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    ADD INDEX idx_conversations_user (user_id);
