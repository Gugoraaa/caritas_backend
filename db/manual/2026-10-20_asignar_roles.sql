/* ============================================================================
   2026-10-20_asignar_roles.sql
   Pasa al usuario de cada rol lo que hoy esta asignado al admin o a nadie:

       Promesas.responsable_id     -> telemarketing@caritas.com
       Recolecciones.recolector_id -> repartidor@caritas.com

   Llamadas, Abonos y Donantes no tienen usuario: se ven a traves de la promesa.
   Lo asignado a otros usuarios (no admin) no se toca.

   Requiere db/bootstrap/03_role_users.sql. Se puede correr varias veces.
   ============================================================================ */

SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @teleId INT = (SELECT id FROM dbo.Users WHERE email = N'telemarketing@caritas.com');
DECLARE @repId  INT = (SELECT id FROM dbo.Users WHERE email = N'repartidor@caritas.com');

IF @teleId IS NULL OR @repId IS NULL
    THROW 51010, 'Faltan los usuarios de 03_role_users.sql.', 1;

BEGIN TRANSACTION;

UPDATE p
   SET p.responsable_id = @teleId
  FROM dbo.Promesas p
  LEFT JOIN dbo.Users u ON u.id = p.responsable_id
 WHERE p.responsable_id IS NULL
    OR LOWER(LTRIM(RTRIM(u.role))) = N'admin';

PRINT CONCAT('Promesas asignadas a telemarketing: ', @@ROWCOUNT);

IF OBJECT_ID(N'dbo.Recolecciones', N'U') IS NOT NULL
BEGIN
    UPDATE r
       SET r.recolector_id = @repId
      FROM dbo.Recolecciones r
      LEFT JOIN dbo.Users u ON u.id = r.recolector_id
     WHERE r.recolector_id IS NULL
        OR LOWER(LTRIM(RTRIM(u.role))) = N'admin';

    PRINT CONCAT('Recolecciones asignadas a repartidor: ', @@ROWCOUNT);
END

COMMIT;

SELECT u.email, u.role,
       (SELECT COUNT(*) FROM dbo.Promesas p WHERE p.responsable_id = u.id) AS promesas,
       (SELECT COUNT(*) FROM dbo.Recolecciones r WHERE r.recolector_id = u.id) AS recolecciones
FROM dbo.Users u
WHERE u.email IN (N'admin@caritas.com', N'telemarketing@caritas.com', N'repartidor@caritas.com');
