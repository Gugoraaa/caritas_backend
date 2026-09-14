# syntax=docker/dockerfile:1

# --- Etapa de build: resuelve el venv con uv ---------------------------------
FROM python:3.13-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Capa de dependencias: solo se invalida si cambian pyproject.toml o uv.lock.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --group prod --no-install-project

# Capa del proyecto: se invalida con cada cambio de codigo.
COPY README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --group prod


# --- Etapa final: solo el runtime -------------------------------------------
FROM python:3.13-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=3000

RUN useradd --create-home --uid 10001 caritas

WORKDIR /app
COPY --from=builder --chown=caritas:caritas /app /app

USER caritas
EXPOSE 3000

# Sin .env dentro de la imagen: la configuracion entra por variables de entorno
# (docker-compose.yml). load_dotenv() no sobreescribe lo que ya esta en el env.
CMD ["sh", "-c", "exec gunicorn -w ${WEB_CONCURRENCY:-4} -b 0.0.0.0:${PORT:-3000} 'caritas_backend:create_app()'"]
