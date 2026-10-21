from datetime import datetime
from decimal import Decimal

from ...database import Database

CollectionRow = dict

LIST_QUERY = """SELECT
                    r.id,
                    r.promesa_id,
                    r.recolector_id,
                    r.fecha_programada,
                    r.ventana_inicio,
                    r.ventana_fin,
                    r.monto,
                    r.notas_domicilio,
                    r.estado,
                    r.motivo,
                    r.fecha_resultado,
                    r.abono_id,
                    d.id AS donor_id,
                    d.nombre,
                    d.apellido_paterno,
                    d.apellido_materno,
                    d.telefono,
                    d.calle,
                    d.numero_exterior,
                    d.numero_interior,
                    d.colonia,
                    d.municipio
                FROM Recolecciones r
                JOIN Promesas p ON p.id = r.promesa_id
                JOIN Donantes d ON d.id = p.donante_id
               WHERE 1 = 1"""

FIND_QUERY = LIST_QUERY + " AND r.id = %s;"

# Historial del recolector: solo las ya resueltas (las pendientes no se han
# hecho). El monto recolectado sale del abono; sin abono no se recolecto nada.
HISTORY_QUERY = """SELECT
                       r.id,
                       r.estado,
                       r.updated_at,
                       ISNULL(a.monto, 0) AS monto_recolectado,
                       d.nombre,
                       d.apellido_paterno,
                       d.apellido_materno
                   FROM Recolecciones r
                   JOIN Promesas p ON p.id = r.promesa_id
                   JOIN Donantes d ON d.id = p.donante_id
                   LEFT JOIN Abonos a ON a.id = r.abono_id
                  WHERE r.recolector_id = %s
                    AND r.estado <> 'pendiente'"""

# El filtro por estado evita confirmar o cerrar dos veces la misma recoleccion
# si llegan dos peticiones al mismo tiempo.
CONFIRM_QUERY = """UPDATE Recolecciones
                      SET estado = 'confirmada',
                          fecha_resultado = %s,
                          recolector_id = COALESCE(recolector_id, %s)
                    WHERE id = %s
                      AND estado = 'pendiente';"""

# Los id de Abonos no son IDENTITY: MAX(id) + 1 con UPDLOCK/HOLDLOCK para que
# dos inserts simultaneos no tomen el mismo id.
INSERT_ABONO_QUERY = """INSERT INTO Abonos
                            (id, promesa_id, monto, fecha_deposito, metodo_pago)
                        OUTPUT INSERTED.id
                        SELECT ISNULL(MAX(id), 0) + 1, %s, %s, %s, N'efectivo'
                          FROM Abonos WITH (UPDLOCK, HOLDLOCK);"""

LINK_ABONO_QUERY = """UPDATE Recolecciones SET abono_id = %s WHERE id = %s;"""

NOT_COLLECTED_QUERY = """UPDATE Recolecciones
                            SET estado = 'no_recolectada',
                                motivo = %s,
                                fecha_resultado = %s,
                                recolector_id = COALESCE(recolector_id, %s)
                          WHERE id = %s
                            AND estado = 'pendiente';"""

PROMISE_EXISTS_QUERY = """SELECT id FROM Promesas WHERE id = %s;"""

INSERT_QUERY = """INSERT INTO Recolecciones
                      (promesa_id, recolector_id, fecha_programada, ventana_inicio,
                       ventana_fin, monto, notas_domicilio)
                  OUTPUT INSERTED.id
                  VALUES (%s, %s, %s, %s, %s, %s, %s);"""

DELETE_QUERY = """DELETE FROM Recolecciones WHERE id = %s AND estado = 'pendiente';"""

# Nombres de columna fijos (nunca del cliente): solo cambian los valores.
UPDATABLE_COLUMNS = (
    "recolector_id",
    "fecha_programada",
    "ventana_inicio",
    "ventana_fin",
    "monto",
    "notas_domicilio",
)


class CollectionsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def find(self, collection_id: int) -> CollectionRow | None:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(FIND_QUERY, (collection_id,))
                return cursor.fetchone()
            finally:
                cursor.close()

    def find_all(
        self,
        status: str | None,
        collector_id: int | None,
        since: datetime | None,
        until: datetime | None,
    ) -> list[CollectionRow]:
        """Rango [since, until) sobre fecha_programada; None omite el filtro."""
        query = LIST_QUERY
        params: list = []
        if status is not None:
            query += " AND r.estado = %s"
            params.append(status)
        if collector_id is not None:
            query += " AND r.recolector_id = %s"
            params.append(collector_id)
        if since is not None:
            query += " AND r.fecha_programada >= %s"
            params.append(since)
        if until is not None:
            query += " AND r.fecha_programada < %s"
            params.append(until)
        query += " ORDER BY r.fecha_programada DESC, r.id DESC;"

        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(query, tuple(params))
                return cursor.fetchall()
            finally:
                cursor.close()

    def find_history(
        self, user_id: int, since: datetime | None, until: datetime | None
    ) -> list[CollectionRow]:
        """Rango [since, until) sobre updated_at; None deja ese lado abierto."""
        query = HISTORY_QUERY
        params: list = [user_id]
        if since is not None:
            query += " AND r.updated_at >= %s"
            params.append(since)
        if until is not None:
            query += " AND r.updated_at < %s"
            params.append(until)
        query += " ORDER BY r.updated_at DESC, r.id DESC;"

        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(query, tuple(params))
                return cursor.fetchall()
            finally:
                cursor.close()

    def confirm(
        self,
        collection_id: int,
        promise_id: int,
        amount: Decimal,
        collected_at: datetime,
        user_id: int,
    ) -> int | None:
        """Marca la recoleccion y crea su abono en una sola transaccion.

        Regresa el id del abono, o None si la recoleccion ya no estaba pendiente.
        """
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(CONFIRM_QUERY, (collected_at, user_id, collection_id))
                if cursor.rowcount == 0:
                    connection.rollback()
                    return None

                cursor.execute(INSERT_ABONO_QUERY, (promise_id, amount, collected_at))
                abono_id = cursor.fetchone()["id"]
                cursor.execute(LINK_ABONO_QUERY, (abono_id, collection_id))

                connection.commit()
                return abono_id
            finally:
                cursor.close()

    def mark_not_collected(
        self, collection_id: int, reason: str, resolved_at: datetime, user_id: int
    ) -> bool:
        """False si la recoleccion ya no estaba pendiente."""
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(
                    NOT_COLLECTED_QUERY, (reason, resolved_at, user_id, collection_id)
                )
                updated = cursor.rowcount > 0
                connection.commit()
                return updated
            finally:
                cursor.close()

    def promise_exists(self, promise_id: int) -> bool:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(PROMISE_EXISTS_QUERY, (promise_id,))
                return cursor.fetchone() is not None
            finally:
                cursor.close()

    def insert(self, values: tuple) -> int:
        """values en el orden de INSERT_QUERY; regresa el id nuevo."""
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(INSERT_QUERY, values)
                new_id = cursor.fetchone()["id"]
                connection.commit()
                return new_id
            finally:
                cursor.close()

    def update_pending(self, collection_id: int, fields: dict) -> bool:
        """fields: columna -> valor (solo UPDATABLE_COLUMNS). False si ya no estaba pendiente."""
        # Los nombres de columna van al SQL tal cual: esta lista blanca es lo que
        # evita la inyeccion. No usar assert, que python -O lo elimina.
        unknown = fields.keys() - set(UPDATABLE_COLUMNS)
        if unknown:
            raise ValueError(f"Columnas no actualizables: {sorted(unknown)}")
        assignments = ", ".join(f"{column} = %s" for column in fields)
        query = f"UPDATE Recolecciones SET {assignments} WHERE id = %s AND estado = 'pendiente';"
        return self._write(query, (*fields.values(), collection_id))

    def delete_pending(self, collection_id: int) -> bool:
        """False si ya no estaba pendiente."""
        return self._write(DELETE_QUERY, (collection_id,))

    def _write(self, query: str, params: tuple) -> bool:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(query, params)
                changed = cursor.rowcount > 0
                connection.commit()
                return changed
            finally:
                cursor.close()
