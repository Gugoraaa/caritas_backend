
import json
import re
from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import request

from .errors import HttpException

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.IGNORECASE)


def is_string(value: Any) -> bool:
    return isinstance(value, str)


def is_not_empty(value: Any) -> bool:
    return value is not None and value != ""


def is_email(value: Any) -> bool:
    return isinstance(value, str) and EMAIL.match(value) is not None


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def optional(predicate: Callable[[Any], bool]) -> Callable[[Any], bool]:
    return lambda value: value is None or predicate(value)


def read_body() -> Any:
    if request.mimetype == "application/x-www-form-urlencoded":
        return request.form.to_dict()
    if request.mimetype != "application/json":
        return {}
    try:
        return json.loads(request.get_data() or b"{}")
    except ValueError as error:
        raise HttpException(400, f"Body JSON invalido: {error}") from error


def check(rules: dict, body: Any) -> dict:
    if not isinstance(body, dict):
        body = {}

    errors = [
        f"{field} {message}"
        for field, checks in rules.items()
        for passes, message in checks
        if not passes(body.get(field))
    ]
    if errors:
        raise HttpException(400, errors)

    return {field: body[field] for field in rules if field in body}


def validate_body(rules: dict) -> Callable:

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return view(*args, body=check(rules, read_body()), **kwargs)

        return wrapper

    return decorator
