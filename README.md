# caritas_backend_flask

Migración a Flask del backend NestJS que vive en `../caritas_backend`.

Dos endpoints: un health check y un login. El proyecto entero son ~400 líneas.

## Setup

```bash
uv sync
cp .env.example .env   # y completá DB_* y JWT_SECRET
```

Todo se corre con `uv`: `uv add` para dependencias, `uv run` para ejecutar.

## Correr

```bash
uv run python -m caritas_backend     # dev, escucha en 0.0.0.0:$PORT (default 3000)
uv run caritas-backend               # idéntico, vía el script del proyecto
```

El servidor de desarrollo de Flask no es para producción. Con un WSGI real:

```bash
uv run --group prod gunicorn -w 4 -b 0.0.0.0:3000 'caritas_backend:create_app()'
```

`gunicorn` vive en el grupo `prod`, que `uv sync` no instala. Es el mismo
comando que corre la imagen de Docker.

La app arranca aunque SQL Server esté caído: se loguea un warning y listo. En
ese estado `GET /` responde 200 y `POST /login` responde 500.

## Docker

```bash
docker compose up --build    # SQL Server + esquema + datos mock + API en http://localhost:3000
docker compose down          # baja todo; los datos quedan en el volumen
docker compose down -v       # baja todo y borra la base
```

Tres servicios:

| Servicio    | Qué hace                                                                 |
| ----------- | ------------------------------------------------------------------------ |
| `sqlserver` | SQL Server 2022 Developer, datos en el volumen `mssql-data`               |
| `db-init`   | Espera a SQL Server, crea la base `caritas` y le aplica los `.sql` de `db/` |
| `api`       | La imagen del `Dockerfile`, servida con gunicorn                         |

`db-init` corre una sola vez y termina; `api` no arranca hasta que salga en 0
(`service_completed_successfully`), así que la base ya está poblada cuando la
API levanta.

### Usuario de prueba

Después de `docker compose up` ya se puede pegar a `POST /login` con:

| email               | contraseña | role    |
| ------------------- | ---------- | ------- |
| `admin@caritas.com` | `admin123` | `admin` |

```bash
curl -X POST http://localhost:3000/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@caritas.com","password":"admin123"}'
```

Los usuarios mock (`user1@mock.local` … `user6@mock.local`) llevan un hash de
relleno a propósito: existen para poblar `Promesas.responsable_id`, no se puede
hacer login con ellos.

### Qué carga `db-init`, y cuándo

| Carpeta         | Contenido                            | Cuándo se aplica                                  |
| --------------- | ------------------------------------ | ------------------------------------------------- |
| `db/schema/`    | `CREATE TABLE`, índices, FKs         | solo si la base no tiene **ninguna** tabla         |
| `db/seed/`      | datos mock (donantes, causas, …)     | solo si la tabla `Donantes` está vacía             |
| `db/bootstrap/` | usuario admin                        | **siempre** (el script es idempotente)             |

Dentro de cada carpeta los archivos van en orden alfabético, por eso están
numerados (`01_`, `02_`, …). No necesitan `CREATE DATABASE` ni `USE`: `db-init`
ya se conecta a la base correcta.

Los tres pasos son **idempotentes**, así que `up` repetidos no pisan datos.
El paso de datos mock se controla con `DB_SEED`:

```bash
docker compose up                  # auto: carga los mock solo si no hay donantes
DB_SEED=force docker compose up    # borra los mock y los reinserta
DB_SEED=skip  docker compose up    # base vacía, solo esquema y admin
```

Para arrancar de cero del todo, `docker compose down -v`.

### A qué base se conecta cada forma de correr

Esto es a propósito y lo resuelve `load_dotenv()`, que **no** sobreescribe
variables que ya existen en el entorno:

| Cómo levantás la API                     | Base a la que pega                          |
| ---------------------------------------- | ------------------------------------------- |
| `docker compose up`                      | el contenedor `sqlserver` (`DB_HOST=sqlserver`) |
| `uv run python -m caritas_backend`       | la de producción, la del `.env`             |

`docker-compose.yml` inyecta las `DB_*` como variables de entorno del
contenedor, y ganan. Fuera de Docker no hay nada en el entorno, así que
`load_dotenv()` carga el `.env` y se usa producción. Además `.env` está en
`.dockerignore`: las credenciales de producción **no entran a la imagen**.

