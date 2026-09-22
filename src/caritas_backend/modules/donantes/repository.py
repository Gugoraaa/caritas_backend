from ...database import Database

DonanteRow = dict

QUERY = """SELECT id, nombre, apellido_paterno, apellido_materno
           FROM Donantes
          ORDER BY nombre, apellido_paterno;"""


class DonantesRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def find_all(self) -> list[DonanteRow]:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(QUERY)
                return cursor.fetchall()
            finally:
                cursor.close()


def nombre_completo(row: dict) -> str:
    partes = [row["nombre"], row.get("apellido_paterno"), row.get("apellido_materno")]
    return " ".join(parte for parte in partes if parte)
