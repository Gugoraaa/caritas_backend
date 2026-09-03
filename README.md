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
uv run --with gunicorn gunicorn -w 4 -b 0.0.0.0:3000 'caritas_backend:create_app()'
```

La app arranca aunque SQL Server esté caído: se loguea un warning y listo. En
ese estado `GET /` responde 200 y `POST /login` responde 500.

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
