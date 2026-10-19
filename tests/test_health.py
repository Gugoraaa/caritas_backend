from contextlib import contextmanager

from caritas_backend.modules.health.controller import (
    API_VERSION,
    DB_ERROR,
    DB_OK,
    check_database,
)


class FakeCursor:
    def execute(self, query):
        self.query = query

    def fetchone(self):
        return (1,)

    def close(self):
        pass


class FakeConnection:
    def cursor(self):
        return FakeCursor()


class FakeDatabase:
    def __init__(self, error=None):
        self.error = error

    @contextmanager
    def connection(self):
        if self.error:
            raise self.error
        yield FakeConnection()


def test_database_ok():
    assert check_database(FakeDatabase()) == DB_OK


def test_database_unreachable():
    assert check_database(FakeDatabase(error=RuntimeError("down"))) == DB_ERROR


def test_version_is_set():
    assert API_VERSION
