from ...database import Database
from .model import DonorRecord

QUERY = """
    SELECT
        d.id,
        d.nombre,
        d.apellido_paterno,
        d.apellido_materno,
        d.email,
        d.telefono,
        d.colonia,
        d.dia_nacimiento,
        d.fecha_creacion,
        ultimo_abono.fecha_deposito AS ultima_donacion_fecha,
        ultimo_abono.monto AS ultima_donacion_monto
    FROM Donantes AS d
    OUTER APPLY (
        SELECT TOP 1
            a.fecha_deposito,
            a.monto
        FROM Promesas AS p
        INNER JOIN Abonos AS a ON a.promesa_id = p.id
        WHERE p.donante_id = d.id
        ORDER BY a.fecha_deposito DESC, a.id DESC
    ) AS ultimo_abono
    WHERE d.id = %s;
"""


class DonorRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def find_by_id(self, donor_id: int) -> DonorRecord | None:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(QUERY, (donor_id,))
                return cursor.fetchone()
            finally:
                cursor.close()

