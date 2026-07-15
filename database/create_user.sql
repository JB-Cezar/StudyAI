-- Roda uma vez, como root, antes do schema.sql:
--   mysql -u root < database/create_user.sql
-- Cria um usuário dedicado para o app (não usar root no backend).
-- Troque a senha antes de subir isso em qualquer lugar além da sua máquina.

CREATE USER IF NOT EXISTS 'studyai'@'localhost' IDENTIFIED BY 'studyai_dev_password';
GRANT ALL PRIVILEGES ON studyai.* TO 'studyai'@'localhost';
FLUSH PRIVILEGES;
