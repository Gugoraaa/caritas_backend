from ...database import Database


class AdminResumenRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def _fetch(self, query: str, params: tuple = ()) -> list[dict]:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(query, params)
                return cursor.fetchall()
            finally:
                cursor.close()

    def donations(self, start, end) -> list[dict]:
        return self._fetch(
            "SELECT CAST(a.fecha_deposito AS date) AS day, SUM(a.monto) AS total "
            "FROM Abonos a WHERE a.fecha_deposito >= %s AND a.fecha_deposito < %s "
            "GROUP BY CAST(a.fecha_deposito AS date) ORDER BY day;",
            (start, end),
        )

    def outcomes(self) -> list[dict]:
        return self._fetch(
            "SELECT CONVERT(nvarchar(255), l.resultado_llamado) AS outcome, "
            "COUNT(*) AS call_count FROM Llamadas l WHERE l.estado = %s "
            "GROUP BY CONVERT(nvarchar(255), l.resultado_llamado) "
            "ORDER BY outcome;",
            ("completada",),
        )

    def calls_by_responsible(self) -> list[dict]:
        return self._fetch(
            "SELECT u.id AS user_id, u.name AS user_name, COUNT(*) AS call_count, "
            "COUNT(DISTINCT p.id) AS promise_count FROM Llamadas l "
            "JOIN Promesas p ON p.id = l.promesa_id "
            "JOIN Users u ON u.id = p.responsable_id "
            "WHERE l.estado = %s GROUP BY u.id, u.name ORDER BY u.name, u.id;",
            ("completada",),
        )

    def latest_donations(self) -> list[dict]:
        return self._fetch(
            "SELECT d.id AS donor_id, MAX(a.fecha_deposito) AS latest_donation "
            "FROM Donantes d LEFT JOIN Promesas p ON p.donante_id = d.id "
            "LEFT JOIN Abonos a ON a.promesa_id = p.id GROUP BY d.id;"
        )
