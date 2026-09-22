"""NSE cash-market session validation.

Holiday dates are intentionally injected so production deployments can source an
official calendar rather than relying on hard-coded assumptions.
"""

from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo


class MarketSessionCalendar:
    def __init__(
        self,
        timezone_name: str = "Asia/Kolkata",
        open_time: time = time(9, 15),
        close_time: time = time(15, 30),
        holidays: set[date] | None = None,
    ) -> None:
        self.timezone = ZoneInfo(timezone_name)
        self.open_time = open_time
        self.close_time = close_time
        self.holidays = holidays or set()

    def localize(self, moment: datetime) -> datetime:
        if moment.tzinfo is None:
            raise ValueError("market-session checks require a timezone-aware datetime")
        return moment.astimezone(self.timezone)

    def is_trading_day(self, moment: datetime) -> bool:
        local = self.localize(moment)
        return local.weekday() < 5 and local.date() not in self.holidays

    def is_open(self, moment: datetime) -> bool:
        local = self.localize(moment)
        return self.is_trading_day(local) and self.open_time <= local.time() <= self.close_time

    def assert_open(self, moment: datetime) -> None:
        if not self.is_open(moment):
            raise RuntimeError("market session is closed")
