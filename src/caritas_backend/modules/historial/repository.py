from ...database import Database

CallHistoryRow = dict
DonationRow = dict
PromiseRow = dict
DonorOptionRow = dict

CALLS_QUERY = """SELECT
                     d.id AS donor_id,
                     d.nombre,
                     d.apellido_paterno,
                     d.apellido_materno,
                     l.id AS call_id,
                     l.estado AS call_status,
                     l.proposito,
                     l.resultado_llamado,
                     l.monto_comprometido,
                     l.fecha_agendada
                 FROM Llamadas l
                 JOIN Promesas p ON p.id = l.promesa_id
                 JOIN Donantes d ON d.id = p.donante_id
                WHERE p.responsable_id = %s"""

DONATIONS_QUERY = """SELECT
                         d.id AS donor_id,
                         d.nombre,
                         d.apellido_paterno,
                         d.apellido_materno,
                         a.id AS donation_id,
                         a.promesa_id,
                         a.monto,
                         a.fecha_deposito
                     FROM Abonos a
                     JOIN Promesas p ON p.id = a.promesa_id
                     JOIN Donantes d ON d.id = p.donante_id
                    WHERE p.responsable_id = %s"""

ACTIVE_PROMISES_QUERY = """SELECT
                               d.id AS donor_id,
                               d.nombre,
                               d.apellido_paterno,
                               d.apellido_materno,
                               p.id AS promesa_id,
                               p.monto_objetivo,
                               p.fecha_inicio,
                               p.numero_frequencia,
                               p.tipo_frquencia,
                               pagos.ultimo_pago,
                               pagos.total_pagado
                           FROM Promesas p
                           JOIN Donantes d ON d.id = p.donante_id
                           OUTER APPLY (
                               SELECT MAX(a.fecha_deposito) AS ultimo_pago,
                                      SUM(a.monto) AS total_pagado
                               FROM Abonos a
                               WHERE a.promesa_id = p.id
                           ) pagos
                          WHERE p.responsable_id = %s
                            AND p.estado = 'activo'
                            AND p.numero_frequencia > 0
                            AND p.tipo_frquencia IS NOT NULL
                            AND p.tipo_frquencia <> 'unica'"""

DONORS_QUERY = """SELECT DISTINCT
                      d.id AS donor_id,
                      d.nombre,
                      d.apellido_paterno,
                      d.apellido_materno
                  FROM Promesas p
                  JOIN Donantes d ON d.id = p.donante_id
                 WHERE p.responsable_id = %s
                 ORDER BY d.nombre, d.apellido_paterno;"""

# _CI_AI: la busqueda ignora mayusculas y acentos ("maria" encuentra "María").
FULL_NAME = (
    "CONCAT(d.nombre, ' ', d.apellido_paterno, ' ', d.apellido_materno)"
    " COLLATE Latin1_General_CI_AI"
)


def with_filters(
    query: str, user_id: int, donor_id: int | None, search: str | None
) -> tuple[str, list]:
    params: list = [user_id]

    if donor_id is not None:
        query += " AND d.id = %s"
        params.append(donor_id)
    if search:
        query += f" AND {FULL_NAME} LIKE %s"
        params.append(f"%{search}%")

    return query, params


class HistoryRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def find_calls(
        self, user_id: int, donor_id: int | None, search: str | None
    ) -> list[CallHistoryRow]:
        query, params = with_filters(CALLS_QUERY, user_id, donor_id, search)
        query += " ORDER BY l.fecha_agendada DESC, l.id DESC;"
        return self._fetch_all(query, params)

    def find_donations(
        self, user_id: int, donor_id: int | None, search: str | None
    ) -> list[DonationRow]:
        query, params = with_filters(DONATIONS_QUERY, user_id, donor_id, search)
        query += " ORDER BY a.fecha_deposito DESC, a.id DESC;"
        return self._fetch_all(query, params)

    def find_active_promises(
        self, user_id: int, donor_id: int | None, search: str | None
    ) -> list[PromiseRow]:
        query, params = with_filters(ACTIVE_PROMISES_QUERY, user_id, donor_id, search)
        return self._fetch_all(query + ";", params)

    def find_donors(self, user_id: int) -> list[DonorOptionRow]:
        return self._fetch_all(DONORS_QUERY, [user_id])

    def _fetch_all(self, query: str, params: list) -> list[dict]:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(query, tuple(params))
                return cursor.fetchall()
            finally:
                cursor.close()