Las credenciales del compose son locales y de desarrollo (SA
`Caritas_Local_2026!`, `JWT_SECRET=dev-secret-solo-para-docker`). Para cambiar
algo sin tocar el archivo versionado, usá un `docker-compose.override.yml`.

Los puertos publicados se pueden mover si están ocupados:

```bash
API_HOST_PORT=3001 SQLSERVER_HOST_PORT=14330 docker compose up
```

### Conectarse a la base del contenedor

La imagen de SQL Server 2022 no trae `sqlcmd`, así que se usa la de
`mssql-tools` que ya está en el compose:

```bash
docker compose run --rm --entrypoint /opt/mssql-tools/bin/sqlcmd db-init \
  -S sqlserver,1433 -U sa -P 'Caritas_Local_2026!' -d caritas -Q "SELECT * FROM Users"
```

O desde el host con cualquier cliente: `localhost:1433`, usuario `sa`.

## Endpoints

| Método | Ruta     | Body                  | 200                        | Errores                                         |
| ------ | -------- | --------------------- | -------------------------- | ----------------------------------------------- |
| GET    | `/`      | —                     | `Hello World!` (text/html) | —                                               |
| POST   | `/login` | `{ email, password }` | `{ token, user }`          | 400 validación · 401 credenciales · 500 interno |

`POST /login` va sin prefijo `/auth` y devuelve 200, como el original. `user` es
`{ id, name, email, role }`: `password_hash` nunca sale.

Cualquier otra ruta **o método** devuelve 404 (no 405): `Cannot {MÉTODO} {ruta}`.

### Formato de errores

```jsonc
// 400 de validación: message es un ARREGLO con todos los errores
{"message":["email must be an email"],"error":"Bad Request","statusCode":400}
// el resto: message es un STRING
{"message":"Correo o contrasena incorrectos","error":"Unauthorized","statusCode":401}
{"message":"Cannot POST /loginn","error":"Not Found","statusCode":404}
```

## Tests y linting

```bash
uv run pytest
uv run ruff check
uv run ruff format
```

Los tests no tocan SQL Server: el repositorio se reemplaza por un doble.

## Cómo está organizado

```
src/caritas_backend/
├── app.py         # create_app(): arma los servicios, los handlers y las rutas
├── config.py      # lectura de variables de entorno
├── routes.py      # router principal: registra los blueprints de cada módulo
├── errors.py      # HttpException y los handlers que arman el JSON de error
├── validation.py  # valida el body y descarta los campos que no se declararon
├── security.py    # bcrypt y firma de tokens
├── database.py    # pool de conexiones a SQL Server
└── modules/
    ├── app/       # GET /
    ├── auth/      # POST /login
    └── users/     # consultas sobre la tabla Users
```

El flujo es **controller → service → repository → database**. Los controllers no
tocan la base. Los servicios se crean una vez en `create_app()` y viven en
`app.extensions`.

### Cosas que parecen bugs y no lo son

- **`login` siempre corre bcrypt**, exista el usuario o no, comparando contra un
  hash de descarte. Si cortáramos antes, el tiempo de respuesta delataría qué
  correos están registrados. No agregar un early return.
- **El email no se normaliza** (sin `trim`, sin `lower`). La insensibilidad a
  mayúsculas la da la collation de SQL Server, no el código.
- **Sin `JWT_SECRET` la app no arranca**, en vez de usar un secreto por defecto.
- **Sin CORS, sin guard de JWT, sin CRUD de usuarios.** El original no los
  tiene; el token se emite pero todavía nada lo verifica.

## Diferencias aceptadas con el backend NestJS

Se priorizó que el código sea corto y legible por sobre replicar casos borde:

- **Emails raros.** La validación usa un regex simple. Direcciones exóticas que
  Nest aceptaba o rechazaba (comillas en el local part, TLD unicode, IPs entre
  corchetes) pueden dar distinto. Los emails normales se comportan igual.
- **Texto del error de JSON roto.** Nest devolvía el mensaje del parser de
  Node; acá sale el de Python. El código y la forma de la respuesta son iguales.
  Un body JSON que no sea objeto (`null`, `"hola"`) ahora se trata como body
  vacío en vez de dar error de parseo.
- **Conexiones ociosas.** El pool original las cerraba a los 30 segundos; este
  las mantiene abiertas. Para esta carga no hace diferencia.
