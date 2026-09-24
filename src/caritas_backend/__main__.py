import os

from .app import create_app


def main() -> None:
    app = create_app()

    # Update these paths to point to your SSL certificate and key files
    cert_path = "/home/user01/mnt/caritas_backend/src/caritas_backend/cert-equipo/minihub.tc2007b.tec.mx.cer"
    key_path = "/home/user01/mnt/caritas_backend/src/caritas_backend/cert-equipo/minihub.tc2007b.tec.mx.key"

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT") or 3000),
        ssl_context=(cert_path, key_path),
    )


if __name__ == "__main__":
    main()
