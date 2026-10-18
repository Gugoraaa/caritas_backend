/* ============================================================================
   2026-10-17_abonos_metodo_pago.sql
   Agrega Abonos.metodo_pago ('efectivo' | 'spei', NULL = no registrado).
   Lo usa GET /admin/donors (metodo de pago del ultimo abono).

   Idempotente: se puede correr varias veces. No toca filas existentes; los
   abonos viejos quedan en NULL.

   Aplicado en: Docker local (caritas-sqlserver).
   PENDIENTE en produccion: correrlo alla y luego reflejar cualquier diferencia
   en db/schema/01_tables.sql.

   Va en lotes separados con GO: el CHECK no compila en el mismo lote que el
   ALTER que crea la columna. Correr con sqlcmd (-I) o un cliente que entienda GO.
   ============================================================================ */

SET NOCOUNT ON;
GO

IF COL_LENGTH(N'dbo.Abonos', N'metodo_pago') IS NULL
    ALTER TABLE dbo.Abonos ADD metodo_pago nvarchar(20) NULL;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE name = N'abonos_metodo_pago_check'
      AND parent_object_id = OBJECT_ID(N'dbo.Abonos')
)
    ALTER TABLE dbo.Abonos
        ADD CONSTRAINT abonos_metodo_pago_check
        CHECK (metodo_pago IN (N'efectivo', N'spei'));
GO
