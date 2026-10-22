from datetime import datetime

from ...database import Database

CallRow = dict
CallOwnerRow = dict
CallResultRow = dict
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
            AND l.estado IN %s
            AND l.fecha_agendada >= %s
            AND l.fecha_agendada < %s
          ORDER BY l.fecha_agendada;"""

ACTIVE_PROMISES_QUERY = """SELECT id
                             FROM Promesas
                            WHERE responsable_id = %s
                              AND state = 'activo';"""

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
        self, user_id: int, start: datetime, end: datetime, statuses: tuple[str, ...]
    ) -> list[CallRow]:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                # pymssql expande la tupla de estados en la lista del IN.
                cursor.execute(QUERY, (user_id, statuses, start, end))
                return cursor.fetchall()
            finally:
                cursor.close()

    def find_active_promise_ids(self, user_id: int) -> list[int]:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(ACTIVE_PROMISES_QUERY, (user_id,))
                return [row["id"] for row in cursor.fetchall()]
            finally:
                cursor.close()

    def insert_calls(self, rows: list[dict]) -> None:
        with self._database.connection() as connection:
            cursor = connection.cursor()
            try:
                for row in rows:
                    cursor.execute(
                        INSERT_CALL_QUERY,
                        (
                            row["promesa_id"],
                            row["resultado_llamado"],
                            row["monto_comprometido"],
                            row["estado"],
                            row["proposito"],
                            row["fecha_agendada"],
                        ),
                    )
                connection.commit()
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
    ) -> bool:
        """Aplica todo en una sola transaccion; False si la llamada ya no estaba
        agendada. Si new_call no trae promesa_id, se liga a new_promise."""
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
                    return False

                promise_id = None
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
                    promise_id = cursor.fetchone()["id"]
                if new_call is not None:
                    cursor.execute(
                        INSERT_CALL_QUERY,
                        (
                            new_call["promesa_id"] or promise_id,
                            new_call["resultado_llamado"],
                            new_call["monto_comprometido"],
                            new_call["estado"],
                            new_call["proposito"],
                            new_call["fecha_agendada"],
                        ),
                    )

                connection.commit()
                return True
            finally:
                cursor.close()
