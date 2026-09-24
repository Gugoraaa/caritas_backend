/* ============================================================================
   seed_mock_caritas.sql
   Datos mock para la base "caritas" (SQL Server).

   Tablas que puebla: Users (solo usuarios mock), Donantes, Causas,
   Promesas, Abonos, Llamadas.

   OJO: con @RESET = 1 (valor por defecto) BORRA TODAS las filas de
   Donantes, Causas, Promesas, Abonos y Llamadas, y los usuarios cuyo
   email termina en @mock.local. Los usuarios reales no se tocan.
   Pon @RESET = 0 si solo quieres agregar encima de lo que ya hay.

   Los datos son deterministas: correrlo dos veces genera lo mismo.
   ============================================================================ */

/* Todo el script es UN SOLO lote (sin GO): selecciona la base "caritas" en tu
   cliente antes de ejecutarlo, o agrega "USE caritas;" arriba si tu cliente
   sí soporta GO como separador de lotes. */

SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @RESET       BIT = 1;    -- 1 = limpiar antes de insertar
DECLARE @N_USERS     INT = 6;
DECLARE @N_DONANTES  INT = 40;
DECLARE @N_CAUSAS    INT = 8;
DECLARE @N_PROMESAS  INT = 60;
DECLARE @MOCK_DOMAIN NVARCHAR(50) = N'@mock.local';
-- Fecha local de Monterrey (UTC-6): las llamadas agendadas se siembran
-- relativas a HOY para que la pantalla "Hoy" siempre tenga datos.
DECLARE @hoy DATE = CAST(DATEADD(HOUR, -6, SYSUTCDATETIME()) AS DATE);

BEGIN TRY
BEGIN TRANSACTION;

/* ---------------------------------------------------------------------------
   0. Limpieza (en orden de dependencias: hijos primero)
   --------------------------------------------------------------------------- */
IF @RESET = 1
BEGIN
    DELETE FROM dbo.Llamadas;
    DELETE FROM dbo.Abonos;
    DELETE FROM dbo.Promesas;
    DELETE FROM dbo.Causas;
    DELETE FROM dbo.Donantes;
    DELETE FROM dbo.Users WHERE email LIKE '%' + @MOCK_DOMAIN;
END

/* Tabla de números reutilizable (1..1000) */
DECLARE @nums TABLE (i INT PRIMARY KEY);
INSERT INTO @nums (i)
SELECT TOP (1000) ROW_NUMBER() OVER (ORDER BY (SELECT NULL))
FROM sys.all_objects a CROSS JOIN sys.all_objects b;

/* Catálogos de nombres para que los datos se vean creíbles */
DECLARE @nombres TABLE (i INT IDENTITY(1,1), v NVARCHAR(50));
INSERT INTO @nombres (v) VALUES
    (N'María'),(N'José'),(N'Guadalupe'),(N'Juan'),(N'Ana'),(N'Carlos'),
    (N'Fernanda'),(N'Ricardo'),(N'Lucía'),(N'Miguel'),(N'Patricia'),(N'Andrés'),
    (N'Sofía'),(N'Héctor'),(N'Rosa'),(N'Alejandro'),(N'Verónica'),(N'Jorge'),
    (N'Elena'),(N'Rafael');

DECLARE @apellidos TABLE (i INT IDENTITY(1,1), v NVARCHAR(50));
INSERT INTO @apellidos (v) VALUES
    (N'Hernández'),(N'García'),(N'Martínez'),(N'López'),(N'González'),
    (N'Pérez'),(N'Rodríguez'),(N'Sánchez'),(N'Ramírez'),(N'Torres'),
    (N'Flores'),(N'Rivera'),(N'Gómez'),(N'Díaz'),(N'Reyes'),
    (N'Cruz'),(N'Morales'),(N'Ortiz'),(N'Castillo'),(N'Vargas');

DECLARE @nNombres   INT = (SELECT COUNT(*) FROM @nombres);
DECLARE @nApellidos INT = (SELECT COUNT(*) FROM @apellidos);

