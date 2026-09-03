
import os


def get(key: str, default: str) -> str:
    return os.environ.get(key) or default


def required(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"Falta la variable de entorno obligatoria {key}")
    return value


def flag(key: str, default: bool) -> bool:
    value = os.environ.get(key)
    return default if value is None else value == "true"
