from datetime import datetime

from ...database import Database

LlamadaRow = dict

QUERY = """SELECT
               d.id AS donante_id,
               d.nombre,
               d.apellido_paterno,
               d.apellido_materno,
               l.id AS llamada_id,
               l.estado AS llamada_estado,
               l.fecha_agendada,
               ultimo.fecha_deposito AS ultimo_abono_fecha,
               ultimo.monto AS ultimo_abono_monto
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


class LlamadasRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def find_agendadas_entre(
        self, user_id: int, start: datetime, end: datetime
    ) -> list[LlamadaRow]:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(QUERY, (user_id, start, end))
                return cursor.fetchall()
            finally:
                cursor.close()
