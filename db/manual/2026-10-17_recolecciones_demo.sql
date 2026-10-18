/* ============================================================================
   2026-10-17_recolecciones_demo.sql
   OPCIONAL, solo para pruebas y demo: agenda recolecciones para hoy a partir
   de promesas activas reales cuyos donantes tienen domicilio.

   Requiere 2026-10-17_recolecciones.sql. No borra nada y no toca otras
   tablas; si hoy ya hay recolecciones agendadas, no hace nada.

   @recolector_id: id del usuario (Users) que hara las recolecciones. NULL =
   sin asignar (cualquier usuario con sesion las puede abrir).
   ============================================================================ */

SET NOCOUNT ON;

DECLARE @recolector_id int = NULL;
DECLARE @cuantas int = 5;
DECLARE @hoy datetime2 = CAST(CAST(SYSDATETIMEOFFSET() AT TIME ZONE 'Central Standard Time (Mexico)' AS date) AS datetime2);

IF NOT EXISTS (
    SELECT 1 FROM dbo.Recolecciones
    WHERE fecha_programada >= @hoy AND fecha_programada < DATEADD(day, 1, @hoy)
)
BEGIN
    ;WITH candidatas AS (
        SELECT TOP (@cuantas)
            p.id AS promesa_id,
            CAST(p.monto_objetivo / CASE WHEN ISNULL(p.numero_frequencia, 0) > 0
                                         THEN p.numero_frequencia ELSE 1 END
                 AS decimal(14,2)) AS cuota,
            ROW_NUMBER() OVER (ORDER BY p.id) AS n
        FROM dbo.Promesas p
        JOIN dbo.Donantes d ON d.id = p.donante_id
        WHERE p.state = N'activo'
          AND d.calle IS NOT NULL
          AND d.colonia IS NOT NULL
        ORDER BY p.id
    )
    INSERT INTO dbo.Recolecciones
        (promesa_id, recolector_id, fecha_programada, ventana_inicio, ventana_fin, monto)
    SELECT
        promesa_id,
        @recolector_id,
        DATEADD(minute, 45, DATEADD(hour, 9 + n, @hoy)),
        DATEADD(minute, 30, DATEADD(hour, 9 + n, @hoy)),
        DATEADD(minute, 30, DATEADD(hour, 10 + n, @hoy)),
        cuota
    FROM candidatas;
END

SELECT r.id, r.promesa_id, r.fecha_programada, r.monto, r.estado
FROM dbo.Recolecciones r
WHERE r.fecha_programada >= @hoy AND r.fecha_programada < DATEADD(day, 1, @hoy)
ORDER BY r.fecha_programada;
