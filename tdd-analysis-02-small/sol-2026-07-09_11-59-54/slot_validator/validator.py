"""
Medical scheduling system appointment slot code validator.

Slot code format: {DAY}-{TIME}-{ROOM}-{CHECKSUM}
"""

from dataclasses import dataclass
from typing import Optional
import re


VALID_DAYS = {"MON", "TUE", "WED", "THU", "FRI"}
VALID_ROOM_PREFIXES = {"ER", "IC", "GP", "OT"}

# TIME boundaries in (HH, MM) tuples
TIME_MIN = (8, 0)
TIME_MAX = (17, 30)


@dataclass
class ValidationResult:
    """Structured result from slot code validation."""
    valid: bool
    error_field: Optional[str] = None
    error_reason: Optional[str] = None

    def __repr__(self) -> str:
        if self.valid:
            return "ValidationResult(valid=True)"
        return (
            f"ValidationResult(valid=False, "
            f"error_field={self.error_field!r}, "
            f"error_reason={self.error_reason!r})"
        )


def _alphabet_position(ch: str) -> int:
    """Return 1-based alphabet position of an uppercase letter."""
    return ord(ch.upper()) - ord('A') + 1


def _validate_format(code: str):
    """Split code into parts or return an error result."""
    parts = code.split("-")
    if len(parts) != 4:
        return None, ValidationResult(
            valid=False,
            error_field="format",
            error_reason=(
                f"Expected 4 dash-separated parts, got {len(parts)}: "
                f"format must be DAY-TIME-ROOM-CHECKSUM"
            ),
        )
    return parts, None


def _validate_day(day: str) -> Optional[ValidationResult]:
    if not re.fullmatch(r"[A-Z]{3}", day):
        return ValidationResult(
            valid=False,
            error_field="DAY",
            error_reason=f"DAY must be a 3-letter uppercase abbreviation, got {day!r}",
        )
    if day not in VALID_DAYS:
        return ValidationResult(
            valid=False,
            error_field="DAY",
            error_reason=(
                f"DAY {day!r} is not a valid weekday; "
                f"must be one of {sorted(VALID_DAYS)}"
            ),
        )
    return None


def _validate_time(time_str: str) -> Optional[ValidationResult]:
    if not re.fullmatch(r"\d{4}", time_str):
        return ValidationResult(
            valid=False,
            error_field="TIME",
            error_reason=f"TIME must be exactly 4 digits (HHMM), got {time_str!r}",
        )
    hh = int(time_str[:2])
    mm = int(time_str[2:])
    if hh > 23 or mm > 59:
        return ValidationResult(
            valid=False,
            error_field="TIME",
            error_reason=(
                f"TIME {time_str!r} is not a valid 24-hour clock value "
                f"(HH must be 00-23, MM must be 00-59)"
            ),
        )
    if mm not in (0, 30):
        return ValidationResult(
            valid=False,
            error_field="TIME",
            error_reason=(
                f"TIME {time_str!r} must be on the hour (:00) or "
                f"half-hour (:30), got minutes={mm}"
            ),
        )
    if (hh, mm) < TIME_MIN or (hh, mm) > TIME_MAX:
        return ValidationResult(
            valid=False,
            error_field="TIME",
            error_reason=(
                f"TIME {time_str!r} is outside the allowed range "
                f"08:00–17:30 inclusive"
            ),
        )
    return None


def _validate_room(room: str) -> Optional[ValidationResult]:
    m = re.fullmatch(r"([A-Z]{2})(\d{1,2})", room)
    if not m:
        return ValidationResult(
            valid=False,
            error_field="ROOM",
            error_reason=(
                f"ROOM must be 2 uppercase letters followed by 1-2 digits, "
                f"got {room!r}"
            ),
        )
    prefix = m.group(1)
    if prefix not in VALID_ROOM_PREFIXES:
        return ValidationResult(
            valid=False,
            error_field="ROOM",
            error_reason=(
                f"ROOM prefix {prefix!r} is not valid; "
                f"must be one of {sorted(VALID_ROOM_PREFIXES)}"
            ),
        )
    return None


def _validate_checksum(day: str, room: str, checksum_str: str) -> Optional[ValidationResult]:
    if not re.fullmatch(r"\d{2}", checksum_str):
        return ValidationResult(
            valid=False,
            error_field="CHECKSUM",
            error_reason=(
                f"CHECKSUM must be exactly 2 digits, got {checksum_str!r}"
            ),
        )
    # Sum of alphabet positions for DAY letters
    day_sum = sum(_alphabet_position(ch) for ch in day)
    # Room number digits (strip the 2-letter prefix)
    room_digits = int(re.search(r"\d+", room).group())
    expected = (day_sum + room_digits) % 100
    actual = int(checksum_str)
    if actual != expected:
        return ValidationResult(
            valid=False,
            error_field="CHECKSUM",
            error_reason=(
                f"CHECKSUM {actual:02d} is incorrect; "
                f"expected {expected:02d} "
                f"(DAY letter sum={day_sum}, room digits={room_digits}, "
                f"({day_sum}+{room_digits})%100={expected})"
            ),
        )
    return None


def validate_slot_code(code: str) -> ValidationResult:
    """
    Validate a medical scheduling appointment slot code.

    Parameters
    ----------
    code : str
        The slot code to validate, expected format: DAY-TIME-ROOM-CHECKSUM

    Returns
    -------
    ValidationResult
        .valid is True if all rules pass.
        Otherwise .valid is False with .error_field and .error_reason set.
    """
    if not isinstance(code, str):
        return ValidationResult(
            valid=False,
            error_field="format",
            error_reason=f"Slot code must be a string, got {type(code).__name__}",
        )

    parts, err = _validate_format(code)
    if err:
        return err

    day, time_str, room, checksum_str = parts

    err = _validate_day(day)
    if err:
        return err

    err = _validate_time(time_str)
    if err:
        return err

    err = _validate_room(room)
    if err:
        return err

    err = _validate_checksum(day, room, checksum_str)
    if err:
        return err

    return ValidationResult(valid=True)
