from ...database import Database
from .model import DonorRecord

# Selecting the donor the view is asking fo
QUERY = """
    SELECT
        id,
        nombre,
        apellido_paterno,
        appellido_materno,
        apodo,
        razon_social,
        curp,
        email,
        telefono,
        telefono_oficina,
        dia_nacimiento,
        fecha_creacion
    FROM Donantes,
    Where id = %s;
"""


class DonorRepository:

    def __init__(self, database: Database) -> None:
        self._database = database

    def find_by_id(self,donor_id: int) -> DonorRecord | None:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)

            try:
                cursor.execture(QUERY, (donor_id,))
                return cursor.fetchone()
            finally:
                cursor.close()



