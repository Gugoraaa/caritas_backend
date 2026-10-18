from datetime import datetime

from ...database import Database

CallRow = dict
CallOwnerRow = dict
CallResultRow = dict

QUERY = """SELECT
               d.id AS donor_id,
               d.nombre,
               d.apellido_paterno,
               d.apellido_materno,
               l.id AS call_id,
               l.estado AS call_status,
               l.fecha_agendada,
               ultimo.fecha_deposito AS latest_payment_date,
               ultimo.monto AS latest_payment_amount
           FROM Llamadas l
           JOIN Promesas p ON p.id = l.promesa_id
           JOIN Donantes d ON d.id = p.donante_id
           OUTER APPLY (
               SELECT TOP 1 a.fecha_deposito, a.monto
               FROM Abonos a
               WHERE a.promesa_id = p.id
               ORDER BY a.fecha_deposito DESC
           ) ultimo
          WHERE p.responsable_id = %s
            AND l.estado IN ('agendada', 'completada')
            AND l.fecha_agendada >= %s
            AND l.fecha_agendada < %s
          ORDER BY l.fecha_agendada;"""

OWNER_QUERY = """SELECT l.id AS call_id, p.responsable_id
                   FROM Llamadas l
                   JOIN Promesas p ON p.id = l.promesa_id
                  WHERE l.id = %s;"""

RESULT_QUERY = """SELECT
                      l.id AS call_id,
                      p.donante_id AS donor_id,
                      l.estado AS call_status,
                      l.fecha_agendada,
                      l.proposito,
                      l.resultado_llamado,
                      l.monto_comprometido
                  FROM Llamadas l
                  JOIN Promesas p ON p.id = l.promesa_id
                 WHERE l.id = %s;"""

# Columnas que el PATCH puede tocar. resultado_llamado es "text": SQL Server
# convierte solo el nvarchar que manda pymssql.
UPDATABLE = ("resultado_llamado", "estado", "proposito", "monto_comprometido")


class CallsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def find_scheduled_between(
        self, user_id: int, start: datetime, end: datetime
    ) -> list[CallRow]:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(QUERY, (user_id, start, end))
                return cursor.fetchall()
            finally:
                cursor.close()

    def find_owner(self, call_id: int) -> CallOwnerRow | None:
        return self._fetch_one(OWNER_QUERY, call_id)

    def find_result(self, call_id: int) -> CallResultRow | None:
        return self._fetch_one(RESULT_QUERY, call_id)

    def update(self, call_id: int, data: dict) -> int:
        columns = [column for column in UPDATABLE if column in data]
        assignments = ", ".join(f"{column} = %s" for column in columns)
        query = f"UPDATE Llamadas SET {assignments} WHERE id = %s;"
        params = [data[column] for column in columns] + [call_id]
        with self._database.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(query, tuple(params))
                connection.commit()
                return cursor.rowcount
            finally:
                cursor.close()

    def _fetch_one(self, query: str, call_id: int) -> dict | None:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(query, (call_id,))
                return cursor.fetchone()
            finally:
                cursor.close()
