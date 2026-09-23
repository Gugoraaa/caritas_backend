from flask import Blueprint

from .service import get_hello

blueprint = Blueprint("app", __name__)


@blueprint.get("/")
def root() -> str:
    """Estado del servicio
    ---
    get:
      summary: Estado del servicio
      tags:
        - App
      responses:
        200:
          description: Mensaje de saludo del backend
          content:
            text/plain:
              schema:
                type: string
    """
    return get_hello()
