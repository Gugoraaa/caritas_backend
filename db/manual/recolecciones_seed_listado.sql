/* ============================================================================
   recolecciones_seed_listado.sql
   OPCIONAL, solo pruebas/demo: inserta 8 recolecciones variadas para probar
   GET /collections (filtros de status, collector y fecha).

   Requiere 2026-10-17_recolecciones.sql. Solo inserta; repartidas entre ayer,
   hoy y manana, con los tres estados y hasta 2 recolectores (los 2 primeros
   Users; si solo hay uno, los demas quedan sin asignar). Las 'confirmada' no
   traen abono_id (no se crea Abono real).
   ============================================================================ */

SET NOCOUNT ON;

DECLARE @hoy datetime2 = CAST(CAST(SYSDATETIMEOFFSET() AT TIME ZONE 'Central Standard Time (Mexico)' AS date) AS datetime2);
DECLARE @u1 int = (SELECT id FROM dbo.Users ORDER BY id OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY);
DECLARE @u2 int = (SELECT id FROM dbo.Users ORDER BY id OFFSET 1 ROWS FETCH NEXT 1 ROWS ONLY);

;WITH promesas AS (
    SELECT p.id,
           CAST(p.monto_objetivo / CASE WHEN ISNULL(p.numero_frequencia, 0) > 0
                                        THEN p.numero_frequencia ELSE 1 END AS decimal(14,2)) AS cuota,
           ROW_NUMBER() OVER (ORDER BY p.id) AS rn
    FROM dbo.Promesas p
    JOIN dbo.Donantes d ON d.id = p.donante_id
    WHERE p.state = N'activo' AND d.calle IS NOT NULL AND d.colonia IS NOT NULL
),
plan (n, dia, hora, estado, motivo, quien) AS (
    SELECT * FROM (VALUES
        (1, -1, 10, N'confirmada',     NULL,                  1),
        (2, -1, 12, N'no_recolectada', N'nadie_en_domicilio', 1),
        (3,  0,  9, N'pendiente',      NULL,                  1),
        (4,  0, 11, N'pendiente',      NULL,                  2),
        (5,  0, 13, N'no_recolectada', N'reprogramar',        2),
        (6,  0, 16, N'confirmada',     NULL,                  2),
        (7,  1, 10, N'pendiente',      NULL,                  1),
        (8,  1, 12, N'pendiente',      NULL,                  NULL)
    ) v (n, dia, hora, estado, motivo, quien)
)
INSERT INTO dbo.Recolecciones
    (promesa_id, recolector_id, fecha_programada, ventana_inicio, ventana_fin,
     monto, estado, motivo, fecha_resultado)
SELECT
    pr.id,
    CASE pl.quien WHEN 1 THEN @u1 WHEN 2 THEN ISNULL(@u2, NULL) END,
    DATEADD(hour, pl.hora, DATEADD(day, pl.dia, @hoy)),
    DATEADD(minute, -30, DATEADD(hour, pl.hora, DATEADD(day, pl.dia, @hoy))),
    DATEADD(minute, 30, DATEADD(hour, pl.hora, DATEADD(day, pl.dia, @hoy))),
    pr.cuota,
    pl.estado,
    pl.motivo,
    CASE WHEN pl.estado <> N'pendiente' THEN DATEADD(hour, pl.hora, DATEADD(day, pl.dia, @hoy)) END
FROM plan pl
JOIN promesas pr ON pr.rn = ((pl.n - 1) % (SELECT COUNT(*) FROM promesas)) + 1;

SELECT id, promesa_id, recolector_id, fecha_programada, estado, motivo
FROM dbo.Recolecciones ORDER BY id DESC;
