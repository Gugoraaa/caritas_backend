from ...database import Database

AdminDonorRow = dict

# CONCAT_WS se salta los apellidos NULL. _CI_AI: ordena y busca sin mayusculas
# ni acentos ("maria" encuentra "María").
FULL_NAME = (
    "CONCAT_WS(' ', d.nombre, d.apellido_paterno, d.apellido_materno)"
    " COLLATE Latin1_General_CI_AI"
)

# Una fila por donante, sin N+1:
#   principal: la promesa activa mas reciente o, si no hay activa, la ultima
#              por fecha_inicio. De ahi sale la causa del donante.
#   ultimo:    el ultimo abono de cualquiera de sus promesas (fecha, monto y
#              metodo de pago); el riesgo se calcula en el servicio.
DONORS_QUERY = """SELECT
                      d.id,
                      d.nombre,
                      d.apellido_paterno,
                      d.apellido_materno,
                      d.colonia,
                      c.id AS causa_id,
                      c.titulo AS causa_titulo,
                      ultimo.fecha_deposito AS ultima_donacion_fecha,
                      ultimo.monto AS ultima_donacion_monto,
                      ultimo.metodo_pago
                  FROM Donantes d
                  OUTER APPLY (
                      SELECT TOP 1 p.caso_id
                      FROM Promesas p
                      WHERE p.donante_id = d.id
                      ORDER BY CASE WHEN p.state = 'activo' THEN 0 ELSE 1 END,
                               p.fecha_inicio DESC,
                               p.id DESC
                  ) principal
                  LEFT JOIN Causas c ON c.id = principal.caso_id
                  OUTER APPLY (
                      SELECT TOP 1 a.fecha_deposito, a.monto, a.metodo_pago
                      FROM Promesas p
                      JOIN Abonos a ON a.promesa_id = p.id
                      WHERE p.donante_id = d.id
                      ORDER BY a.fecha_deposito DESC, a.id DESC
                  ) ultimo
                 WHERE 1 = 1"""


class AdminRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def find_donors(
        self, search: str | None, causa_id: int | None, metodo: str | None
    ) -> list[AdminDonorRow]:
        query = DONORS_QUERY
        params: list = []

        if search:
            query += (
                f" AND ({FULL_NAME} LIKE %s"
                " OR d.colonia COLLATE Latin1_General_CI_AI LIKE %s)"
            )
            params += [f"%{search}%", f"%{search}%"]
        if causa_id is not None:
            query += " AND c.id = %s"
            params.append(causa_id)
        if metodo:
            query += " AND ultimo.metodo_pago = %s"
            params.append(metodo)

        query += f" ORDER BY {FULL_NAME}, d.id;"
        return self._fetch_all(query, params)

    def _fetch_all(self, query: str, params: list) -> list[dict]:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(query, tuple(params))
                return cursor.fetchall()
            finally:
                cursor.close()