/* Offsets de id: con @RESET = 1 son 0; con @RESET = 0 continúan la numeración
   existente para no chocar con la PK */
DECLARE @offDonante  INT = ISNULL((SELECT MAX(id) FROM dbo.Donantes), 0);
DECLARE @offCausa    INT = ISNULL((SELECT MAX(id) FROM dbo.Causas),   0);
DECLARE @offPromesa  INT = ISNULL((SELECT MAX(id) FROM dbo.Promesas), 0);
DECLARE @offAbono    INT = ISNULL((SELECT MAX(id) FROM dbo.Abonos),   0);
DECLARE @offLlamada  INT = ISNULL((SELECT MAX(id) FROM dbo.Llamadas), 0);

/* ---------------------------------------------------------------------------
   1. Users  (respeta el IDENTITY existente; no pisa usuarios reales)
   --------------------------------------------------------------------------- */
DECLARE @users TABLE (rn INT IDENTITY(1,1), id INT);
DECLARE @usersTieneIdentity BIT =
    ISNULL(OBJECTPROPERTY(OBJECT_ID('dbo.Users'), 'TableHasIdentity'), 0);

/* Roles candidatos. dbo.Users tiene un CHECK sobre "role", así que de esta
   lista se descartan automáticamente los valores que el CHECK no acepta.
   Si tu catálogo de roles es otro, agrégalo aquí. */
DECLARE @roles TABLE (i INT, v NVARCHAR(50));
INSERT INTO @roles (i, v) VALUES
    (1, N'admin'), (2, N'coordinador'), (3, N'promotor'),
    (4, N'user'),  (5, N'usuario'),     (6, N'capturista'),
    (7, N'Admin'), (8, N'ADMIN'),       (9, N'operador');

/* Definición del CHECK de la columna "role", si existe */
DECLARE @ckRole NVARCHAR(MAX) = (
    SELECT TOP (1) cc.definition
    FROM sys.check_constraints cc
    WHERE cc.parent_object_id = OBJECT_ID('dbo.Users')
      AND cc.definition LIKE N'%[[]role]%'   -- cubre checks de columna y de tabla
);

