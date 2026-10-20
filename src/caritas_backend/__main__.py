import os

from werkzeug.serving import WSGIRequestHandler

from .app import create_app
from .config import get

CERT_FILE = "certs/minihub.tc2007b.tec.mx.cer"
KEY_FILE = "certs/minihub.tc2007b.tec.mx.key"
SERVER_NAME = "caritas-backend"


class RequestHandler(WSGIRequestHandler):
    """Sin version en la cabecera Server (Werkzeug/x.y Python/x.y)."""

    def version_string(self) -> str:
        return SERVER_NAME


def main() -> None:
    app = create_app()

    # Por defecto solo acepta conexiones de esta maquina. HOST=0.0.0.0 lo abre
    # a la red: es lo que usa el servidor (ver su .env).
    # Rutas del certificado relativas a la raiz del repo. Ver certs/ en el README.
    app.run(
        host=get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT") or 3000),
        ssl_context=(get("SSL_CERT_FILE", CERT_FILE), get("SSL_KEY_FILE", KEY_FILE)),
        request_handler=RequestHandler,
    )


if __name__ == "__main__":
    main()
