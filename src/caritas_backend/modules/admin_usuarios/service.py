import logging

from ...database import Database
from ...errors import HttpException
from .repository import AdminUserRow, AdminUsersRepository

INTERNAL_ERROR = "Internal server error"

log = logging.getLogger(__name__)


class AdminUsersService:
    def __init__(self, database: Database) -> None:
        self.users = AdminUsersRepository(database)

    def list_users(self) -> list[dict]:
        try:
            rows = self.users.find_users()
        except Exception as error:
            log.exception("Failed to list users for admin")
            raise HttpException(500, INTERNAL_ERROR) from error
        return [to_public_user(row) for row in rows]


def to_public_user(row: AdminUserRow) -> dict:
    # No se inventa estado "Activa"/"En ruta": Users no tiene esa columna.
    return {
        "id": row["id"],
        "name": row["name"],
        "role": row["role"],
    }