/* Deja solo los roles que aparecen literalmente en el CHECK */
IF @ckRole IS NOT NULL
    DELETE FROM @roles WHERE CHARINDEX(N'''' + v + N'''', @ckRole) = 0;

IF NOT EXISTS (SELECT 1 FROM @roles)
BEGIN
    DECLARE @msg NVARCHAR(2000) =
        N'Ningún rol de la lista @roles pasa el CHECK de dbo.Users.role. '
      + N'Definición del constraint: ' + ISNULL(@ckRole, N'(no encontrada)')
      + N' -- agrega uno de esos valores a @roles y vuelve a correr el script.';
    THROW 50001, @msg, 1;
END

/* Renumera los roles que sobrevivieron para poder repartirlos por módulo */
DECLARE @rolesOk TABLE (i INT IDENTITY(1,1), v NVARCHAR(50));
INSERT INTO @rolesOk (v) SELECT v FROM @roles ORDER BY i;
DECLARE @nRoles INT = (SELECT COUNT(*) FROM @rolesOk);

DECLARE @nuevosUsers TABLE (
    rn    INT,
    name  NVARCHAR(100),
    email NVARCHAR(255),
    rol   NVARCHAR(50)
);

INSERT INTO @nuevosUsers (rn, name, email, rol)
SELECT
    n.i,
    nom.v + N' ' + ape.v,
    LOWER(N'user' + CAST(n.i AS NVARCHAR(10))) + @MOCK_DOMAIN,
    rol.v
FROM @nums n
JOIN @nombres   nom ON nom.i = ((n.i * 3) % @nNombres) + 1
JOIN @apellidos ape ON ape.i = ((n.i * 7) % @nApellidos) + 1
JOIN @rolesOk   rol ON rol.i = (n.i % @nRoles) + 1
WHERE n.i <= @N_USERS;

IF @usersTieneIdentity = 1
BEGIN
    /* Ids 1..N fijos (si estan libres): user1..userN conservan su id entre
       re-seeds, asi los responsable_id y el user_id de la app no se rompen.
       Si algun id 1..N ya lo ocupa un usuario real, se usa IDENTITY normal. */
    IF NOT EXISTS (SELECT 1 FROM dbo.Users WHERE id BETWEEN 1 AND @N_USERS)
    BEGIN
        SET IDENTITY_INSERT dbo.Users ON;

        INSERT INTO dbo.Users (id, name, email, password_hash, role, created_at)
        OUTPUT inserted.id INTO @users (id)
        SELECT u.rn,
               u.name,
               u.email,
               /* hash de relleno, NO es una contraseña utilizable */
               N'$2y$10$mockmockmockmockmockmockmockmockmockmockmockmockmockmo',
               u.rol,
               DATEADD(DAY, -(u.rn * 30), SYSUTCDATETIME())
        FROM @nuevosUsers u
        WHERE NOT EXISTS (SELECT 1 FROM dbo.Users e WHERE e.email = u.email);

        SET IDENTITY_INSERT dbo.Users OFF;
    END
    ELSE
    BEGIN
        INSERT INTO dbo.Users (name, email, password_hash, role, created_at)
        OUTPUT inserted.id INTO @users (id)
        SELECT u.name,
               u.email,
               /* hash de relleno, NO es una contraseña utilizable */
               N'$2y$10$mockmockmockmockmockmockmockmockmockmockmockmockmockmo',
               u.rol,
               DATEADD(DAY, -(u.rn * 30), SYSUTCDATETIME())
        FROM @nuevosUsers u
        WHERE NOT EXISTS (SELECT 1 FROM dbo.Users e WHERE e.email = u.email);
    END
END

ELSE
BEGIN
    /* Ids 1..N fijos si estan libres (base 0): user1..userN conservan su id
       entre re-seeds. Si 1..N esta ocupado, se continua desde MAX(id). */
    DECLARE @baseUserId INT =
        CASE WHEN NOT EXISTS (SELECT 1 FROM dbo.Users WHERE id BETWEEN 1 AND @N_USERS)
             THEN 0
             ELSE ISNULL((SELECT MAX(id) FROM dbo.Users), 0) END;

    INSERT INTO dbo.Users (id, name, email, password_hash, role, created_at)
    OUTPUT inserted.id INTO @users (id)
    SELECT @baseUserId + u.rn,
           u.name,
           u.email,
           N'$2y$10$mockmockmockmockmockmockmockmockmockmockmockmockmockmo',
           u.rol,
           DATEADD(DAY, -(u.rn * 30), SYSUTCDATETIME())
    FROM @nuevosUsers u
    WHERE NOT EXISTS (SELECT 1 FROM dbo.Users e WHERE e.email = u.email);
END

/* Si el script se corre con @RESET = 0 y los mock ya existían, los recupera */
IF NOT EXISTS (SELECT 1 FROM @users)
    INSERT INTO @users (id)
    SELECT id FROM dbo.Users WHERE email LIKE '%' + @MOCK_DOMAIN;

DECLARE @nUsers INT = (SELECT COUNT(*) FROM @users);

/* ---------------------------------------------------------------------------
   2. Donantes
       curp tiene índice UNIQUE: en SQL Server eso solo admite UN NULL,
       así que todos los donantes llevan curp distinta.
   --------------------------------------------------------------------------- */
IF OBJECTPROPERTY(OBJECT_ID('dbo.Donantes'), 'TableHasIdentity') = 1
    SET IDENTITY_INSERT dbo.Donantes ON;

INSERT INTO dbo.Donantes
    (id, nombre, apellido_paterno, apellido_materno, apodo, razon_social,
     curp, email, fecha_creacion, dia_nacimiento, telefono_oficina, telefono)
SELECT
    @offDonante + n.i,
    CASE WHEN n.i % 7 = 0 THEN N'Fundación ' + ape.v   -- 1 de cada 7 es empresa
         ELSE nom.v END,
    CASE WHEN n.i % 7 = 0 THEN NULL ELSE ape.v END,
    CASE WHEN n.i % 7 = 0 THEN NULL ELSE ape2.v END,
    CASE WHEN n.i % 5 = 0 THEN LOWER(nom.v) + CAST(n.i AS NVARCHAR(10)) ELSE NULL END,
    CASE WHEN n.i % 7 = 0 THEN N'Fundación ' + ape.v + N' S.A. de C.V.' ELSE NULL END,
    N'MOCK' + RIGHT(N'00000000' + CAST(@offDonante + n.i AS NVARCHAR(10)), 8) + N'HDFXYZ',
    CASE WHEN n.i % 9 = 0 THEN NULL
         ELSE LOWER(N'donante' + CAST(@offDonante + n.i AS NVARCHAR(10))) + @MOCK_DOMAIN END,
    DATEADD(DAY, -((n.i * 11) % 900), SYSUTCDATETIME()),
    CASE WHEN n.i % 7 = 0 THEN NULL
         ELSE DATEADD(DAY, -((n.i * 97) % 20000) - 6570, CAST(SYSUTCDATETIME() AS DATE)) END,
    CASE WHEN n.i % 4 = 0
         THEN N'55' + RIGHT(N'00000000' + CAST(10000000 + (n.i * 4567) % 89999999 AS NVARCHAR(10)), 8)
         ELSE NULL END,
    N'55' + RIGHT(N'00000000' + CAST(10000000 + (n.i * 1234) % 89999999 AS NVARCHAR(10)), 8)
FROM @nums n
JOIN @nombres   nom  ON nom.i  = ((n.i * 5) % @nNombres) + 1
JOIN @apellidos ape  ON ape.i  = ((n.i * 3) % @nApellidos) + 1
JOIN @apellidos ape2 ON ape2.i = ((n.i * 11) % @nApellidos) + 1
WHERE n.i <= @N_DONANTES;

IF OBJECTPROPERTY(OBJECT_ID('dbo.Donantes'), 'TableHasIdentity') = 1
    SET IDENTITY_INSERT dbo.Donantes OFF;

/* ---------------------------------------------------------------------------
   3. Causas
   --------------------------------------------------------------------------- */
DECLARE @titulos TABLE (i INT IDENTITY(1,1), titulo NVARCHAR(200), lugar NVARCHAR(255));
INSERT INTO @titulos (titulo, lugar) VALUES
    (N'Despensas para familias vulnerables',      N'Monterrey, N.L.'),
    (N'Becas escolares ciclo 2026-2027',          N'Guadalajara, Jal.'),
    (N'Rehabilitación del comedor comunitario',   N'Ciudad de México'),
    (N'Apoyo a damnificados por inundaciones',    N'Villahermosa, Tab.'),
    (N'Medicamentos para adultos mayores',        N'Puebla, Pue.'),
    (N'Construcción de aulas rurales',            N'Oaxaca, Oax.'),
    (N'Campaña de invierno: cobijas y abrigos',   N'Toluca, Edo. Méx.'),
    (N'Equipamiento de casa hogar',               N'Mérida, Yuc.');

DECLARE @nTitulos INT = (SELECT COUNT(*) FROM @titulos);

IF OBJECTPROPERTY(OBJECT_ID('dbo.Causas'), 'TableHasIdentity') = 1
    SET IDENTITY_INSERT dbo.Causas ON;

INSERT INTO dbo.Causas
    (id, titulo, fecha_fin, descripcion, monto_objetivo, beneficiario, responsable, lugar)
SELECT
    @offCausa + n.i,
    t.titulo,
    CASE WHEN n.i % 4 = 0 THEN NULL   -- causas abiertas sin fecha de cierre
         ELSE DATEADD(DAY, ((n.i * 37) % 240) + 30, CAST(SYSUTCDATETIME() AS DATE)) END,
    N'Causa de prueba: ' + t.titulo + N'. Recursos destinados a cubrir las '
        + N'necesidades reportadas por la comunidad en ' + t.lugar + N'.',
    CAST((((n.i * 17) % 45) + 5) * 10000 AS DECIMAL(14, 2)),
    N'Comunidad de ' + t.lugar,
    nom.v + N' ' + ape.v,
    t.lugar
FROM @nums n
JOIN @titulos   t   ON t.i    = ((n.i - 1) % @nTitulos) + 1
JOIN @nombres   nom ON nom.i  = ((n.i * 13) % @nNombres) + 1
JOIN @apellidos ape ON ape.i  = ((n.i * 17) % @nApellidos) + 1
WHERE n.i <= @N_CAUSAS;

IF OBJECTPROPERTY(OBJECT_ID('dbo.Causas'), 'TableHasIdentity') = 1
    SET IDENTITY_INSERT dbo.Causas OFF;

/* ---------------------------------------------------------------------------
   4. Promesas
   --------------------------------------------------------------------------- */
IF OBJECTPROPERTY(OBJECT_ID('dbo.Promesas'), 'TableHasIdentity') = 1
    SET IDENTITY_INSERT dbo.Promesas ON;

INSERT INTO dbo.Promesas
    (id, donante_id, caso_id, monto_objetivo, estado, fecha_inicio, fecha_final,
     numero_frequencia, tipo_frquencia, responsable_id)
SELECT
    @offPromesa + n.i,
    @offDonante + ((n.i * 7) % @N_DONANTES) + 1,   -- donante_id
    @offCausa   + ((n.i * 3) % @N_CAUSAS) + 1,     -- caso_id
    CAST((((n.i * 23) % 48) + 2) * 500 AS DECIMAL(14, 2)),
    CASE n.i % 5 WHEN 0 THEN N'cancelado'
                 WHEN 1 THEN N'completado'
                 ELSE N'activo' END,
    DATEADD(DAY, -((n.i * 13) % 540), CAST(SYSUTCDATETIME() AS DATE)),
    CASE WHEN n.i % 3 = 0 THEN NULL                -- promesas sin fecha de cierre
         ELSE DATEADD(DAY, ((n.i * 19) % 300) + 15, CAST(SYSUTCDATETIME() AS DATE)) END,
    CASE n.i % 4 WHEN 0 THEN 1 WHEN 1 THEN 6 WHEN 2 THEN 12 ELSE 3 END,
    CASE n.i % 4 WHEN 0 THEN N'unica'
                 WHEN 1 THEN N'semestral'
                 WHEN 2 THEN N'mensual'
                 ELSE N'trimestral' END,
    CASE WHEN n.i % 7 = 0 THEN NULL                -- algunas promesas sin responsable
         ELSE (SELECT u.id FROM @users u WHERE u.rn = ((n.i - 1) % @nUsers) + 1) END
FROM @nums n
WHERE n.i <= @N_PROMESAS;

IF OBJECTPROPERTY(OBJECT_ID('dbo.Promesas'), 'TableHasIdentity') = 1
    SET IDENTITY_INSERT dbo.Promesas OFF;

/* ---------------------------------------------------------------------------
   5. Abonos  (entre 0 y 4 por promesa; las canceladas no abonan)
   --------------------------------------------------------------------------- */
IF OBJECTPROPERTY(OBJECT_ID('dbo.Abonos'), 'TableHasIdentity') = 1
    SET IDENTITY_INSERT dbo.Abonos ON;

INSERT INTO dbo.Abonos (id, promesa_id, monto, fecha_deposito)
SELECT
    @offAbono + ROW_NUMBER() OVER (ORDER BY p.id, k.i),
    p.id,
    CAST(p.monto_objetivo / (((p.id - @offPromesa) % 4) + 2) AS DECIMAL(14, 2)),
    DATEADD(DAY, k.i * 30, p.fecha_inicio)
FROM dbo.Promesas p
JOIN @nums k ON k.i <= ((p.id - @offPromesa) * 3) % 5    -- 0..4 abonos
WHERE p.id > @offPromesa                                 -- solo las recién creadas
  AND p.estado <> N'cancelado'
  AND DATEADD(DAY, k.i * 30, p.fecha_inicio) <= SYSUTCDATETIME();

IF OBJECTPROPERTY(OBJECT_ID('dbo.Abonos'), 'TableHasIdentity') = 1
    SET IDENTITY_INSERT dbo.Abonos OFF;

/* ---------------------------------------------------------------------------
   6. Llamadas  (0 a 2 por promesa)
       "estado" tiene CHECK: solo agendada / cancelada / completada
       fecha_agendada es relativa a @hoy: ayer, hoy, manana, +2 o +4 dias,
       para que la ventana de hoy+manana siempre tenga contenido.
   --------------------------------------------------------------------------- */
IF OBJECTPROPERTY(OBJECT_ID('dbo.Llamadas'), 'TableHasIdentity') = 1
    SET IDENTITY_INSERT dbo.Llamadas ON;

INSERT INTO dbo.Llamadas
    (id, resultado_llamado, monto_comprometido, estado, proposito, fecha_agendada, promesa_id)
SELECT
    @offLlamada + ROW_NUMBER() OVER (ORDER BY p.id, k.i),
    CASE (p.id + k.i) % 5 WHEN 0 THEN N'contactado'
                          WHEN 1 THEN N'no contesta'
                          WHEN 2 THEN N'numero incorrecto'
                          WHEN 3 THEN N'compromiso confirmado'
                          ELSE N'solicita volver a llamar' END,
    CASE WHEN (p.id + k.i) % 3 = 0 THEN NULL
         ELSE CAST((((p.id * 11) % 20) + 1) * 250 AS DECIMAL(14, 2)) END,
    CASE (p.id + k.i) % 6 WHEN 0 THEN N'cancelada'
                          WHEN 1 THEN N'agendada'
                          ELSE N'completada' END,
    CASE (p.id + k.i) % 4 WHEN 0 THEN N'seguimiento'
                          WHEN 1 THEN N'agradecimiento'
                          WHEN 2 THEN N'recordatorio de pago'
                          ELSE N'invitacion a evento' END,
    DATEADD(HOUR, 9 + (k.i * 3), CONVERT(DATETIME,
        DATEADD(DAY,
            CASE (p.id + k.i) % 5 WHEN 0 THEN -1 WHEN 1 THEN 0 WHEN 2 THEN 1
                                  WHEN 3 THEN 2 ELSE 4 END,
            @hoy))),
    p.id
FROM dbo.Promesas p
JOIN @nums k ON k.i <= ((p.id - @offPromesa) * 7) % 3    -- 0..2 llamadas
WHERE p.id > @offPromesa;                                -- solo las recién creadas

IF OBJECTPROPERTY(OBJECT_ID('dbo.Llamadas'), 'TableHasIdentity') = 1
    SET IDENTITY_INSERT dbo.Llamadas OFF;

COMMIT TRANSACTION;

/* ---------------------------------------------------------------------------
   7. Resumen
   --------------------------------------------------------------------------- */
SELECT 'Users (mock)' AS tabla, COUNT(*) AS filas FROM dbo.Users WHERE email LIKE '%' + @MOCK_DOMAIN
UNION ALL SELECT 'Donantes', COUNT(*) FROM dbo.Donantes
UNION ALL SELECT 'Causas',   COUNT(*) FROM dbo.Causas
UNION ALL SELECT 'Promesas', COUNT(*) FROM dbo.Promesas
UNION ALL SELECT 'Abonos',   COUNT(*) FROM dbo.Abonos
UNION ALL SELECT 'Llamadas', COUNT(*) FROM dbo.Llamadas;

END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH
