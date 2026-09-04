from flask import Blueprint

from .service import get_hello

blueprint = Blueprint("app", __name__)


@blueprint.get("/")
def root() -> str:
    return get_hello()
