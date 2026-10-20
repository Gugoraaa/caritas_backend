import os

from .app import create_app
from .config import get

CERT_FILE = "certs/minihub.tc2007b.tec.mx.cer"
KEY_FILE = "certs/minihub.tc2007b.tec.mx.key"


def main() -> None:
    app = create_app()

    # Servidor de desarrollo: por defecto solo acepta conexiones de esta maquina.
    # HOST=0.0.0.0 lo abre a la red (p. ej. para probar desde un iPad). Docker
    # no pasa por aca, usa gunicorn.conf.py.
    # Rutas del certificado relativas a la raiz del repo. Ver certs/ en el README.
    app.run(
        host=get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT") or 3000),
        ssl_context=(get("SSL_CERT_FILE", CERT_FILE), get("SSL_KEY_FILE", KEY_FILE)),
    )


if __name__ == "__main__":
    main()
