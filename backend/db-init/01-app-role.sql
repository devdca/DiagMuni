-- Rol de aplicación, sin privilegios de superusuario ni de dueño de tabla.
--
-- POSTGRES_USER (docker-compose.yml) crea un rol SUPERUSER por diseño de la imagen
-- oficial de postgres — y un superusuario ignora RLS siempre, sin importar
-- ENABLE/FORCE ROW LEVEL SECURITY (docs/backend-schema.md, "Políticas RLS").
-- Este script corre una sola vez, al crear el volumen de datos por primera vez
-- (docker-entrypoint-initdb.d), ANTES de que existan las tablas (las migraciones
-- de Alembic corren después, como el rol superusuario). Por eso el GRANT sobre
-- tablas concretas no alcanza nada todavía: lo que importa es el
-- ALTER DEFAULT PRIVILEGES, que sí aplica automáticamente a las tablas que el
-- rol superusuario cree más adelante vía Alembic.
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'diagmuni_app') THEN
      CREATE ROLE diagmuni_app LOGIN PASSWORD 'diagmuni_app_password';
   END IF;
END
$$;

GRANT CONNECT ON DATABASE diagmuni TO diagmuni_app;
GRANT USAGE ON SCHEMA public TO diagmuni_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO diagmuni_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO diagmuni_app;
