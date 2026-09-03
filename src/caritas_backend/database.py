
import logging
import queue
import threading
from collections.abc import Iterator
from contextlib import contextmanager

import pymssql

from .config import flag, get, required

MAX_CONNECTIONS = 10

log = logging.getLogger(__name__)


class Database:

    def __init__(self) -> None:
        self._idle: queue.LifoQueue = queue.LifoQueue()
        self._slots = threading.Semaphore(MAX_CONNECTIONS)

    def connect(self) -> None:
        with self.connection():
            pass

    @contextmanager
    def connection(self) -> Iterator[pymssql.Connection]:
        self._slots.acquire()
        connection = None
        try:
            connection = self._take()
            yield connection
        except Exception:
            close_quietly(connection)  
            connection = None
            raise
        finally:
            if connection is not None:
                self._idle.put(connection)
            self._slots.release()

    def close(self) -> None:
        while not self._idle.empty():
            close_quietly(self._idle.get_nowait())

    def _take(self) -> pymssql.Connection:
        try:
            return self._idle.get_nowait()
        except queue.Empty:
            return self._open()

    def _open(self) -> pymssql.Connection:
        settings = {
            "server": required("DB_HOST"),
            "port": get("DB_PORT", "1433"),
            "database": required("DB_NAME"),
            "user": required("DB_USER"),
            "password": required("DB_PASSWORD"),
            "encryption": "require" if flag("DB_ENCRYPT", True) else "off",
        }
        log.info("Conectando a %(server)s:%(port)s/%(database)s", settings)
        return pymssql.connect(**settings)


def close_quietly(connection: pymssql.Connection | None) -> None:
    try:
        if connection is not None:
            connection.close()
    except Exception:
        pass
