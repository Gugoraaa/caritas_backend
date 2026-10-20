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
        return {
            "period": {
                "start": first.isoformat(),
                "end": (following - timedelta(days=1)).isoformat(),
            },
            "fundraising": {
                "total": sum(daily_by_date.values(), start=Decimal("0.00")),
                "weekly_totals": _weekly_totals(daily_by_date, first, following),
            },
            "call_outcomes": outcomes,
            "completed_calls_total": sum(row["call_count"] for row in outcomes),
            "calls_by_responsible": callers,
            "donor_risk": _donor_risk(latest, local_now.date()),
        }


def _weekly_totals(daily_by_date, first, following):
    weeks = []
    start = first
    while start < following:
        end = min(start + timedelta(days=7 - start.weekday()), following)
        total = sum(
            (amount for day, amount in daily_by_date.items() if start <= day < end),
            start=Decimal("0.00"),
        )
        weeks.append(
            {
                "start": start.isoformat(),
                "end": (end - timedelta(days=1)).isoformat(),
                "total": total,
            }
        )
        start = end
    return weeks


def _donor_risk(latest, today):
    risk = {"green": 0, "yellow": 0, "red": 0}
    for row in latest:
        donated = row["latest_donation"]
        if donated is None:
            color = "red"
        else:
            days = max((today - as_date(donated)).days, 0)
            if days < 30:
                color = "green"
            elif days < 60:
                color = "yellow"
            else:
                color = "red"
        risk[color] += 1
    return risk


def as_date(value):
    return value.date() if isinstance(value, datetime) else value
