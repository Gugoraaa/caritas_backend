/* ============================================================================
   01_admin_user.sql
   Usuario administrador de desarrollo para la base "caritas".

       email:      admin@caritas.com
       contrasena: admin123
       role:       admin

   Este script corre en CADA arranque de docker compose y es idempotente:
   si el usuario no existe lo crea, y si existe le reescribe nombre, rol y
   hash para que la contrasena siempre sea la de arriba.

   El hash es bcrypt con cost 10, el mismo formato que genera
   src/caritas_backend/security.py. Para cambiar la contrasena:

       uv run python -c "import bcrypt; \
           print(bcrypt.hashpw(b'NUEVA', bcrypt.gensalt(10)).decode())"

   OJO: credenciales de desarrollo. No subir esta base a produccion.
   ============================================================================ */

SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @email NVARCHAR(255) = N'admin@caritas.com';
DECLARE @name  NVARCHAR(100) = N'Administrador';
DECLARE @role  NVARCHAR(50)  = N'admin';
/* bcrypt(admin123, cost 10) */
DECLARE @hash  NVARCHAR(255) = N'$2b$10$pClKKJZF3hmiasipMCnwbOeZhEVEEWcER7HnKHYvOyg41W3AZkBFu';

IF EXISTS (SELECT 1 FROM dbo.Users WHERE email = @email)
BEGIN
    UPDATE dbo.Users
       SET name          = @name,
           password_hash = @hash,
           role          = @role
     WHERE email = @email;

    PRINT 'Usuario admin actualizado: ' + @email;
END
ELSE IF OBJECTPROPERTY(OBJECT_ID('dbo.Users'), 'TableHasIdentity') = 1
BEGIN
    INSERT INTO dbo.Users (name, email, password_hash, role, created_at)
    VALUES (@name, @email, @hash, @role, SYSUTCDATETIME());

    PRINT 'Usuario admin creado: ' + @email;
END
ELSE
BEGIN
    /* dbo.Users.id no es IDENTITY en el esquema actual: hay que asignarlo. */
    DECLARE @nextId INT = ISNULL((SELECT MAX(id) FROM dbo.Users), 0) + 1;

    INSERT INTO dbo.Users (id, name, email, password_hash, role, created_at)
    VALUES (@nextId, @name, @email, @hash, @role, SYSUTCDATETIME());

    PRINT 'Usuario admin creado: ' + @email;
END

SELECT id, name, email, role, created_at
FROM dbo.Users
WHERE email = @email;
