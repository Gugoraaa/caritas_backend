SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @CONFIRM_RESEED BIT = 1;

IF @CONFIRM_RESEED <> 1
    THROW 51000, 'Cambia @CONFIRM_RESEED a 1 después de hacer un backup.', 1;

BEGIN TRY
    BEGIN TRANSACTION;

    /* ---------------------------------------------------------------
       0. Validaciones de seguridad y compatibilidad
       --------------------------------------------------------------- */
    IF OBJECT_ID(N'dbo.Users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.Donantes', N'U') IS NULL
       OR OBJECT_ID(N'dbo.Causas', N'U') IS NULL
       OR OBJECT_ID(N'dbo.Promesas', N'U') IS NULL
       OR OBJECT_ID(N'dbo.Abonos', N'U') IS NULL
       OR OBJECT_ID(N'dbo.Llamadas', N'U') IS NULL
        THROW 51001, 'Faltan una o más tablas requeridas.', 1;

    IF COL_LENGTH(N'dbo.Promesas', N'state') IS NULL
        THROW 51002, 'La tabla Promesas no tiene la columna state esperada.', 1;

    DECLARE @AdminId INT = (
        SELECT TOP (1) id
        FROM dbo.Users
        WHERE email = N'admin@caritas.com'
    );

    IF @AdminId IS NULL
        THROW 51003, 'No existe admin@caritas.com. Crea o restaura el administrador antes del seed.', 1;

    DECLARE @Hoy DATE = CAST(DATEADD(HOUR, -6, SYSUTCDATETIME()) AS DATE);
    DECLARE @Ahora DATETIME2(0) = CAST(@Hoy AS DATETIME2(0));

    /* ---------------------------------------------------------------
       1. Catálogo determinista de donantes
       --------------------------------------------------------------- */
    DECLARE @Donantes TABLE (
        id INT PRIMARY KEY,
        nombre NVARCHAR(100) NOT NULL,
        apellido_paterno NVARCHAR(100) NULL,
        apellido_materno NVARCHAR(100) NULL,
        nickname NVARCHAR(100) NULL,
        razon_social NVARCHAR(255) NULL,
        curp NVARCHAR(18) NOT NULL,
        email NVARCHAR(255) NULL,
        telefono NVARCHAR(20) NULL,
        telefono_oficina NVARCHAR(20) NULL,
        calle NVARCHAR(200) NULL,
        numero_exterior NVARCHAR(20) NULL,
        colonia NVARCHAR(150) NULL,
        municipio NVARCHAR(150) NULL,
        estado NVARCHAR(100) NULL,
        codigo_postal NVARCHAR(10) NULL,
        pais NVARCHAR(100) NOT NULL
    );

    INSERT INTO @Donantes (
        id, nombre, apellido_paterno, apellido_materno, nickname,
        razon_social, curp, email, telefono, telefono_oficina, calle,
        numero_exterior, colonia, municipio, estado, codigo_postal, pais
    )
    VALUES
    (1,  N'María',       N'Hernández', N'García',     NULL,             NULL, N'MOCK00000001HDFXYZ', N'donante1@mock.local',  N'5510000001', N'8181000001', N'Juárez',       N'101', N'Centro',              N'Monterrey',      N'Nuevo León',      N'64000', N'México'),
    (2,  N'Patricia',    N'Rodríguez', N'Martínez',   NULL,             NULL, N'MOCK00000002HDFXYZ', N'donante2@mock.local',  N'5510000002', N'8181000002', N'Constitución', N'202', N'Obispado',            N'Monterrey',      N'Nuevo León',      N'64010', N'México'),
    (3,  N'Alejandro',   N'Torres',    N'Díaz',       NULL,             NULL, N'MOCK00000003HDFXYZ', N'donante3@mock.local',  N'5510000003', N'8181000003', N'Pino Suárez',   N'303', N'Independencia',       N'Monterrey',      N'Nuevo León',      N'64020', N'México'),
    (4,  N'María',       N'Gómez',     N'González',   NULL,             NULL, N'MOCK00000004HDFXYZ', N'donante4@mock.local',  N'5510000004', N'8181000004', N'Madero',        N'404', N'Mitras Centro',        N'Monterrey',      N'Nuevo León',      N'64460', N'México'),
    (5,  N'Carlos',      N'Cruz',      N'Cruz',       NULL,             NULL, N'MOCK00000005HDFXYZ', N'donante5@mock.local',  N'5510000005', N'8181000005', N'Washington',    N'505', N'Roma',                 N'Monterrey',      N'Nuevo León',      N'64700', N'México'),
    (6,  N'Patricia',    N'Castillo',  N'Rodríguez',  NULL,             NULL, N'MOCK00000006HDFXYZ', N'donante6@mock.local',  N'5510000006', N'8181000006', N'Allende',        N'606', N'Vista Hermosa',        N'Monterrey',      N'Nuevo León',      N'64620', N'México'),
    (7,  N'José',        N'López',     N'Pérez',      NULL,             NULL, N'MOCK00000007HDFXYZ', N'donante7@mock.local',  N'5510000007', N'8181000007', N'Aramberri',      N'707', N'Nuevo Repueblo',       N'Monterrey',      N'Nuevo León',      N'64700', N'México'),
    (8,  N'María',       N'González',  N'Ramírez',    NULL,             NULL, N'MOCK00000008HDFXYZ', N'donante8@mock.local',  N'5510000008', N'8181000008', N'Moctezuma',      N'808', N'Linda Vista',           N'Guadalupe',      N'Nuevo León',      N'67123', N'México'),
    (9,  N'Carlos',      N'Sánchez',   N'Vargas',     NULL,             NULL, N'MOCK00000009HDFXYZ', N'donante9@mock.local',  N'5510000009', N'8181000009', N'Pueblo Nuevo',   N'909', N'Contry',                N'Monterrey',      N'Nuevo León',      N'64845', N'México'),
    (10, N'Patricia',    N'Flores',    N'Flores',     NULL,             NULL, N'MOCK00000010HDFXYZ', N'donante10@mock.local', N'5510000010', N'8181000010', N'Garza Sada',    N'110', N'Brisas',                N'Monterrey',      N'Nuevo León',      N'64790', N'México'),
    (11, N'Alejandro',   N'Díaz',      N'García',     NULL,             NULL, N'MOCK00000011HDFXYZ', N'donante11@mock.local', N'5510000011', N'8181000011', N'Abasolo',        N'111', N'Centro',                N'San Nicolás',    N'Nuevo León',      N'66400', N'México'),
    (12, N'María',       N'Morales',   N'Gómez',      NULL,             NULL, N'MOCK00000012HDFXYZ', N'donante12@mock.local', N'5510000012', N'8181000012', N'Universidad',    N'212', N'Anáhuac',               N'San Nicolás',    N'Nuevo León',      N'66450', N'México'),
    (13, N'Guadalupe',   N'Martínez',  N'López',      NULL,             NULL, N'MOCK00000013HDFXYZ', N'donante13@mock.local', N'5510000013', N'8181000013', N'Juárez',         N'313', N'Centro',                N'Apodaca',         N'Nuevo León',      N'66600', N'México'),
    (14, N'Fundación Martínez', NULL,   NULL,          NULL,             N'Fundación Martínez A.C.', N'MOCK00000014HDFXYZ', N'donante14@mock.local', N'5510000014', NULL, N'Constitución', N'414', N'Obispado', N'Monterrey', N'Nuevo León', N'64010', N'México'),
    (15, N'Alejandro',   N'Pérez',     N'Pérez',      NULL,             NULL, N'MOCK00000015HDFXYZ', N'donante15@mock.local', N'5510000015', N'8181000015', N'Washington',    N'515', N'Roma',                 N'Monterrey',      N'Nuevo León',      N'64700', N'México'),
    (16, N'Juan',        N'Rodríguez', N'Sánchez',    NULL,             NULL, N'MOCK00000016HDFXYZ', N'donante16@mock.local', N'5510000016', N'8181000016', N'Lincoln',        N'616', N'Valle Verde',           N'Monterrey',      N'Nuevo León',      N'64330', N'México'),
    (17, N'Carlos',      N'Rivera',    N'Sánchez',    NULL,             NULL, N'MOCK00000017HDFXYZ', N'donante17@mock.local', N'5510000017', N'8181000017', N'Madero',         N'717', N'Mitras Centro',         N'Monterrey',      N'Nuevo León',      N'64460', N'México'),
    (18, N'Fernanda',    N'Ramírez',   N'Ortiz',      NULL,             NULL, N'MOCK00000018HDFXYZ', N'donante18@mock.local', N'5510000018', N'8181000018', N'Vasconcelos',    N'818', N'Del Valle',             N'San Pedro',      N'Nuevo León',      N'66220', N'México'),
    (19, N'Alejandro',   N'Ortiz',     N'Torres',     NULL,             NULL, N'MOCK00000019HDFXYZ', N'donante19@mock.local', N'5510000019', N'8181000019', N'Calzada',        N'919', N'Garza García',          N'San Pedro',      N'Nuevo León',      N'66200', N'México'),
    (20, N'Ana',         N'Gómez',     N'Flores',     NULL,             NULL, N'MOCK00000020HDFXYZ', N'donante20@mock.local', N'5510000020', N'8181000020', N'Jardín',         N'120', N'Las Puentes',           N'San Nicolás',    N'Nuevo León',      N'66460', N'México'),
    (21, N'Ricardo',     N'Hernández', N'Cruz',       NULL,             NULL, N'MOCK00000021HDFXYZ', N'donante21@mock.local', N'5510000021', N'8181000021', N'Juárez',         N'221', N'Centro',                N'Guadalupe',      N'Nuevo León',      N'67100', N'México'),
    (22, N'Lucía',       N'García',    N'Morales',    NULL,             NULL, N'MOCK00000022HDFXYZ', N'donante22@mock.local', N'5510000022', N'8181000022', N'Zaragoza',       N'322', N'Centro',                N'Guadalupe',      N'Nuevo León',      N'67100', N'México'),
    (23, N'Miguel',      N'Martínez',  N'Reyes',      NULL,             NULL, N'MOCK00000023HDFXYZ', N'donante23@mock.local', N'5510000023', N'8181000023', N'Juárez',         N'423', N'Centro',                N'Apodaca',         N'Nuevo León',      N'66600', N'México'),
    (24, N'Fundación Torres', NULL,     NULL,          NULL,             N'Fundación Torres A.C.', N'MOCK00000024HDFXYZ', N'donante24@mock.local', N'5510000024', NULL, N'Insurgentes', N'524', N'Contry', N'Monterrey', N'Nuevo León', N'64845', N'México'),
    (25, N'Jorge',       N'Pérez',     N'Vargas',     NULL,             NULL, N'MOCK00000025HDFXYZ', N'donante25@mock.local', N'5510000025', N'8181000025', N'Garza Sada',    N'625', N'Brisas',                N'Monterrey',      N'Nuevo León',      N'64790', N'México'),
    (26, N'Elena',       N'Sánchez',   N'López',      NULL,             NULL, N'MOCK00000026HDFXYZ', N'donante26@mock.local', N'5510000026', N'8181000026', N'Universidad',   N'726', N'Anáhuac',               N'San Nicolás',    N'Nuevo León',      N'66450', N'México'),
    (27, N'Rosa',        N'Ramírez',   N'Díaz',       NULL,             NULL, N'MOCK00000027HDFXYZ', N'donante27@mock.local', N'5510000027', N'8181000027', N'Allende',        N'827', N'Vista Hermosa',         N'Monterrey',      N'Nuevo León',      N'64620', N'México'),
    (28, N'Rafael',      N'López',     N'Castillo',   NULL,             NULL, N'MOCK00000028HDFXYZ', N'donante28@mock.local', N'5510000028', N'8181000028', N'Madero',         N'928', N'Mitras Centro',         N'Monterrey',      N'Nuevo León',      N'64460', N'México'),
    (29, N'Sofía',       N'González',  N'Morales',    NULL,             NULL, N'MOCK00000029HDFXYZ', N'donante29@mock.local', N'5510000029', N'8181000029', N'Pino Suárez',    N'129', N'Independencia',         N'Monterrey',      N'Nuevo León',      N'64020', N'México'),
    (30, N'Fundación Rivera', NULL,    NULL,          NULL,             N'Fundación Rivera A.C.', N'MOCK00000030HDFXYZ', N'donante30@mock.local', N'5510000030', NULL, N'Lincoln', N'230', N'Valle Verde', N'Monterrey', N'Nuevo León', N'64330', N'México'),
    (31, N'Andrés',      N'Flores',    N'Hernández',  NULL,             NULL, N'MOCK00000031HDFXYZ', N'donante31@mock.local', N'5510000031', N'8181000031', N'Washington',    N'331', N'Roma',                 N'Monterrey',      N'Nuevo León',      N'64700', N'México'),
    (32, N'Verónica',    N'Cruz',      N'García',     NULL,             NULL, N'MOCK00000032HDFXYZ', N'donante32@mock.local', N'5510000032', N'8181000032', N'Abasolo',        N'432', N'Centro',                N'San Nicolás',    N'Nuevo León',      N'66400', N'México'),
    (33, N'Jorge',       N'Morales',   N'Pérez',      NULL,             NULL, N'MOCK00000033HDFXYZ', N'donante33@mock.local', N'5510000033', N'8181000033', N'Calzada',        N'533', N'Garza García',          N'San Pedro',      N'Nuevo León',      N'66200', N'México'),
    (34, N'Elena',       N'Ortiz',     N'Sánchez',    NULL,             NULL, N'MOCK00000034HDFXYZ', N'donante34@mock.local', N'5510000034', N'8181000034', N'Jardín',         N'634', N'Las Puentes',           N'San Nicolás',    N'Nuevo León',      N'66460', N'México'),
    (35, N'Rafael',      N'Castillo',  N'Gómez',      NULL,             NULL, N'MOCK00000035HDFXYZ', N'donante35@mock.local', N'5510000035', N'8181000035', N'Constitución',  N'735', N'Obispado',              N'Monterrey',      N'Nuevo León',      N'64010', N'México'),
    (36, N'María',       N'Ramírez',   N'Morales',    NULL,             NULL, N'MOCK00000036HDFXYZ', N'donante36@mock.local', N'5510000036', N'8181000036', N'Juárez',         N'836', N'Centro',                N'Monterrey',      N'Nuevo León',      N'64000', N'México'),
    (37, N'Rosa',        N'Vargas',    N'Torres',     NULL,             NULL, N'MOCK00000037HDFXYZ', N'donante37@mock.local', N'5510000037', N'8181000037', N'Moctezuma',      N'937', N'Linda Vista',           N'Guadalupe',      N'Nuevo León',      N'67123', N'México'),
    (38, N'Patricia',    N'Reyes',     N'Castillo',   NULL,             NULL, N'MOCK00000038HDFXYZ', N'donante38@mock.local', N'5510000038', N'8181000038', N'Pueblo Nuevo',   N'138', N'Contry',                N'Monterrey',      N'Nuevo León',      N'64845', N'México'),
    (39, N'Fundación Gómez', NULL,     NULL,          NULL,             N'Fundación Gómez A.C.', N'MOCK00000039HDFXYZ', N'donante39@mock.local', N'5510000039', NULL, N'Vasconcelos', N'239', N'Del Valle', N'San Pedro', N'Nuevo León', N'66220', N'México'),
    (40, N'María',       N'Hernández', N'Hernández',  NULL,             NULL, N'MOCK00000040HDFXYZ', N'donante40@mock.local', N'5510000040', N'8181000040', N'Zaragoza',       N'340', N'Centro',                N'Guadalupe',      N'Nuevo León',      N'67100', N'México');

    /* ---------------------------------------------------------------
       2. Limpieza de datos de demo
       --------------------------------------------------------------- */
    DELETE FROM dbo.Llamadas;
    DELETE FROM dbo.Abonos;
    DELETE FROM dbo.Promesas;
    DELETE FROM dbo.Causas;
    DELETE FROM dbo.Donantes;
    DELETE FROM dbo.Users WHERE email LIKE N'%@mock.local';

    /* ---------------------------------------------------------------
       3. Donantes
       --------------------------------------------------------------- */
    IF COLUMNPROPERTY(OBJECT_ID(N'dbo.Donantes'), N'id', N'IsIdentity') = 1
        SET IDENTITY_INSERT dbo.Donantes ON;

    IF COL_LENGTH(N'dbo.Donantes', N'nickname') IS NULL
        THROW 51004, 'La tabla Donantes no tiene la columna nickname esperada.', 1;

    INSERT INTO dbo.Donantes (
        id, nombre, apellido_paterno, apellido_materno, nickname,
        razon_social, curp, email, telefono, telefono_oficina, calle,
        numero_exterior, colonia, municipio, estado, codigo_postal, pais
    )
    SELECT id, nombre, apellido_paterno, apellido_materno, nickname,
           razon_social, curp, email, telefono, telefono_oficina, calle,
           numero_exterior, colonia, municipio, estado, codigo_postal, pais
    FROM @Donantes;

    IF COLUMNPROPERTY(OBJECT_ID(N'dbo.Donantes'), N'id', N'IsIdentity') = 1
        SET IDENTITY_INSERT dbo.Donantes OFF;

    /* Estas columnas existen en algunas versiones del esquema. Se llenan
       solo cuando existen, para no romper el seed de la base del reto. */
    IF COL_LENGTH(N'dbo.Donantes', N'dia_nacimiento') IS NOT NULL
        EXEC sys.sp_executesql
            N'
                UPDATE d
                   SET dia_nacimiento = DATEADD(DAY, -(6570 + ((d.id * 97) % 12000)), @hoy)
                FROM dbo.Donantes d;',
            N'@hoy DATETIME2(0)',
            @hoy = @Ahora;

    IF COL_LENGTH(N'dbo.Donantes', N'fecha_creacion') IS NOT NULL
        EXEC sys.sp_executesql
            N'
                UPDATE d
                   SET fecha_creacion = DATEADD(DAY, -((d.id * 11) % 900), @hoy)
                FROM dbo.Donantes d;',
            N'@hoy DATETIME2(0)',
            @hoy = @Ahora;

    /* ---------------------------------------------------------------
       4. Causas
       --------------------------------------------------------------- */
    IF COLUMNPROPERTY(OBJECT_ID(N'dbo.Causas'), N'id', N'IsIdentity') = 1
        SET IDENTITY_INSERT dbo.Causas ON;

    INSERT INTO dbo.Causas
        (id, titulo, descripcion, monto_objetivo, beneficiario, responsable, lugar, fecha_fin)
    VALUES
        (1, N'Despensas para familias vulnerables', N'Recursos destinados a cubrir las necesidades reportadas por la comunidad.', 220000.00, N'Comunidad de Monterrey, N.L.', N'Héctor Ortiz',     N'Monterrey, N.L.',     DATEADD(DAY, 60, @Ahora)),
        (2, N'Becas escolares ciclo 2026-2027', N'Apoyo para estudiantes de familias con recursos limitados.',             390000.00, N'Estudiantes de Guadalajara, Jal.', N'Fernanda Reyes', N'Guadalajara, Jal.',  DATEADD(DAY, 90, @Ahora)),
        (3, N'Rehabilitación del comedor comunitario', N'Renovación del espacio y compra de equipo para preparar alimentos.', 110000.00, N'Comunidad de Ciudad de México', N'Rafael Rivera', N'Ciudad de México', DATEADD(DAY, 120, @Ahora)),
        (4, N'Apoyo a damnificados por inundaciones', N'Atención y entrega de suministros a familias afectadas.',          280000.00, N'Familias de Villahermosa, Tab.', N'Sofía Ramírez', N'Villahermosa, Tab.', NULL),
        (5, N'Medicamentos para adultos mayores', N'Compra de medicamentos y material de atención básica.',              450000.00, N'Adultos mayores de Puebla, Pue.', N'Carlos Pérez', N'Puebla, Pue.', DATEADD(DAY, 180, @Ahora)),
        (6, N'Construcción de aulas rurales', N'Mejoramiento de espacios educativos para comunidades rurales.',         170000.00, N'Estudiantes de Oaxaca, Oax.', N'Elena Martínez', N'Oaxaca, Oax.', DATEADD(DAY, 210, @Ahora)),
        (7, N'Campaña de invierno: cobijas y abrigos', N'Entrega de ropa de abrigo durante la temporada de frío.',         340000.00, N'Familias de Toluca, Edo. Méx.', N'Andrés Vargas', N'Toluca, Edo. Méx.', DATEADD(DAY, 45, @Ahora)),
        (8, N'Equipamiento de casa hogar', N'Compra de camas, muebles y artículos de uso diario.',                  60000.00, N'Casa hogar de Mérida, Yuc.', N'Ana Morales', N'Mérida, Yuc.', NULL);

    IF COLUMNPROPERTY(OBJECT_ID(N'dbo.Causas'), N'id', N'IsIdentity') = 1
        SET IDENTITY_INSERT dbo.Causas OFF;

    /* ---------------------------------------------------------------
       5. Promesas

       Una promesa por donante hace que el riesgo del listado de llamadas y
       el riesgo del detalle del donante se basen en la misma información.
       Todas quedan asignadas al administrador.
       --------------------------------------------------------------- */
    IF COLUMNPROPERTY(OBJECT_ID(N'dbo.Promesas'), N'id', N'IsIdentity') = 1
        SET IDENTITY_INSERT dbo.Promesas ON;

    INSERT INTO dbo.Promesas
        (id, donante_id, caso_id, monto_objetivo, state, fecha_inicio,
         fecha_final, numero_frequencia, tipo_frquencia, responsable_id)
    SELECT
        d.id,
        d.id,
        ((d.id - 1) % 8) + 1,
        CAST(1500 + ((d.id * 17) % 12) * 500 AS DECIMAL(14,2)),
        CASE
            WHEN d.id IN (7, 14, 21, 28) THEN N'cancelado'
            WHEN d.id IN (4, 11, 24, 32, 40) THEN N'completado'
            ELSE N'activo'
        END,
        DATEADD(DAY, -(60 + ((d.id * 13) % 420)), @Ahora),
        NULL,
        CASE WHEN d.id % 3 = 0 THEN 1 ELSE 12 END,
        CASE WHEN d.id % 3 = 0 THEN N'unica' ELSE N'mensual' END,
        @AdminId
    FROM @Donantes d;

    IF COLUMNPROPERTY(OBJECT_ID(N'dbo.Promesas'), N'id', N'IsIdentity') = 1
        SET IDENTITY_INSERT dbo.Promesas OFF;

    /* ---------------------------------------------------------------
       6. Abonos
       --------------------------------------------------------------- */
    IF COLUMNPROPERTY(OBJECT_ID(N'dbo.Abonos'), N'id', N'IsIdentity') = 1
        SET IDENTITY_INSERT dbo.Abonos ON;

    ;WITH Numeros AS (
        SELECT 1 AS n UNION ALL SELECT 2 UNION ALL SELECT 3
    ), AbonosCalculados AS (
        SELECT
            p.id AS promesa_id,
            n.n,
            CAST(p.monto_objetivo / 4 AS DECIMAL(14,2)) AS monto,
            DATEADD(DAY, -(n.n * 30 + ((p.id * 7) % 18)), @Ahora) AS fecha_deposito
        FROM dbo.Promesas p
        CROSS JOIN Numeros n
        WHERE p.state <> N'cancelado'
          AND n.n <= CASE
                        WHEN p.id % 4 = 0 THEN 0
                        WHEN p.id % 4 = 1 THEN 1
                        WHEN p.id % 4 = 2 THEN 2
                        ELSE 3
                     END
    )
    INSERT INTO dbo.Abonos (id, promesa_id, monto, fecha_deposito)
    SELECT ROW_NUMBER() OVER (ORDER BY promesa_id, n), promesa_id, monto, fecha_deposito
    FROM AbonosCalculados;

    IF COLUMNPROPERTY(OBJECT_ID(N'dbo.Abonos'), N'id', N'IsIdentity') = 1
        SET IDENTITY_INSERT dbo.Abonos OFF;

    /* Casos intencionales para la demostración:
       donante 3 = riesgo bajo, donante 38 = riesgo medio,
       donante 36 = riesgo alto/sin abonos. */
    DELETE FROM dbo.Abonos WHERE promesa_id = 36;
    UPDATE dbo.Abonos SET fecha_deposito = DATEADD(DAY, -10, @Ahora) WHERE promesa_id = 3;
    UPDATE dbo.Abonos SET fecha_deposito = DATEADD(DAY, -40, @Ahora) WHERE promesa_id = 38;

    /* ---------------------------------------------------------------
       7. Llamadas

       21 registros en total:
       - 7 para HOY: 4 completadas y 3 agendadas.
       - 14 históricas: todas en fechas pasadas.
       No se generan llamadas futuras para no contaminar Historial.
       --------------------------------------------------------------- */
    DECLARE @Llamadas TABLE (
        id INT PRIMARY KEY,
        promesa_id INT NOT NULL,
        resultado_llamado NVARCHAR(255) NOT NULL,
        monto_comprometido DECIMAL(14,2) NULL,
        estado NVARCHAR(20) NOT NULL,
        proposito NVARCHAR(30) NULL,
        fecha_agendada DATETIME2(0) NOT NULL
    );

    INSERT INTO @Llamadas
        (id, promesa_id, resultado_llamado, monto_comprometido, estado, proposito, fecha_agendada)
    VALUES
        (1, 36, N'contactado',              1200.00, N'completada', N'seguimiento',        DATEADD(HOUR,  9, @Ahora)),
        (2, 38, N'solicita volver a llamar', NULL,   N'completada', N'recordatorio de pago', DATEADD(HOUR, 10, @Ahora)),
        (3, 3,  N'compromiso confirmado',   5500.00, N'completada', N'agradecimiento',      DATEADD(HOUR, 11, @Ahora)),
        (4, 10, N'contactado',              2700.00, N'completada', N'seguimiento',        DATEADD(HOUR, 12, @Ahora)),
        (5, 36, N'solicita volver a llamar', NULL,   N'agendada',   N'seguimiento',        DATEADD(HOUR, 13, @Ahora)),
        (6, 38, N'pendiente',               1500.00, N'agendada',   N'recordatorio de pago', DATEADD(HOUR, 14, @Ahora)),
        (7, 3,  N'pendiente',               5500.00, N'agendada',   N'agradecimiento',      DATEADD(HOUR, 15, @Ahora)),
        (8,  1, N'contactado',              1000.00, N'completada', N'seguimiento',        DATEADD(DAY, -1, @Ahora)),
        (9,  2, N'compromiso confirmado',   2500.00, N'completada', N'agradecimiento',      DATEADD(DAY, -2, @Ahora)),
        (10, 4, N'no contesta',             NULL,    N'completada', N'recordatorio de pago', DATEADD(DAY, -3, @Ahora)),
        (11, 5, N'contactado',              1500.00, N'completada', N'seguimiento',         DATEADD(DAY, -4, @Ahora)),
        (12, 6, N'numero incorrecto',       NULL,    N'completada', N'invitacion a evento',   DATEADD(DAY, -5, @Ahora)),
        (13, 8, N'contactado',              2000.00, N'completada', N'agradecimiento',       DATEADD(DAY, -6, @Ahora)),
        (14, 9, N'compromiso confirmado',   3000.00, N'completada', N'seguimiento',          DATEADD(DAY, -7, @Ahora)),
        (15, 10,N'no contesta',             NULL,    N'completada', N'recordatorio de pago', DATEADD(DAY, -8, @Ahora)),
        (16, 12,N'contactado',              1800.00, N'completada', N'invitacion a evento',   DATEADD(DAY, -9, @Ahora)),
        (17, 15,N'compromiso confirmado',   2200.00, N'completada', N'seguimiento',          DATEADD(DAY, -10, @Ahora)),
        (18, 18,N'no contesta',             NULL,    N'completada', N'agradecimiento',       DATEADD(DAY, -11, @Ahora)),
        (19, 20,N'contactado',              1200.00, N'completada', N'seguimiento',          DATEADD(DAY, -12, @Ahora)),
        (20, 25,N'numero incorrecto',       NULL,    N'completada', N'recordatorio de pago', DATEADD(DAY, -13, @Ahora)),
        (21, 30,N'contactado',              2500.00, N'completada', N'agradecimiento',       DATEADD(DAY, -14, @Ahora));

    IF COLUMNPROPERTY(OBJECT_ID(N'dbo.Llamadas'), N'id', N'IsIdentity') = 1
        SET IDENTITY_INSERT dbo.Llamadas ON;

    INSERT INTO dbo.Llamadas
        (id, promesa_id, resultado_llamado, monto_comprometido, estado, proposito, fecha_agendada)
    SELECT id, promesa_id, resultado_llamado, monto_comprometido, estado, proposito, fecha_agendada
    FROM @Llamadas;

    IF COLUMNPROPERTY(OBJECT_ID(N'dbo.Llamadas'), N'id', N'IsIdentity') = 1
        SET IDENTITY_INSERT dbo.Llamadas OFF;

    COMMIT TRANSACTION;

    /* ---------------------------------------------------------------
       8. Resumen verificable
       --------------------------------------------------------------- */
    SELECT N'Admin' AS dato, CAST(@AdminId AS NVARCHAR(100)) AS valor
    UNION ALL SELECT N'Donantes', CAST(COUNT(*) AS NVARCHAR(100)) FROM dbo.Donantes
    UNION ALL SELECT N'Causas', CAST(COUNT(*) AS NVARCHAR(100)) FROM dbo.Causas
    UNION ALL SELECT N'Promesas', CAST(COUNT(*) AS NVARCHAR(100)) FROM dbo.Promesas
    UNION ALL SELECT N'Abonos', CAST(COUNT(*) AS NVARCHAR(100)) FROM dbo.Abonos
    UNION ALL SELECT N'Llamadas', CAST(COUNT(*) AS NVARCHAR(100)) FROM dbo.Llamadas
    UNION ALL SELECT N'Promesas del admin', CAST(COUNT(*) AS NVARCHAR(100)) FROM dbo.Promesas WHERE responsable_id = @AdminId
    UNION ALL SELECT N'Colonias vacías', CAST(COUNT(*) AS NVARCHAR(100)) FROM dbo.Donantes WHERE colonia IS NULL OR LTRIM(RTRIM(colonia)) = N'';

END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
