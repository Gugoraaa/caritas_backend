from datetime import datetime

from ...database import Database

CallRow = dict
CallDetailRow = dict

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

FIND_CALL_QUERY = """SELECT
                         l.id,
                         l.promesa_id,
                         l.estado,
                         l.monto_comprometido,
                         l.proposito,
                         p.donante_id,
                         p.caso_id
                     FROM Llamadas l
                     JOIN Promesas p ON p.id = l.promesa_id
                    WHERE l.id = %s;"""

# El filtro por estado evita registrar dos veces la misma llamada si llegan
# dos peticiones al mismo tiempo.
UPDATE_CALL_QUERY = """UPDATE Llamadas
                          SET resultado_llamado = %s,
                              notas_llamada = %s,
                              estado = %s,
                              monto_comprometido = COALESCE(%s, monto_comprometido),
                              fecha_agendada = COALESCE(%s, fecha_agendada)
                        WHERE id = %s
                          AND estado = 'agendada';"""

# Los id de Llamadas y Promesas no son IDENTITY: se asigna MAX(id) + 1 con
# UPDLOCK/HOLDLOCK para que dos inserts simultaneos no tomen el mismo id.
INSERT_CALL_QUERY = """INSERT INTO Llamadas
                           (id, promesa_id, resultado_llamado, monto_comprometido,
                            estado, proposito, fecha_agendada)
                       OUTPUT INSERTED.id
                       SELECT ISNULL(MAX(id), 0) + 1, %s, %s, %s, %s, %s, %s
                         FROM Llamadas WITH (UPDLOCK, HOLDLOCK);"""

INSERT_PROMISE_QUERY = """INSERT INTO Promesas
                              (id, donante_id, caso_id, responsable_id,
                               monto_objetivo, state, fecha_inicio,
                               numero_frequencia, tipo_frquencia)
                          OUTPUT INSERTED.id
                          SELECT ISNULL(MAX(id), 0) + 1, %s, %s, %s, %s, %s, %s, %s, %s
                            FROM Promesas WITH (UPDLOCK, HOLDLOCK);"""


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

    def find_call(self, call_id: int) -> CallDetailRow | None:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(FIND_CALL_QUERY, (call_id,))
                return cursor.fetchone()
            finally:
                cursor.close()

    def register_result(
        self,
        call_id: int,
        update: dict,
        new_call: dict | None,
        new_promise: dict | None,
    ) -> dict | None:
        """Aplica todo en una sola transaccion; None si la llamada ya no estaba
        agendada."""
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(
                    UPDATE_CALL_QUERY,
                    (
                        update["resultado_llamado"],
                        update["notas_llamada"],
                        update["estado"],
                        update["monto_comprometido"],
                        update["fecha_agendada"],
                        call_id,
                    ),
                )
                if cursor.rowcount == 0:
                    connection.rollback()
                    return None

                saved = {"nueva_llamada_id": None, "promesa_id": None}
                if new_call is not None:
                    cursor.execute(
                        INSERT_CALL_QUERY,
                        (
                            new_call["promesa_id"],
                            new_call["resultado_llamado"],
                            new_call["monto_comprometido"],
                            new_call["estado"],
                            new_call["proposito"],
                            new_call["fecha_agendada"],
                        ),
                    )
                    saved["nueva_llamada_id"] = cursor.fetchone()["id"]
                if new_promise is not None:
                    cursor.execute(
                        INSERT_PROMISE_QUERY,
                        (
                            new_promise["donante_id"],
                            new_promise["caso_id"],
                            new_promise["responsable_id"],
                            new_promise["monto_objetivo"],
                            new_promise["state"],
                            new_promise["fecha_inicio"],
                            new_promise["numero_frequencia"],
                            new_promise["tipo_frquencia"],
                        ),
                    )
                    saved["promesa_id"] = cursor.fetchone()["id"]

                connection.commit()
                return saved
            finally:
                cursor.close()
