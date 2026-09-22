CREATE TABLE "Users"(
    "id" INT NOT NULL,
    "name" NVARCHAR(100) NOT NULL,
    "email" NVARCHAR(255) NOT NULL,
    "password_hash" NVARCHAR(255) NOT NULL,
    "role" NVARCHAR(50) NOT NULL,
    "created_at" DATETIME2 NOT NULL DEFAULT GETDATE()
);
ALTER TABLE
    "Users" ADD CONSTRAINT "users_id_primary" PRIMARY KEY("id");
CREATE UNIQUE INDEX "users_email_unique" ON
    "Users"("email");

CREATE TABLE "Donantes"(
    "id" INT NOT NULL,
    "nombre" NVARCHAR(100) NOT NULL,
    "apellido_paterno" NVARCHAR(100) NULL,
    "apellido_materno" NVARCHAR(100) NULL,
    "apodo" NVARCHAR(100) NULL,
    "razon_social" NVARCHAR(255) NULL,
    "curp" NVARCHAR(18) NULL,
    "email" NVARCHAR(255) NULL,
    "telefono" NVARCHAR(20) NULL,
    "telefono_oficina" NVARCHAR(20) NULL,
    "calle" NVARCHAR(200) NULL,
    "numero_exterior" NVARCHAR(20) NULL,
    "numero_interior" NVARCHAR(20) NULL,
    "colonia" NVARCHAR(150) NULL,
    "municipio" NVARCHAR(150) NULL,
    "estado" NVARCHAR(100) NULL,
    "codigo_postal" NVARCHAR(10) NULL,
    "pais" NVARCHAR(100) NOT NULL DEFAULT 'México',
    "dia_nacimiento" DATETIME2 NULL,
    "fecha_creacion" datetime2(3) NOT NULL DEFAULT SYSUTCDATETIME()
);
ALTER TABLE
    "Donantes" ADD CONSTRAINT "donantes_id_primary" PRIMARY KEY("id");
CREATE UNIQUE INDEX "donantes_curp_unique" ON
    "Donantes"("curp");
CREATE INDEX "donantes_email_index" ON
    "Donantes"("email");
CREATE INDEX "donantes_telefono_index" ON
    "Donantes"("telefono");

CREATE TABLE "Causas"(
    "id" INT NOT NULL,
    "titulo" NVARCHAR(200) NOT NULL,
    "descripcion" NVARCHAR(MAX) NULL,
    "monto_objetivo" DECIMAL(14, 2) NOT NULL,
    "beneficiario" NVARCHAR(255) NULL,
    "responsable" NVARCHAR(255) NULL,
    "lugar" NVARCHAR(255) NULL,
    "fecha_fin" DATETIME2 NULL
);
ALTER TABLE
    "Causas" ADD CONSTRAINT "causas_id_primary" PRIMARY KEY("id");

CREATE TABLE "Promesas"(
    "id" INT NOT NULL,
    "donante_id" INT NOT NULL,
    "caso_id" INT NOT NULL,
    "responsable_id" INT NULL,
    "monto_objetivo" DECIMAL(14, 2) NOT NULL,
    "estado" NVARCHAR(20) CHECK
        (
            "estado" IN(
                N'activo',
                N'completado',
                N'cancelado'
            )
        ) NOT NULL DEFAULT 'activo',
    "fecha_inicio" DATETIME2 NOT NULL,
    "fecha_final" DATETIME2 NULL,
    "numero_frequencia" INT NULL,
    "tipo_frquencia" NVARCHAR(20) NULL
);
ALTER TABLE
    "Promesas" ADD CONSTRAINT "promesas_id_primary" PRIMARY KEY("id");
CREATE INDEX "promesas_donante_id_index" ON
    "Promesas"("donante_id");
CREATE INDEX "promesas_caso_id_index" ON
    "Promesas"("caso_id");
CREATE INDEX "promesas_responsable_id_index" ON
    "Promesas"("responsable_id");

CREATE TABLE "Abonos"(
    "id" INT NOT NULL,
    "promesa_id" INT NOT NULL,
    "monto" DECIMAL(14, 2) NOT NULL,
    "fecha_deposito" DATETIME2 NOT NULL
);
ALTER TABLE
    "Abonos" ADD CONSTRAINT "abonos_id_primary" PRIMARY KEY("id");
CREATE INDEX "abonos_promesa_id_fecha_deposito_index" ON
    "Abonos"("promesa_id", "fecha_deposito");

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
    "fecha_agendada" DATETIME2 NULL
);
ALTER TABLE
    "Llamadas" ADD CONSTRAINT "llamadas_id_primary" PRIMARY KEY("id");
CREATE INDEX "llamadas_promesa_id_index" ON
    "Llamadas"("promesa_id");

ALTER TABLE
    "Promesas" ADD CONSTRAINT "promesas_donante_id_foreign" FOREIGN KEY("donante_id") REFERENCES "Donantes"("id");
ALTER TABLE
    "Promesas" ADD CONSTRAINT "promesas_caso_id_foreign" FOREIGN KEY("caso_id") REFERENCES "Causas"("id");
ALTER TABLE
    "Promesas" ADD CONSTRAINT "promesas_responsable_id_foreign" FOREIGN KEY("responsable_id") REFERENCES "Users"("id");
ALTER TABLE
    "Abonos" ADD CONSTRAINT "abonos_promesa_id_foreign" FOREIGN KEY("promesa_id") REFERENCES "Promesas"("id");
ALTER TABLE
    "Llamadas" ADD CONSTRAINT "llamadas_promesa_id_foreign" FOREIGN KEY("promesa_id") REFERENCES "Promesas"("id");