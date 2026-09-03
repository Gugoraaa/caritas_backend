
import logging
from http import HTTPStatus

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import HTTPException

log = logging.getLogger(__name__)


class HttpException(Exception):
    def __init__(self, status: int, message: str | list[str]):
        super().__init__(message)
        self.status = status
        self.message = message

    def body(self) -> dict:
        return {
            "message": self.message,
            "error": HTTPStatus(self.status).phrase,
            "statusCode": self.status,
        }


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HttpException)
    def handle_http(error: HttpException) -> tuple[Response, int]:
        return jsonify(error.body()), error.status

    @app.errorhandler(HTTPException)
    def handle_werkzeug(error: HTTPException) -> tuple[Response, int]:
        if error.code in (404, 405):
            url = request.full_path if request.query_string else request.path
            error = HttpException(404, f"Cannot {request.method} {url}")
        else:
            error = HttpException(error.code, error.description)
        return jsonify(error.body()), error.status

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception) -> tuple[Response, int]:
        log.exception("Error no manejado")
        return jsonify(HttpException(500, "Internal server error").body()), 500
