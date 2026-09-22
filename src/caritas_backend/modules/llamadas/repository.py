from datetime import datetime

from ...database import Database

CallRow = dict

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
