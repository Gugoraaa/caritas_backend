"""Rate limit en memoria por IP, con ventana deslizante.

Cada worker de gunicorn tiene su propio contador: con WEB_CONCURRENCY=4 el
limite efectivo puede llegar a 4 veces el configurado. Para esta carga alcanza;
si hiciera falta exactitud habria que mover los contadores a Redis.
"""

import math
import threading
import time
from collections import deque
from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import Flask, current_app, request

from .config import get
from .errors import HttpException
from .security import parse_duration

TOO_MANY_REQUESTS = "Demasiadas solicitudes, intenta más tarde"
# Pasado este numero de IPs distintas se descartan las que ya no tienen intentos
# dentro de la ventana, para que la memoria no crezca sin limite.
MAX_KEYS = 10_000


class RateLimiter:
    def __init__(
        self, limit: int, window: int, clock: Callable[[], float] = time.monotonic
    ):
        self.limit = limit
        self.window = window
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> float | None:
        """Registra un intento. Devuelve None si pasa, o los segundos a esperar."""
        now = self._clock()
        with self._lock:
            if len(self._hits) > MAX_KEYS:
                self._purge(now)

            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - self.window:
                hits.popleft()

            if len(hits) >= self.limit:
                return hits[0] + self.window - now
            hits.append(now)
            return None

    def _purge(self, now: float) -> None:
        cutoff = now - self.window
        stale = [key for key, hits in self._hits.items() if hits[-1] <= cutoff]
        for key in stale:
            del self._hits[key]


def parse_rate(value: str) -> RateLimiter:
    """Convierte "5/1m" en un limiter de 5 intentos por minuto."""
    limit, _, window = value.partition("/")
    return RateLimiter(int(limit), parse_duration(window))


def check(limiter: RateLimiter) -> None:
    retry_after = limiter.hit(request.remote_addr or "unknown")
    if retry_after is not None:
        raise HttpException(
            429,
            TOO_MANY_REQUESTS,
            headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
        )


def rate_limited(name: str) -> Callable:
    """Aplica a la vista el limiter guardado en app.extensions[name]."""

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            check(current_app.extensions[name])
            return view(*args, **kwargs)

        return wrapper

    return decorator


def register_rate_limit(app: Flask) -> None:
    """Limite global por IP para toda la API y uno mas estricto para el login."""
    global_limiter = parse_rate(get("RATE_LIMIT", "300/1m"))
    app.extensions["login_limiter"] = parse_rate(get("LOGIN_RATE_LIMIT", "5/1m"))

    @app.before_request
    def limit_all_requests() -> None:
        check(global_limiter)
