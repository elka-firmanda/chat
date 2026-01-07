"""DateTime service with timezone support."""

from datetime import datetime

import pytz
from dateutil import parser as date_parser


class DateTimeService:
    def __init__(self, timezone: str = "UTC"):
        self.set_timezone(timezone)

    def set_timezone(self, timezone: str) -> None:
        try:
            self.timezone = pytz.timezone(timezone)
            self.timezone_name = timezone
        except pytz.exceptions.UnknownTimeZoneError:
            self.timezone = pytz.UTC
            self.timezone_name = "UTC"

    def get_current_datetime(self) -> datetime:
        return datetime.now(self.timezone)

    def get_current_date(self) -> str:
        return self.get_current_datetime().strftime("%Y-%m-%d")

    def get_current_time(self) -> str:
        return self.get_current_datetime().strftime("%H:%M:%S")

    def get_context_string(self) -> str:
        now = self.get_current_datetime()
        return (
            f"Current date and time: {now.strftime('%A, %B %d, %Y at %I:%M %p %Z')}\n"
            f"Timezone: {self.timezone_name}\n"
            f"Unix timestamp: {int(now.timestamp())}"
        )

    def parse_datetime(self, datetime_string: str) -> datetime | None:
        try:
            dt = date_parser.parse(datetime_string)
            if dt.tzinfo is None:
                dt = self.timezone.localize(dt)
            return dt
        except Exception:
            return None

    @staticmethod
    def list_timezones() -> list[str]:
        return sorted(pytz.all_timezones)
