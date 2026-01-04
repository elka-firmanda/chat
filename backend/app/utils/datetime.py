"""
Timezone utilities for the backend.

Provides functions for timezone-aware datetime handling,
UTC conversion, and timezone context for agents.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo
import pytz


def get_current_utc() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def utc_now_isoformat() -> str:
    """Get current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def convert_to_timezone(dt: datetime, timezone_str: str) -> datetime:
    """
    Convert a datetime to a specific timezone.

    Args:
        dt: The datetime to convert (should be timezone-aware or UTC)
        timezone_str: Timezone string (e.g., 'America/New_York', 'UTC')

    Returns:
        Datetime in the specified timezone
    """
    if timezone_str == "UTC" or timezone_str == "auto":
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    try:
        tz = ZoneInfo(timezone_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(tz)
    except Exception:
        return dt


def format_in_timezone(
    dt: datetime,
    timezone_str: str,
    format_str: str = "%Y-%m-%d %H:%M:%S",
) -> str:
    """
    Format a datetime in a specific timezone.

    Args:
        dt: The datetime to format
        timezone_str: Timezone string
        format_str: Format string (default: YYYY-MM-DD HH:MM:SS)

    Returns:
        Formatted datetime string
    """
    local_dt = convert_to_timezone(dt, timezone_str)
    return local_dt.strftime(format_str)


def get_user_timezone_context(timezone_str: str) -> Dict[str, Any]:
    """
    Generate timezone context for agent system prompts.

    Args:
        timezone_str: The user's configured timezone

    Returns:
        Dictionary with timezone information for agents
    """
    if timezone_str == "auto":
        timezone_str = "UTC"

    try:
        tz = ZoneInfo(timezone_str)
        offset = datetime.now(tz).strftime("%z")
        current_time = format_in_timezone(datetime.now(timezone.utc), timezone_str)
        return {
            "timezone": timezone_str,
            "utc_offset": offset,
            "current_time": current_time,
            "formatted": f"{current_time} ({timezone_str}, UTC{offset})",
        }
    except Exception:
        return {
            "timezone": "UTC",
            "utc_offset": "+0000",
            "current_time": datetime.now(timezone.utc).isoformat(),
            "formatted": "UTC (+0000)",
        }


def get_common_timezones() -> list:
    """
    Get list of common timezones for UI selection.

    Returns:
        List of timezone info dicts with value, label, and offset
    """
    common_tz = [
        "UTC",
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Los_Angeles",
        "America/Anchorage",
        "Pacific/Honolulu",
        "Europe/London",
        "Europe/Paris",
        "Europe/Berlin",
        "Europe/Moscow",
        "Asia/Dubai",
        "Asia/Kolkata",
        "Asia/Bangkok",
        "Asia/Singapore",
        "Asia/Tokyo",
        "Asia/Shanghai",
        "Australia/Sydney",
        "Pacific/Auckland",
    ]

    timezones = []
    for tz_str in common_tz:
        try:
            tz = ZoneInfo(tz_str)
            now = datetime.now(tz)
            offset = now.strftime("%z")
            offset_formatted = f"UTC{offset[:3]}:{offset[3:]}"
            label = f"{tz_str.replace('_', ' ')} ({offset_formatted})"
            timezones.append({"value": tz_str, "label": label, "offset": offset})
        except Exception:
            pass

    timezones.sort(key=lambda x: x["label"])
    return timezones


def parse_iso_to_utc(iso_string: str) -> datetime:
    """
    Parse ISO format string to timezone-aware UTC datetime.

    Args:
        iso_string: ISO format datetime string

    Returns:
        UTC datetime
    """
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def datetime_to_utc(dt: datetime) -> datetime:
    """
    Ensure datetime is in UTC timezone.

    Args:
        dt: Input datetime

    Returns:
        UTC datetime
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_timezone_offset_hours(timezone_str: str) -> int:
    """
    Get the UTC offset in hours for a timezone.

    Args:
        timezone_str: Timezone string

    Returns:
        Offset in hours from UTC
    """
    if timezone_str == "UTC":
        return 0

    try:
        tz = ZoneInfo(timezone_str)
        now = datetime.now(tz)
        offset = now.utcoffset()
        if offset:
            return int(offset.total_seconds() / 3600)
    except Exception:
        pass

    return 0


# Aliases for compatibility
detect_timezone = get_common_timezones
format_datetime = format_in_timezone
