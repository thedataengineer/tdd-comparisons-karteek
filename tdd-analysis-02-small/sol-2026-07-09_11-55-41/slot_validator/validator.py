"""
Medical scheduling appointment slot code validator.

Slot code format: {DAY}-{TIME}-{ROOM}-{CHECKSUM}

Rules:
  DAY      : MON | TUE | WED | THU | FRI
  TIME     : HHMM, 24-hour, on the hour or half-hour, 08:00–17:30 inclusive
  ROOM     : one of (ER, IC, GP, OT) followed by 1–2 digits
  CHECKSUM : (sum of alphabet positions of DAY letters + room number) % 100
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_DAYS = {"MON", "TUE", "WED", "THU", "FRI"}
VALID_ROOM_PREFIXES = {"ER", "IC", "GP", "OT"}

# Pre-compiled patterns for each component
_DAY_RE = re.compile(r"^[A-Z]{3}$")
_TIME_RE = re.compile(r"^\d{4}$")
_ROOM_RE = re.compile(r"^([A-Z]{2})(\d{1,2})$")
_CHECKSUM_RE = re.compile(r"^\d{2}$")

# Valid (HH, MM) pairs within 08:00–17:30
_MIN_TIME = (8, 0)
_MAX_TIME = (17, 30)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Result of a slot code validation."""

    valid: bool
    error_field: Optional[str] = None   # "format" | "day" | "time" | "room" | "checksum"
    error_reason: Optional[str] = None

    def __repr__(self) -> str:
        if self.valid:
            return "ValidationResult(valid=True)"
        return (
            f"ValidationResult(valid=False, "
            f"error_field={self.error_field!r}, "
            f"error_reason={self.error_reason!r})"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _letter_position(ch: str) -> int:
    """Return 1-based alphabet position of an uppercase letter."""
    return ord(ch) - ord("A") + 1


def _day_letter_sum(day: str) -> int:
    """Sum the alphabet positions of each letter in *day*."""
    return sum(_letter_position(ch) for ch in day)


def _compute_checksum(day: str, room_digits: int) -> int:
    """Compute expected checksum for *day* and *room_digits*."""
    return (_day_letter_sum(day) + room_digits) % 100


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_slot_code(code: str) -> ValidationResult:
    """
    Validate a medical scheduling appointment slot code.

    Returns a :class:`ValidationResult` with ``valid=True`` when the code
    satisfies all rules, or ``valid=False`` with ``error_field`` and
    ``error_reason`` describing the first failing rule.
    """

    # ------------------------------------------------------------------ #
    # 1. Top-level format check                                            #
    # ------------------------------------------------------------------ #
    if not isinstance(code, str):
        return ValidationResult(
            valid=False,
            error_field="format",
            error_reason="Code must be a string.",
        )

    parts = code.split("-")
    if len(parts) != 4:
        return ValidationResult(
            valid=False,
            error_field="format",
            error_reason=(
                f"Expected 4 dash-separated components, got {len(parts)}."
            ),
        )

    day_part, time_part, room_part, checksum_part = parts

    # ------------------------------------------------------------------ #
    # 2. DAY validation                                                    #
    # ------------------------------------------------------------------ #
    if not _DAY_RE.match(day_part):
        return ValidationResult(
            valid=False,
            error_field="day",
            error_reason=(
                f"DAY must be a 3-letter uppercase abbreviation; got {day_part!r}."
            ),
        )

    if day_part not in VALID_DAYS:
        return ValidationResult(
            valid=False,
            error_field="day",
            error_reason=(
                f"DAY must be one of MON, TUE, WED, THU, FRI; got {day_part!r}."
            ),
        )

    # ------------------------------------------------------------------ #
    # 3. TIME validation                                                   #
    # ------------------------------------------------------------------ #
    if not _TIME_RE.match(time_part):
        return ValidationResult(
            valid=False,
            error_field="time",
            error_reason=(
                f"TIME must be exactly 4 digits (HHMM); got {time_part!r}."
            ),
        )

    hh = int(time_part[:2])
    mm = int(time_part[2:])

    if mm not in (0, 30):
        return ValidationResult(
            valid=False,
            error_field="time",
            error_reason=(
                f"TIME minutes must be 00 or 30; got {mm:02d}."
            ),
        )

    if hh > 23:
        return ValidationResult(
            valid=False,
            error_field="time",
            error_reason=(
                f"TIME hours must be 00–23; got {hh:02d}."
            ),
        )

    if (hh, mm) < _MIN_TIME or (hh, mm) > _MAX_TIME:
        return ValidationResult(
            valid=False,
            error_field="time",
            error_reason=(
                f"TIME must be between 08:00 and 17:30 inclusive; "
                f"got {hh:02d}:{mm:02d}."
            ),
        )

    # ------------------------------------------------------------------ #
    # 4. ROOM validation                                                   #
    # ------------------------------------------------------------------ #
    room_match = _ROOM_RE.match(room_part)
    if not room_match:
        return ValidationResult(
            valid=False,
            error_field="room",
            error_reason=(
                f"ROOM must be 2 uppercase letters followed by 1–2 digits; "
                f"got {room_part!r}."
            ),
        )

    room_prefix = room_match.group(1)
    room_digits = int(room_match.group(2))

    if room_prefix not in VALID_ROOM_PREFIXES:
        return ValidationResult(
            valid=False,
            error_field="room",
            error_reason=(
                f"ROOM prefix must be one of ER, IC, GP, OT; got {room_prefix!r}."
            ),
        )

    # ------------------------------------------------------------------ #
    # 5. CHECKSUM validation                                               #
    # ------------------------------------------------------------------ #
    if not _CHECKSUM_RE.match(checksum_part):
        return ValidationResult(
            valid=False,
            error_field="checksum",
            error_reason=(
                f"CHECKSUM must be exactly 2 digits; got {checksum_part!r}."
            ),
        )

    expected = _compute_checksum(day_part, room_digits)
    actual = int(checksum_part)

    if actual != expected:
        return ValidationResult(
            valid=False,
            error_field="checksum",
            error_reason=(
                f"CHECKSUM mismatch: expected {expected:02d}, got {actual:02d}."
            ),
        )

    # ------------------------------------------------------------------ #
    # All checks passed                                                    #
    # ------------------------------------------------------------------ #
    return ValidationResult(valid=True)
