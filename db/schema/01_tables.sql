/* ============================================================================
   01_tables.sql
   Esquema de la base "caritas", copia del de PRODUCCION. Mantener igual:
   si cambia produccion, se cambia aca, no al reves.

   Diferencias con el DDL que exporta DBeaver de produccion, solo por sintaxis:
     - "ON DELETE/UPDATE RESTRICT" no existe en SQL Server; el equivalente es
       el default (NO ACTION), asi que las FKs van sin clausula.
     - Causas.descripcion sale como nvarchar(8000), que no es valido
       (nvarchar llega a 4000); se usa NVARCHAR(MAX).

   Cosas de produccion que se copian tal cual aunque parezcan raras:
     - Users.id es IDENTITY; el resto de las tablas asignan el id a mano.
     - Users.email tiene dos indices UNIQUE (duplicados).
     - Promesas.state tiene como DEFAULT el texto 'activo, completado,
       cancelado' (29 caracteres en un nvarchar(20)): un INSERT que no mande
       state falla por truncamiento. Hay que mandarlo siempre.
     - Promesas.state y Llamadas.estado no tienen CHECK.
   ============================================================================ */

CREATE TABLE dbo.Causas (
    id int NOT NULL,
    titulo nvarchar(200) NOT NULL,
    fecha_fin datetime2 NULL,
    descripcion nvarchar(MAX) NULL,
    monto_objetivo decimal(14,2) NOT NULL,
    beneficiario nvarchar(255) NULL,
    responsable nvarchar(255) NULL,
    lugar nvarchar(255) NULL,
    CONSTRAINT causas_id_primary PRIMARY KEY (id)
);

CREATE TABLE dbo.Donantes (
    id int NOT NULL,
    nombre nvarchar(100) NOT NULL,
    apellido_paterno nvarchar(100) NULL,
    apellido_materno nvarchar(100) NULL,
    nickname nvarchar(100) NULL,
    razon_social nvarchar(255) NULL,
    curp nvarchar(18) NULL,
    email nvarchar(255) NULL,
    fecha_creacion datetime2 DEFAULT (sysutcdatetime()) NOT NULL,
    dia_nacimiento datetime2 NULL,
    telefono_oficina nvarchar(20) NULL,
    telefono nvarchar(20) NULL,
    calle nvarchar(200) NULL,
    numero_exterior nvarchar(20) NULL,
    numero_interior nvarchar(20) NULL,
    colonia nvarchar(150) NULL,
    municipio nvarchar(150) NULL,
    estado nvarchar(100) NULL,
    codigo_postal nvarchar(10) NULL,
    pais nvarchar(100) DEFAULT (N'México') NOT NULL,
    CONSTRAINT donantes_id_primary PRIMARY KEY (id)
);
CREATE UNIQUE INDEX donantes_curp_unique ON dbo.Donantes (curp);
CREATE INDEX donantes_email_index ON dbo.Donantes (email);
CREATE INDEX donantes_telefono_index ON dbo.Donantes (telefono);

CREATE TABLE dbo.Users (
    id int NOT NULL IDENTITY(1,1),
    name nvarchar(100) NOT NULL,
    email nvarchar(255) NOT NULL,
    password_hash nvarchar(255) NOT NULL,
    [role] nvarchar(50) NOT NULL,
    created_at datetime2 DEFAULT (getdate()) NOT NULL,
    CONSTRAINT PK__Users__3213E83FE3CB03F4 PRIMARY KEY (id)
);
CREATE UNIQUE INDEX UQ__Users__AB6E6164BD28C7AF ON dbo.Users (email);
CREATE UNIQUE INDEX users_email_unique ON dbo.Users (email);

