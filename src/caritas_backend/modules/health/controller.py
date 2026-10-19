import logging

from flask import Blueprint, Response, current_app, jsonify

# Cambiar en cada despliegue (fecha + numero si hay varios el mismo dia) para
# saber que version corre el servidor. La imagen de Docker no incluye .git,
# asi que no se puede leer el commit en tiempo de ejecucion.
API_VERSION = "2026.10.18"

DB_OK = "ok"
DB_ERROR = "error"

blueprint = Blueprint("health", __name__)

log = logging.getLogger(__name__)


@blueprint.get("/health")
def health() -> Response:
    return jsonify(
        {
            "status": "ok",
            "version": API_VERSION,
            "database": check_database(current_app.extensions["database"]),
        }
    )


def check_database(database) -> str:
    try:
        with database.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
            finally:
                cursor.close()
        return DB_OK
    except Exception:
        log.warning("Health check: database is not reachable", exc_info=True)
        return DB_ERROR
