/* ============================================================================
   2026-10-18_llamadas_notas.sql
   Agrega Llamadas.notas_llamada (texto libre, NULL = sin notas). Lo usa el
   registro de llamadas (modules/llamadas).

   Idempotente: se puede correr varias veces. No toca filas existentes; las
   llamadas viejas quedan en NULL.

   Aplicado en: (pendiente).
   PENDIENTE en produccion: correrlo alla y luego reflejar cualquier diferencia
   en db/schema/01_tables.sql.
   ============================================================================ */

SET NOCOUNT ON;
GO

IF COL_LENGTH(N'dbo.Llamadas', N'notas_llamada') IS NULL
    ALTER TABLE dbo.Llamadas ADD notas_llamada nvarchar(MAX) NULL;
GO
