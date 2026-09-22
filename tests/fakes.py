"""Dobles de Database para tests que no tocan SQL Server."""

from contextlib import contextmanager


class FakeCursor:
    """Cursor que responde con filas distintas segun una palabra clave del query."""

    def __init__(self, rows_by_keyword: dict[str, list[dict]]) -> None:
        self._rows_by_keyword = rows_by_keyword
        self._rows: list[dict] = []
        self.executed: list[tuple[str, tuple]] = []

    def execute(self, query: str, params: tuple = ()) -> None:
        self.executed.append((query, params))
        for keyword, rows in self._rows_by_keyword.items():
            if keyword in query:
                self._rows = rows
                return
        self._rows = []

    def fetchall(self) -> list[dict]:
        return self._rows

    def fetchone(self) -> dict | None:
        return self._rows[0] if self._rows else None

    def close(self) -> None:
        pass


class FakeConnection:
    def __init__(self, rows_by_keyword: dict[str, list[dict]]) -> None:
        self._rows_by_keyword = rows_by_keyword

    def cursor(self, as_dict: bool = False) -> FakeCursor:
        return FakeCursor(self._rows_by_keyword)


class FakeDatabase:
    """Doble de Database: enruta cada query por una palabra clave del SQL."""

    def __init__(self, rows_by_keyword: dict[str, list[dict]]) -> None:
        self._connection = FakeConnection(rows_by_keyword)

    @contextmanager
    def connection(self):
        yield self._connection
