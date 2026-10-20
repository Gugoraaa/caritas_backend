"""Lectura del JWT que llega en "Authorization: Bearer <token>"."""

from collections.abc import Callable
from functools import wraps
from typing import Any

import jwt
from flask import current_app, request

from ...errors import HttpException

INVALID_TOKEN = "Token inválido o expirado"
MISSING_TOKEN = "Token requerido"
ADMIN_REQUIRED = "Admin role required"
ROLE_REQUIRED = "Your role cannot use this endpoint"

ADMIN_ROLE = "admin"
TELEMARKETING_ROLE = "telemarketing"
COURIER_ROLE = "repartidor"

AuthUser = dict


def optional_user() -> AuthUser | None:
    """Sin header devuelve None; con un header que no sirve corta con 401."""
    header = request.headers.get("Authorization", "").strip()
    if not header:
        return None

    scheme, _, token = header.partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        raise HttpException(401, INVALID_TOKEN)

    try:
        claims = current_app.extensions["auth"].verify(token)
    except jwt.InvalidTokenError as error:
        raise HttpException(401, INVALID_TOKEN) from error

    user_id = claims.get("userId")
    if not isinstance(user_id, int) or isinstance(user_id, bool):
        raise HttpException(401, INVALID_TOKEN)

    return {"userId": user_id, "role": claims.get("role")}


def require_auth(view: Callable) -> Callable:
    """Exige un token valido y lo pasa a la vista como `user`."""

    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        user = optional_user()
        if user is None:
            raise HttpException(401, MISSING_TOKEN)
        return view(*args, user=user, **kwargs)

    return wrapper


def is_admin(role: object) -> bool:
    """En Users conviven 'admin' y 'Admin': se compara sin mayusculas."""
    return isinstance(role, str) and role.strip().lower() == ADMIN_ROLE


def require_admin(view: Callable) -> Callable:
    """Como require_auth, pero ademas exige role admin (si no, 403).

    El rol se lee de Users y no del token: un token firmado antes de un cambio
    de rol seguiria diciendo "admin" hasta que expire.
    """

    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        user = optional_user()
        if user is None:
            raise HttpException(401, MISSING_TOKEN)

        role = current_app.extensions["auth"].current_role(user["userId"])
        if role is None:
            raise HttpException(401, INVALID_TOKEN)
        if not is_admin(role):
            raise HttpException(403, ADMIN_REQUIRED)
        return view(*args, user={**user, "role": role}, **kwargs)

    return wrapper


def require_role(*roles: str) -> Callable[[Callable], Callable]:
    """Como require_auth, pero exige uno de `roles` (si no, 403). Admin siempre pasa.

    Igual que require_admin, el rol se lee de Users y no del token.
    """
    allowed = {role.lower() for role in roles} | {ADMIN_ROLE}

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = optional_user()
            if user is None:
                raise HttpException(401, MISSING_TOKEN)

            role = current_app.extensions["auth"].current_role(user["userId"])
            if role is None:
                raise HttpException(401, INVALID_TOKEN)
            if role.strip().lower() not in allowed:
                raise HttpException(403, ROLE_REQUIRED)
            return view(*args, user={**user, "role": role}, **kwargs)

        return wrapper

    return decorator


def user_id_from_token_or_query() -> int:
    """El userId del token si hay uno; si no, el query param user_id."""
    user = optional_user()
    if user is not None:
        return user["userId"]

    raw = request.args.get("user_id")
    if not raw or not raw.isdigit():
        raise HttpException(400, "user_id must be an integer")
    return int(raw)
