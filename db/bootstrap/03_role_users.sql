/* ============================================================================
   03_role_users.sql
   Usuarios de desarrollo para cada rol de la app, ademas del admin.

       email                       contrasena  role           app
       telemarketing@caritas.com   tele123     TELEMARKETINA  Hoy, Casos, Historial
       repartidor@caritas.com      rep123      RECOLECTOR     Mi ruta

   Los roles van como los pide el CHECK de dbo.Users.role:
   'ADMIN', 'TELEMARKETINA' o 'RECOLECTOR'.

   Igual que 01_admin_user.sql: corre en CADA arranque, es idempotente y
   reescribe nombre, rol y hash. Los hash son bcrypt con cost 10.

   Para pasarles promesas y recolecciones: db/manual/2026-10-20_asignar_roles.sql.

   OJO: credenciales de desarrollo. No subir esta base a produccion.
   ============================================================================ */

SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @users TABLE (email NVARCHAR(255), name NVARCHAR(100), role NVARCHAR(50), hash NVARCHAR(255));
INSERT INTO @users (email, name, role, hash) VALUES
    /* bcrypt(tele123, cost 10) */
    (N'telemarketing@caritas.com', N'Telemarketing', N'TELEMARKETINA',
     N'$2b$10$XgliXaO77JZOmuZBBptZnuLWg2jttUZXLHm1IIfLOb6XmaIISwRju'),
    /* bcrypt(rep123, cost 10) */
    (N'repartidor@caritas.com', N'Repartidor', N'RECOLECTOR',
     N'$2b$10$SMCHDjyZcYa6bvoc3l7a/.z0CPFG1R5YhO6u7R9lqjin7SYwEZ26G');

UPDATE u
   SET u.name = n.name, u.role = n.role, u.password_hash = n.hash
  FROM dbo.Users u
  JOIN @users n ON n.email = u.email;

IF OBJECTPROPERTY(OBJECT_ID('dbo.Users'), 'TableHasIdentity') = 1
BEGIN
    INSERT INTO dbo.Users (name, email, password_hash, role, created_at)
    SELECT n.name, n.email, n.hash, n.role, SYSUTCDATETIME()
      FROM @users n
     WHERE NOT EXISTS (SELECT 1 FROM dbo.Users u WHERE u.email = n.email);
END
ELSE
BEGIN
    /* dbo.Users.id no es IDENTITY en el esquema actual: hay que asignarlo. */
    DECLARE @maxId INT = ISNULL((SELECT MAX(id) FROM dbo.Users), 0);

    INSERT INTO dbo.Users (id, name, email, password_hash, role, created_at)
    SELECT @maxId + ROW_NUMBER() OVER (ORDER BY n.email), n.name, n.email, n.hash, n.role, SYSUTCDATETIME()
      FROM @users n
     WHERE NOT EXISTS (SELECT 1 FROM dbo.Users u WHERE u.email = n.email);
END

SELECT u.id, u.name, u.email, u.role
FROM dbo.Users u
JOIN @users n ON n.email = u.email;
