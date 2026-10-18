from ...database import Database
from .model import CausaRecord

FIELDS = (
    "titulo",
    "descripcion",
    "monto_objetivo",
    "beneficiario",
    "responsable",
    "lugar",
    "fecha_fin",
)

# Lo recaudado sale de los abonos de las promesas de cada causa, en la misma
# query para no hacer una consulta por causa. ISNULL conserva el decimal(38,2)
# de SUM, asi que una causa sin abonos devuelve 0.00.
SELECT_WITH_RAISED = """SELECT c.*, ISNULL(recaudado.total, 0) AS monto_recaudado
                          FROM Causas c
                          OUTER APPLY (
                              SELECT SUM(a.monto) AS total
                              FROM Promesas p
                              JOIN Abonos a ON a.promesa_id = p.id
                              WHERE p.caso_id = c.id
                          ) recaudado"""


class CausaRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def find_all(self) -> list[CausaRecord]:
        return self._fetch_all(f"{SELECT_WITH_RAISED} ORDER BY c.id;", [])

    def find_by_id(self, causa_id: int) -> CausaRecord | None:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(f"{SELECT_WITH_RAISED} WHERE c.id = %s;", (causa_id,))
                return cursor.fetchone()
            finally:
                cursor.close()

    def insert(self, data: dict) -> int:
        columns = [field for field in FIELDS if field in data]
        placeholders = ", ".join("%s" for _ in columns)
        query = (
            f"INSERT INTO Causas ({', '.join(columns)}) "
            f"OUTPUT INSERTED.id VALUES ({placeholders});"
        )
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(query, tuple(data[column] for column in columns))
                new_id = cursor.fetchone()["id"]
                connection.commit()
                return new_id
            finally:
                cursor.close()

    def update(self, causa_id: int, data: dict) -> int:
        columns = [field for field in FIELDS if field in data]
        assignments = ", ".join(f"{column} = %s" for column in columns)
        query = f"UPDATE Causas SET {assignments} WHERE id = %s;"
        params = [data[column] for column in columns] + [causa_id]
        with self._database.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(query, tuple(params))
                connection.commit()
                return cursor.rowcount
            finally:
                cursor.close()

    def delete(self, causa_id: int) -> int:
        with self._database.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute("DELETE FROM Causas WHERE id = %s;", (causa_id,))
                connection.commit()
                return cursor.rowcount
            finally:
                cursor.close()

    def _fetch_all(self, query: str, params: list) -> list[dict]:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(query, tuple(params))
                return cursor.fetchall()
            finally:
                cursor.close()
