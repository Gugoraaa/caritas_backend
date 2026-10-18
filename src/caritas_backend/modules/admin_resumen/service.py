import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from ...database import Database
from ...errors import HttpException
from .repository import AdminResumenRepository

log = logging.getLogger(__name__)


class AdminResumenService:
    def __init__(self, database: Database) -> None:
        self.repository = AdminResumenRepository(database)

    def get_summary(self, now: datetime | None = None) -> dict:
        local_now = now or datetime.now(ZoneInfo("America/Monterrey"))
        if local_now.tzinfo is not None:
            local_now = local_now.astimezone(ZoneInfo("America/Monterrey"))
        first = date(local_now.year, local_now.month, 1)
        following = date(
            local_now.year + (local_now.month == 12), local_now.month % 12 + 1, 1
        )
        try:
            daily = self.repository.donations(first, following)
            outcomes = self.repository.outcomes()
            callers = self.repository.calls_by_responsible()
            latest = self.repository.latest_donations()
        except Exception as error:
            log.exception("Failed to fetch admin summary")
            raise HttpException(500, "Internal server error") from error

        daily_by_date = {as_date(row["day"]): row["total"] for row in daily}
        weeks = []
        cursor = first - timedelta(days=first.weekday())
        while cursor < following:
            week_end = cursor + timedelta(days=7)
            left, right = max(cursor, first), min(week_end, following)
            total = sum(
                (
                    amount
                    for day, amount in daily_by_date.items()
                    if left <= day < right
                ),
                start=Decimal("0.00"),
            )
            weeks.append(
                {
                    "start": left.isoformat(),
                    "end": (right - timedelta(days=1)).isoformat(),
                    "total": total,
                }
            )
            cursor = week_end

        today = local_now.date()
        risk = {"green": 0, "yellow": 0, "red": 0}
        for row in latest:
            donated = row["latest_donation"]
            days = (
                max((today - as_date(donated)).days, 0) if donated is not None else None
            )
            risk[
                "green"
                if days is not None and days < 30
                else "yellow"
                if days is not None and days < 60
                else "red"
            ] += 1
        return {
            "period": {
                "start": first.isoformat(),
                "end": (following - timedelta(days=1)).isoformat(),
            },
            "fundraising": {
                "total": sum(daily_by_date.values(), start=Decimal("0.00")),
                "weekly_totals": weeks,
            },
            "call_outcomes": outcomes,
            "calls_by_responsible": callers,
            "donor_risk": risk,
        }


def as_date(value):
    return value.date() if isinstance(value, datetime) else value
