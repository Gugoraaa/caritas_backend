import logging

from ...database import Database
from ...errors import HttpException
from .repository import AdminCallRow, AdminCallsRepository

INTERNAL_ERROR = "Internal server error"

log = logging.getLogger(__name__)


class AdminCallsService:
    def __init__(self, database: Database) -> None:
        self.calls = AdminCallsRepository(database)

    def list_calls(self, user_id: int | None = None) -> list[dict]:
        try:
            rows = self.calls.find_calls(user_id)
        except Exception as error:
            log.exception("Failed to list calls for admin")
            raise HttpException(500, INTERNAL_ERROR) from error
        return [to_public_call(row) for row in rows]


def to_public_call(row: AdminCallRow) -> dict:
    scheduled = row["scheduled_date"]
    return {
        "call_id": row["call_id"],
        "donor_id": row["donor_id"],
        "donor_full_name": row["donor_full_name"],
        "user_id": row["user_id"],
        "user_name": row["user_name"],
        "result": row["result"],
        "call_status": row["call_status"],
        "scheduled_date": scheduled.isoformat() if scheduled is not None else None,
    }
