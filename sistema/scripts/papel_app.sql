-- Papel restrito do aplicativo. Rodar UMA vez, com o dono do banco (ex.: postgres), depois das migrations:
--   psql -d pizzaria -v app_role=pizzaria_app -f scripts/papel_app.sql
-- Crie o papel antes: CREATE ROLE pizzaria_app LOGIN PASSWORD '...';  (sem SUPERUSER, sem CREATEDB)
-- O aplicativo (DB_USER) usa este papel; o migrator e o criar_admin usam o dono (MIGRATE_DB_USER).
-- Efeito: o app não consegue alterar nem apagar a auditoria, nem desligar o gatilho dela.
GRANT USAGE ON SCHEMA public TO :app_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO :app_role;
REVOKE UPDATE, DELETE, TRUNCATE ON auditoria FROM :app_role;
REVOKE UPDATE, DELETE, TRUNCATE ON backup_registro FROM :app_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO :app_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO :app_role;
