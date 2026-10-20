"""Cabeceras de seguridad en todas las respuestas, incluidas las de error."""

from flask import Flask, Response, request

DOCS_PREFIX = "/docs"

# frame-ancestors, base-uri y form-action no heredan de default-src: van
# explicitas en las dos politicas.
NO_FALLBACK = "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
# La API solo devuelve JSON: no carga nada ni se deja embeber.
API_CSP = f"default-src 'none'; {NO_FALLBACK}"
# Swagger UI se sirve desde el mismo origen pero arranca con un <script> inline
# y usa estilos inline e imagenes data:.
DOCS_CSP = (
    "default-src 'self'; script-src 'self' 'unsafe-inline'; "
    f"style-src 'self' 'unsafe-inline'; img-src 'self' data:; {NO_FALLBACK}"
)

SECURE_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Embedder-Policy": "require-corp",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def add_secure_headers(response: Response) -> Response:
    response.headers.update(SECURE_HEADERS)
    is_docs = request.path.startswith(DOCS_PREFIX)
    response.headers["Content-Security-Policy"] = DOCS_CSP if is_docs else API_CSP
    # Las respuestas llevan tokens y datos de donantes: que no queden en caches.
    # Los estaticos de Swagger ya traen su propio Cache-Control.
    response.headers.setdefault("Cache-Control", "no-store, no-cache, must-revalidate")
    return response


def register_secure_headers(app: Flask) -> None:
    app.after_request(add_secure_headers)