CREATE TABLE dbo.Promesas (
    id int NOT NULL,
    donante_id int NOT NULL,
    caso_id int NOT NULL,
    monto_objetivo decimal(14,2) NOT NULL,
    state nvarchar(20) DEFAULT ('activo, completado, cancelado') NOT NULL,
    fecha_inicio datetime2 NOT NULL,
    fecha_final datetime2 NULL,
    numero_frequencia int NULL,
    tipo_frquencia nvarchar(20) NULL,
    responsable_id int NULL,
    CONSTRAINT promesas_id_primary PRIMARY KEY (id),
    CONSTRAINT promesas_caso_id_foreign FOREIGN KEY (caso_id) REFERENCES dbo.Causas(id),
    CONSTRAINT promesas_donante_id_foreign FOREIGN KEY (donante_id) REFERENCES dbo.Donantes(id),
    CONSTRAINT promesas_responsable_id_foreign FOREIGN KEY (responsable_id) REFERENCES dbo.Users(id)
);
CREATE INDEX promesas_caso_id_index ON dbo.Promesas (caso_id);
CREATE INDEX promesas_donante_id_index ON dbo.Promesas (donante_id);
CREATE INDEX promesas_responsable_id_index ON dbo.Promesas (responsable_id);

CREATE TABLE "Llamadas"(
    "id" INT NOT NULL,
    "promesa_id" INT NOT NULL,
    "resultado_llamado" TEXT NOT NULL,
    "monto_comprometido" DECIMAL(14, 2) NULL,
    "estado" NVARCHAR(20) CHECK
        (
            "estado" IN(
                N'agendada',
                N'cancelada',
                N'completada'
            )
        ) NOT NULL,
    "proposito" NVARCHAR(30) NULL,
    "fecha_agendada" DATETIME2 NULL,
    "notas_llamada" NVARCHAR(MAX) NULL
CREATE TABLE dbo.Abonos (
    id int NOT NULL,
    promesa_id int NOT NULL,
    monto decimal(14,2) NOT NULL,
    fecha_deposito datetime2 NOT NULL,
    -- db/manual/2026-10-17_abonos_metodo_pago.sql (PENDIENTE en produccion).
    metodo_pago nvarchar(20) NULL,
    CONSTRAINT abonos_id_primary PRIMARY KEY (id),
    CONSTRAINT abonos_promesa_id_foreign FOREIGN KEY (promesa_id) REFERENCES dbo.Promesas(id),
    CONSTRAINT abonos_metodo_pago_check CHECK (metodo_pago IN (N'efectivo', N'spei'))
);
CREATE INDEX abonos_promesa_id_fecha_deposito_index ON dbo.Abonos (promesa_id, fecha_deposito);

CREATE TABLE dbo.Llamadas (
    id int NOT NULL,
    resultado_llamado text NOT NULL,
    monto_comprometido decimal(14,2) NULL,
    estado nvarchar(255) NOT NULL,
    proposito nvarchar(30) NULL,
    promesa_id int NOT NULL,
    fecha_agendada datetime2 NULL,
    CONSTRAINT llamadas_id_primary PRIMARY KEY (id),
    CONSTRAINT llamadas_promesa_id_foreign FOREIGN KEY (promesa_id) REFERENCES dbo.Promesas(id)
);
CREATE INDEX llamadas_promesa_id_index ON dbo.Llamadas (promesa_id);

-- db/manual/2026-10-17_recolecciones.sql (PENDIENTE en produccion).
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
    CONSTRAINT recolecciones_id_primary PRIMARY KEY (id),
    CONSTRAINT recolecciones_promesa_id_foreign FOREIGN KEY (promesa_id) REFERENCES dbo.Promesas(id),
    CONSTRAINT recolecciones_recolector_id_foreign FOREIGN KEY (recolector_id) REFERENCES dbo.Users(id),
    CONSTRAINT recolecciones_abono_id_foreign FOREIGN KEY (abono_id) REFERENCES dbo.Abonos(id),
    CONSTRAINT recolecciones_estado_check CHECK (estado IN (N'pendiente', N'confirmada', N'no_recolectada')),
    CONSTRAINT recolecciones_motivo_check CHECK (motivo IN (
        N'nadie_en_domicilio', N'reprogramar', N'domicilio_incorrecto', N'ya_no_desea_donar'
    ))
);
CREATE INDEX recolecciones_promesa_id_index ON dbo.Recolecciones (promesa_id);
CREATE INDEX recolecciones_recolector_fecha_index ON dbo.Recolecciones (recolector_id, fecha_programada);
