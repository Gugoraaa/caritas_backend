"""Configuracion de gunicorn, en Docker y en el servidor.

gunicorn lee ./gunicorn.conf.py solo. Sirve HTTPS con el certificado de certs/
(o el de SSL_CERT_FILE y SSL_KEY_FILE); si falta alguno en disco gunicorn no
arranca, en vez de caer a HTTP. Dejarlas vacias sirve HTTP plano (solo dev).

A diferencia del servidor de desarrollo de Flask, gunicorn no expone su version
en la cabecera Server.
"""

import os

from dotenv import load_dotenv

# Fuera de Docker el puerto y el certificado vienen del .env, y gunicorn lee
# esta config antes de que create_app() lo cargue.
load_dotenv()

CERT_FILE = "certs/minihub.tc2007b.tec.mx.cer"
KEY_FILE = "certs/minihub.tc2007b.tec.mx.key"

bind = f"0.0.0.0:{os.environ.get('PORT') or 3000}"
workers = int(os.environ.get("WEB_CONCURRENCY") or 4)
# Sin definir: el de certs/. Definida pero vacia: sin TLS.
certfile = os.environ.get("SSL_CERT_FILE", CERT_FILE) or None
keyfile = os.environ.get("SSL_KEY_FILE", KEY_FILE) or None
