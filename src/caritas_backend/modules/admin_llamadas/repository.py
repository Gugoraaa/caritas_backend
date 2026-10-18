from ...database import Database

AdminCallRow = dict

# fecha_agendada es la cita, no la hora real de la llamada.
CALLS_QUERY = """SELECT
                     l.id AS call_id,
                     d.id AS donor_id,
                     CONCAT_WS(' ', d.nombre, d.apellido_paterno, d.apellido_materno)
                         AS donor_full_name,
                     p.responsable_id AS user_id,
                     u.name AS user_name,
                     l.resultado_llamado AS result,
                     l.estado AS call_status,
                     l.fecha_agendada AS scheduled_date
                 FROM Llamadas l
                 JOIN Promesas p ON p.id = l.promesa_id
                 JOIN Donantes d ON d.id = p.donante_id
                 LEFT JOIN Users u ON u.id = p.responsable_id
                 WHERE l.estado IN ('agendada', 'completada')"""


class AdminCallsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def find_calls(self, user_id: int | None) -> list[AdminCallRow]:
        query = CALLS_QUERY
        params: list = []

        if user_id is not None:
            query += " AND p.responsable_id = %s"
            params.append(user_id)

        query += " ORDER BY l.fecha_agendada DESC, l.id DESC;"
        return self._fetch_all(query, params)

    def _fetch_all(self, query: str, params: list) -> list[dict]:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(query, tuple(params))
                return cursor.fetchall()
            finally:
                cursor.close()
