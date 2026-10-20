/* ============================================================================
   02_api_login.sql
   Login de SQL Server para la API, con el minimo de permisos (least privilege).

       login / usuario: caritas_api
       contrasena:      variable de sqlcmd API_DB_PASSWORD (docker-compose)
       permisos:        SELECT, INSERT, UPDATE, DELETE sobre el esquema dbo

   La API ya no se conecta con sa: no puede crear, alterar ni borrar tablas,
   ni tocar otras bases. sa queda solo para db-init y para mantenimiento.

   Corre en CADA arranque de docker compose y es idempotente: si el login ya
   existe le reescribe la contrasena.

   Fuera de docker (SSMS / Azure Data Studio) hay que activar el modo SQLCMD
   o reemplazar $(API_DB_PASSWORD) a mano.
   ============================================================================ */

SET NOCOUNT ON;
SET XACT_ABORT ON;

IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'caritas_api')
BEGIN
    CREATE LOGIN caritas_api WITH PASSWORD = N'$(API_DB_PASSWORD)', CHECK_POLICY = ON;
    PRINT 'Login caritas_api creado.';
END
ELSE
BEGIN
    ALTER LOGIN caritas_api WITH PASSWORD = N'$(API_DB_PASSWORD)';
    PRINT 'Login caritas_api actualizado.';
END

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'caritas_api')
    CREATE USER caritas_api FOR LOGIN caritas_api WITH DEFAULT_SCHEMA = dbo;

GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::dbo TO caritas_api;

SELECT dp.name AS usuario, p.permission_name AS permiso, p.class_desc AS sobre
FROM sys.database_permissions p
JOIN sys.database_principals dp ON dp.principal_id = p.grantee_principal_id
WHERE dp.name = N'caritas_api'
ORDER BY p.permission_name;
