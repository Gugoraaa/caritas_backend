from datetime import datetime

from ...database import Database

CollectionRow = dict

# Una recoleccion es el cobro a domicilio de la cuota de una promesa.
FIND_QUERY = """SELECT
                    p.id AS promesa_id,
                    p.state,
                    p.monto_objetivo,
                    p.numero_frequencia,
                    d.id AS donor_id,
                    d.nombre,
                    d.apellido_paterno,
                    d.apellido_materno,
                    d.telefono,
                    d.calle,
                    d.numero_exterior,
                    d.numero_interior,
                    d.colonia,
                    d.municipio,
                    pagos.total_pagado,
                    hoy.id AS abono_hoy_id,
                    hoy.monto AS abono_hoy_monto,
                    hoy.fecha_deposito AS abono_hoy_fecha
                FROM Promesas p
                JOIN Donantes d ON d.id = p.donante_id
                OUTER APPLY (
                    SELECT SUM(a.monto) AS total_pagado
                    FROM Abonos a
                    WHERE a.promesa_id = p.id
                ) pagos
                OUTER APPLY (
                    SELECT TOP 1 a.id, a.monto, a.fecha_deposito
                    FROM Abonos a
                    WHERE a.promesa_id = p.id
                      AND a.fecha_deposito >= %s
                    ORDER BY a.fecha_deposito DESC
                ) hoy
               WHERE p.id = %s;"""

# Los id de Abonos no son IDENTITY: MAX(id) + 1 con UPDLOCK/HOLDLOCK para que
# dos inserts simultaneos no tomen el mismo id.
INSERT_ABONO_QUERY = """INSERT INTO Abonos (id, promesa_id, monto, fecha_deposito)
                        OUTPUT INSERTED.id
                        SELECT ISNULL(MAX(id), 0) + 1, %s, %s, %s
                          FROM Abonos WITH (UPDLOCK, HOLDLOCK);"""


class CollectionsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def find(self, promise_id: int, today: datetime) -> CollectionRow | None:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(FIND_QUERY, (today, promise_id))
                return cursor.fetchone()
            finally:
                cursor.close()

    def insert_abono(self, promise_id: int, amount, collected_at: datetime) -> int:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(INSERT_ABONO_QUERY, (promise_id, amount, collected_at))
                abono_id = cursor.fetchone()["id"]
                connection.commit()
                return abono_id
            finally:
                cursor.close()
