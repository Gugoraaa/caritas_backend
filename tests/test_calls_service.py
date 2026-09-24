from datetime import datetime
from zoneinfo import ZoneInfo

from caritas_backend.modules.llamadas.service import today_local

MONTERREY = ZoneInfo("America/Monterrey")


def test_today_local_returns_naive_local_midnight():
    now = datetime(2026, 9, 24, 23, 45, 12, tzinfo=MONTERREY)
    assert today_local(now) == datetime(2026, 9, 24, 0, 0, 0)


def test_today_local_flips_at_local_midnight_not_utc_midnight():
    # 00:30 del 25 en Monterrey = 06:30 UTC del 25: sigue siendo dia 25 local.
    now = datetime(2026, 9, 25, 0, 30, tzinfo=MONTERREY)
    assert today_local(now).day == 25

    # 17:59 del 24 en Monterrey = 23:59 UTC del 24: todavia es dia 24 local.
    now = datetime(2026, 9, 24, 17, 59, tzinfo=MONTERREY)
    assert today_local(now).day == 24


def test_today_local_defaults_to_current_time():
    result = today_local()
    assert result.hour == 0
    assert result.minute == 0
    assert result.tzinfo is None
