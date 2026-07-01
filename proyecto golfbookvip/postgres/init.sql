-- ============================================================
-- GOLFBOOKVIP.COM — PostgreSQL Init
-- Se ejecuta automáticamente al crear el contenedor
-- ============================================================

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- Búsqueda de texto
CREATE EXTENSION IF NOT EXISTS "unaccent";  -- Búsqueda sin acentos
