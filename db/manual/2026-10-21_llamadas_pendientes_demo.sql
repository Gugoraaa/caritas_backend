/* ============================================================================
   2026-10-21_llamadas_pendientes_demo.sql
   OPCIONAL, solo pruebas/demo: inserta 10 llamadas pendientes para HOY y 10
   para MANANA (estado 'agendada', resultado 'pendiente') para probar
   GET /calls/pending y GET /calls/scheduled.

   Requiere db/bootstrap/03_role_users.sql y 2026-10-20_asignar_roles.sql: las
   llamadas se cuelgan de las promesas de telemarketing@caritas.com, que es el
   usuario que ve /calls/pending. Solo inserta; NO es idempotente: correrlo dos
   veces duplica las llamadas.
   ============================================================================ */

SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @hoy datetime2 = CAST(CAST(SYSDATETIMEOFFSET() AT TIME ZONE 'Central Standard Time (Mexico)' AS date) AS datetime2);
DECLARE @teleId INT = (SELECT id FROM dbo.Users WHERE email = N'telemarketing@caritas.com');
DECLARE @nPromesas INT = (SELECT COUNT(*) FROM dbo.Promesas WHERE responsable_id = @teleId AND state = N'activo');

IF @teleId IS NULL OR @nPromesas = 0
    THROW 51020, 'Faltan el usuario de telemarketing o sus promesas activas (ver 2026-10-20_asignar_roles.sql).', 1;

-- Los id de Llamadas no son IDENTITY: se toma MAX(id) con UPDLOCK/HOLDLOCK,
-- igual que INSERT_CALL_QUERY en modules/llamadas/repository.py.
DECLARE @offset INT = (SELECT ISNULL(MAX(id), 0) FROM dbo.Llamadas WITH (UPDLOCK, HOLDLOCK));

;WITH promesas AS (
    SELECT p.id,
           ROW_NUMBER() OVER (ORDER BY p.id) AS rn
    FROM dbo.Promesas p
    WHERE p.responsable_id = @teleId AND p.state = N'activo'
),
plan (n, dia, hora, proposito) AS (
    SELECT * FROM (VALUES
        ( 1, 0,  9, N'seguimiento'),
        ( 2, 0, 10, N'recordatorio de pago'),
        ( 3, 0, 11, N'agradecimiento'),
        ( 4, 0, 12, N'invitacion a evento'),
        ( 5, 0, 13, N'seguimiento'),
        ( 6, 0, 14, N'recordatorio de pago'),
        ( 7, 0, 15, N'agradecimiento'),
        ( 8, 0, 16, N'seguimiento'),
        ( 9, 0, 17, N'recordatorio de pago'),
        (10, 0, 18, N'invitacion a evento'),
        (11, 1,  9, N'seguimiento'),
        (12, 1, 10, N'recordatorio de pago'),
        (13, 1, 11, N'agradecimiento'),
        (14, 1, 12, N'invitacion a evento'),
        (15, 1, 13, N'seguimiento'),
        (16, 1, 14, N'recordatorio de pago'),
        (17, 1, 15, N'agradecimiento'),
        (18, 1, 16, N'seguimiento'),
        (19, 1, 17, N'recordatorio de pago'),
        (20, 1, 18, N'invitacion a evento')
    ) v (n, dia, hora, proposito)
)
INSERT INTO dbo.Llamadas
    (id, promesa_id, resultado_llamado, monto_comprometido, estado, proposito, fecha_agendada)
SELECT
    @offset + pl.n,
    pr.id,
    N'pendiente',
    NULL,
    N'agendada',
    pl.proposito,
    DATEADD(hour, pl.hora, DATEADD(day, pl.dia, @hoy))
FROM plan pl
JOIN promesas pr ON pr.rn = ((pl.n - 1) % @nPromesas) + 1;

PRINT CONCAT('Llamadas pendientes insertadas: ', @@ROWCOUNT);

SELECT id, promesa_id, estado, proposito, fecha_agendada
FROM dbo.Llamadas
WHERE id > @offset
ORDER BY fecha_agendada, id;
