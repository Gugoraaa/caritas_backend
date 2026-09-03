"""Contrasenas y tokens."""

import secrets
import time

import bcrypt
import jwt

ALGORITHM = "HS256"
BCRYPT_COST = 10
UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}

ABSENT_USER_HASH = bcrypt.hashpw(
    secrets.token_hex(32).encode(), bcrypt.gensalt(BCRYPT_COST)
).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], password_hash.encode())
    except (ValueError, TypeError):
        return False


def parse_duration(value: str) -> int:
    if value[-1] in UNITS:
        return int(value[:-1]) * UNITS[value[-1]]
    return int(value)


def sign_token(payload: dict, secret: str, expires_in: int) -> str:
    issued_at = int(time.time())
    claims = {**payload, "iat": issued_at, "exp": issued_at + expires_in}
    return jwt.encode(claims, secret, algorithm=ALGORITHM)
