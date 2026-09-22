from ...database import Database

HistorialFiltro = dict

ABONOS_QUERY = """SELECT
                       d.id AS donante_id,
                       d.nombre, d.apellido_paterno, d.apellido_materno,
                       a.monto, a.fecha_deposito, a.metodo
                   FROM Abonos a
                   JOIN Promesas p ON p.id = a.promesa_id
                   JOIN Donantes d ON d.id = p.donante_id
                  WHERE 1 = 1"""

LLAMADAS_QUERY = """SELECT
                         d.id AS donante_id,
                         d.nombre, d.apellido_paterno, d.apellido_materno,
                         l.resultado_llamado, l.nota, l.fecha_agendada
                     FROM Llamadas l
                     JOIN Promesas p ON p.id = l.promesa_id
                     JOIN Donantes d ON d.id = p.donante_id
                    WHERE l.fecha_agendada IS NOT NULL"""

PROMESAS_ACTIVAS_QUERY = """SELECT
                                 p.id AS promesa_id, p.donante_id,
                                 d.nombre, d.apellido_paterno, d.apellido_materno,
                                 p.monto_objetivo, p.fecha_inicio,
                                 p.numero_frequencia, p.tipo_frquencia,
                                 ultimo.fecha_deposito AS ultimo_abono_fecha
                             FROM Promesas p
                             JOIN Donantes d ON d.id = p.donante_id
                             OUTER APPLY (
                                 SELECT TOP 1 a.fecha_deposito
                                 FROM Abonos a
                                 WHERE a.promesa_id = p.id
                                 ORDER BY a.fecha_deposito DESC
                             ) ultimo
                            WHERE p.estado = 'activo'
                              AND p.numero_frequencia IS NOT NULL
                              AND p.tipo_frquencia IS NOT NULL
                              AND p.tipo_frquencia <> 'unica'"""


def _con_filtros(
    query: str, donante_id: int | None, q: str | None
) -> tuple[str, tuple]:
    params: list = []

    if donante_id is not None:
        query += " AND d.id = %s"
        params.append(donante_id)

    if q:
        query += """ AND (d.nombre LIKE %s
                       OR d.apellido_paterno LIKE %s
                       OR d.apellido_materno LIKE %s)"""
        comodin = f"%{q}%"
        params.extend([comodin, comodin, comodin])

    return query, tuple(params)


class HistorialRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def find_abonos(self, donante_id: int | None, q: str | None) -> list[dict]:
        query, params = _con_filtros(ABONOS_QUERY, donante_id, q)
        query += " ORDER BY a.fecha_deposito DESC;"
        return self._fetch(query, params)

    def find_llamadas(self, donante_id: int | None, q: str | None) -> list[dict]:
        query, params = _con_filtros(LLAMADAS_QUERY, donante_id, q)
        query += " ORDER BY l.fecha_agendada DESC;"
        return self._fetch(query, params)

    def find_promesas_activas(
        self, donante_id: int | None, q: str | None
    ) -> list[dict]:
        query, params = _con_filtros(PROMESAS_ACTIVAS_QUERY, donante_id, q)
        query += ";"
        return self._fetch(query, params)

    def _fetch(self, query: str, params: tuple) -> list[dict]:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(query, params)
                return cursor.fetchall()
            finally:
                cursor.close()
