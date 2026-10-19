/* ============================================================================
   2026-10-17_recolecciones.sql
   Crea dbo.Recolecciones: cada visita agendada para cobrar en domicilio la
   cuota de una promesa. La usan /collections (detalle, confirmar y motivo de
   no recoleccion) y la sirve de base para la lista "Mi ruta" del recolector.

   - estado: 'pendiente' hasta que el recolector la confirma ('confirmada') o
     indica que no se pudo ('no_recolectada', con motivo).
   - Al confirmar se crea el Abono (metodo_pago = 'efectivo') y se guarda su id
     en abono_id. Requiere 2026-10-17_abonos_metodo_pago.sql.
   - id es IDENTITY (como Users) para no depender de MAX(id) + 1.
   - updated_at se actualiza automaticamente (trigger) solo cuando cambia
     estado. created_at queda fijo.

   Idempotente: se puede correr varias veces. No toca ninguna tabla existente.

   Aplicado en: (pendiente).
   PENDIENTE en produccion: correrlo alla y luego reflejar cualquier diferencia
   en db/schema/01_tables.sql.

   Va en lotes separados con GO. Correr con sqlcmd (-I) o un cliente que
   entienda GO.
   ============================================================================ */

SET NOCOUNT ON;
GO

IF OBJECT_ID(N'dbo.Recolecciones', N'U') IS NULL
    CREATE TABLE dbo.Recolecciones (
        id int NOT NULL IDENTITY(1,1),
        promesa_id int NOT NULL,
        recolector_id int NULL,
        fecha_programada datetime2 NOT NULL,
        ventana_inicio datetime2 NULL,
        ventana_fin datetime2 NULL,
        monto decimal(14,2) NOT NULL,
        notas_domicilio nvarchar(500) NULL,
        estado nvarchar(20) DEFAULT (N'pendiente') NOT NULL,
        motivo nvarchar(30) NULL,
        fecha_resultado datetime2 NULL,
        abono_id int NULL,
        created_at datetime2 DEFAULT (getdate()) NOT NULL,
        updated_at datetime2 DEFAULT (getdate()) NOT NULL,
        CONSTRAINT recolecciones_id_primary PRIMARY KEY (id),
        CONSTRAINT recolecciones_promesa_id_foreign FOREIGN KEY (promesa_id) REFERENCES dbo.Promesas(id),
        CONSTRAINT recolecciones_recolector_id_foreign FOREIGN KEY (recolector_id) REFERENCES dbo.Users(id),
        CONSTRAINT recolecciones_abono_id_foreign FOREIGN KEY (abono_id) REFERENCES dbo.Abonos(id),
        CONSTRAINT recolecciones_estado_check CHECK (estado IN (N'pendiente', N'confirmada', N'no_recolectada')),
        CONSTRAINT recolecciones_motivo_check CHECK (motivo IN (
            N'nadie_en_domicilio', N'reprogramar', N'domicilio_incorrecto', N'ya_no_desea_donar'
        ))
    );
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'recolecciones_promesa_id_index')
    CREATE INDEX recolecciones_promesa_id_index ON dbo.Recolecciones (promesa_id);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'recolecciones_recolector_fecha_index')
    CREATE INDEX recolecciones_recolector_fecha_index
        ON dbo.Recolecciones (recolector_id, fecha_programada);
GO

/* updated_at: se actualiza solo cuando estado cambia de valor. */
CREATE OR ALTER TRIGGER dbo.trg_Recolecciones_estado_updated_at
ON dbo.Recolecciones
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF UPDATE(estado)
        UPDATE r
        SET updated_at = getdate()
        FROM dbo.Recolecciones r
        INNER JOIN inserted i ON i.id = r.id
        INNER JOIN deleted d ON d.id = i.id
        WHERE i.estado <> d.estado;
END;
GO
