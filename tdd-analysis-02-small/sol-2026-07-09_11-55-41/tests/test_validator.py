"""
Tests for slot_validator.validator
"""

import pytest
from slot_validator import validate_slot_code, ValidationResult
from slot_validator.validator import (
    _letter_position,
    _day_letter_sum,
    _compute_checksum,
)


# ---------------------------------------------------------------------------
# Helper to build valid slot codes on-the-fly
# ---------------------------------------------------------------------------

def make_code(day="MON", time="0900", room="GP1", checksum=None):
    """Build a slot code; compute correct checksum if not supplied."""
    if checksum is None:
        room_digits = int("".join(ch for ch in room if ch.isdigit()))
        checksum = _compute_checksum(day, room_digits)
    return f"{day}-{time}-{room}-{checksum:02d}"


# ---------------------------------------------------------------------------
# Sanity helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_letter_position_a(self):
        assert _letter_position("A") == 1

    def test_letter_position_z(self):
        assert _letter_position("Z") == 26

    def test_letter_position_m(self):
        assert _letter_position("M") == 13

    def test_day_letter_sum_mon(self):
        # M=13, O=15, N=14 → 42
        assert _day_letter_sum("MON") == 42

    def test_day_letter_sum_fri(self):
        # F=6, R=18, I=9 → 33
        assert _day_letter_sum("FRI") == 33

    def test_compute_checksum_example_from_spec(self):
        # MON + OT7: 42 + 7 = 49
        assert _compute_checksum("MON", 7) == 49

    def test_compute_checksum_wraps_modulo(self):
        # Make it overflow 100
        # FRI = 33, room digit 99 → (33+99) % 100 = 32
        assert _compute_checksum("FRI", 99) == 32


# ---------------------------------------------------------------------------
# Valid codes
# ---------------------------------------------------------------------------

class TestValidCodes:
    def test_mon_gp1_0900(self):
        code = make_code("MON", "0900", "GP1")
        result = validate_slot_code(code)
        assert result.valid is True
        assert result.error_field is None
        assert result.error_reason is None

    def test_tue_er2_1200(self):
        code = make_code("TUE", "1200", "ER2")
        assert validate_slot_code(code).valid is True

    def test_wed_ic10_1730(self):
        code = make_code("WED", "1730", "IC10")
        assert validate_slot_code(code).valid is True

    def test_thu_ot7_0800(self):
        # From spec example: MON-...-OT7-49 style
        code = make_code("THU", "0800", "OT7")
        assert validate_slot_code(code).valid is True

    def test_fri_gp99_1500(self):
        code = make_code("FRI", "1500", "GP99")
        assert validate_slot_code(code).valid is True

    def test_half_hour_slot(self):
        code = make_code("MON", "0830", "GP1")
        assert validate_slot_code(code).valid is True

    def test_boundary_0800(self):
        code = make_code("FRI", "0800", "ER1")
        assert validate_slot_code(code).valid is True

    def test_boundary_1730(self):
        code = make_code("FRI", "1730", "ER1")
        assert validate_slot_code(code).valid is True

    def test_all_valid_days(self):
        for day in ("MON", "TUE", "WED", "THU", "FRI"):
            code = make_code(day, "1000", "GP1")
            r = validate_slot_code(code)
            assert r.valid is True, f"Expected valid for day={day}, got: {r}"

    def test_all_valid_room_prefixes(self):
        for prefix in ("ER", "IC", "GP", "OT"):
            room = f"{prefix}1"
            code = make_code("MON", "1000", room)
            r = validate_slot_code(code)
            assert r.valid is True, f"Expected valid for room={room}, got: {r}"

    def test_repr_valid(self):
        r = ValidationResult(valid=True)
        assert repr(r) == "ValidationResult(valid=True)"

    def test_repr_invalid(self):
        r = ValidationResult(valid=False, error_field="day", error_reason="bad day")
        assert "error_field='day'" in repr(r)
        assert "error_reason='bad day'" in repr(r)


# ---------------------------------------------------------------------------
# Format errors
# ---------------------------------------------------------------------------

class TestFormatErrors:
    def test_non_string_input(self):
        r = validate_slot_code(None)
        assert r.valid is False
        assert r.error_field == "format"
        assert "string" in r.error_reason.lower()

    def test_integer_input(self):
        r = validate_slot_code(12345)
        assert r.valid is False
        assert r.error_field == "format"

    def test_too_few_parts(self):
        r = validate_slot_code("MON-0900-GP1")
        assert r.valid is False
        assert r.error_field == "format"
        assert "4" in r.error_reason

    def test_too_many_parts(self):
        r = validate_slot_code("MON-0900-GP1-42-extra")
        assert r.valid is False
        assert r.error_field == "format"

    def test_empty_string(self):
        r = validate_slot_code("")
        assert r.valid is False
        assert r.error_field == "format"


# ---------------------------------------------------------------------------
# DAY errors
# ---------------------------------------------------------------------------

class TestDayErrors:
    def test_weekend_sat(self):
        code = make_code("SAT", "0900", "GP1")
        r = validate_slot_code(code)
        assert r.valid is False
        assert r.error_field == "day"
        assert "SAT" in r.error_reason

    def test_weekend_sun(self):
        code = make_code("SUN", "0900", "GP1")
        r = validate_slot_code(code)
        assert r.valid is False
        assert r.error_field == "day"

    def test_lowercase_day(self):
        # "mon" won't match _DAY_RE (not 3 uppercase letters as a valid day)
        r = validate_slot_code("mon-0900-GP1-42")
        assert r.valid is False
        assert r.error_field == "day"

    def test_day_too_short(self):
        r = validate_slot_code("MO-0900-GP1-42")
        assert r.valid is False
        assert r.error_field == "day"

    def test_day_too_long(self):
        r = validate_slot_code("MOND-0900-GP1-42")
        assert r.valid is False
        assert r.error_field == "day"

    def test_day_with_digit(self):
        r = validate_slot_code("M0N-0900-GP1-42")
        assert r.valid is False
        assert r.error_field == "day"

    def test_invalid_three_letter_day(self):
        # Looks like 3 uppercase letters but not a valid weekday
        r = validate_slot_code("XYZ-0900-GP1-42")
        assert r.valid is False
        assert r.error_field == "day"
        assert "MON" in r.error_reason or "FRI" in r.error_reason


# ---------------------------------------------------------------------------
# TIME errors
# ---------------------------------------------------------------------------

class TestTimeErrors:
    def test_time_not_digits(self):
        r = validate_slot_code("MON-09AM-GP1-42")
        assert r.valid is False
        assert r.error_field == "time"

    def test_time_too_short(self):
        r = validate_slot_code("MON-900-GP1-42")
        assert r.valid is False
        assert r.error_field == "time"

    def test_time_too_long(self):
        r = validate_slot_code("MON-09000-GP1-42")
        assert r.valid is False
        assert r.error_field == "time"

    def test_time_not_on_hour_or_half(self):
        code = make_code("MON", "0915", "GP1")
        # Override checksum with the raw constructed string
        r = validate_slot_code("MON-0915-GP1-42")
        assert r.valid is False
        assert r.error_field == "time"
        assert "30" in r.error_reason or "00" in r.error_reason

    def test_time_too_early(self):
        r = validate_slot_code("MON-0730-GP1-42")
        assert r.valid is False
        assert r.error_field == "time"

    def test_time_too_late(self):
        r = validate_slot_code("MON-1800-GP1-42")
        assert r.valid is False
        assert r.error_field == "time"

    def test_time_invalid_hours(self):
        # 2500 – hours > 23
        r = validate_slot_code("MON-2500-GP1-42")
        assert r.valid is False
        assert r.error_field == "time"

    def test_time_just_before_open(self):
        # 07:30 – before 08:00
        r = validate_slot_code("MON-0730-GP1-42")
        assert r.valid is False
        assert r.error_field == "time"

    def test_time_just_after_close(self):
        # 18:00 – after 17:30
        r = validate_slot_code("MON-1800-GP1-42")
        assert r.valid is False
        assert r.error_field == "time"

    def test_time_minutes_45(self):
        r = validate_slot_code("MON-0945-GP1-42")
        assert r.valid is False
        assert r.error_field == "time"


# ---------------------------------------------------------------------------
# ROOM errors
# ---------------------------------------------------------------------------

class TestRoomErrors:
    def test_room_no_digits(self):
        r = validate_slot_code("MON-0900-GP-42")
        assert r.valid is False
        assert r.error_field == "room"

    def test_room_too_many_digits(self):
        # 3 digits is too many
        r = validate_slot_code("MON-0900-GP123-42")
        assert r.valid is False
        assert r.error_field == "room"

    def test_room_lowercase_prefix(self):
        r = validate_slot_code("MON-0900-gp1-42")
        assert r.valid is False
        assert r.error_field == "room"

    def test_room_invalid_prefix(self):
        r = validate_slot_code("MON-0900-XY1-42")
        assert r.valid is False
        assert r.error_field == "room"
        assert "ER" in r.error_reason or "GP" in r.error_reason

    def test_room_only_digits(self):
        r = validate_slot_code("MON-0900-123-42")
        assert r.valid is False
        assert r.error_field == "room"

    def test_room_three_letters_no_digit(self):
        r = validate_slot_code("MON-0900-GPX-42")
        assert r.valid is False
        assert r.error_field == "room"

    def test_room_valid_two_digit_number(self):
        code = make_code("MON", "0900", "ER12")
        assert validate_slot_code(code).valid is True

    def test_room_er_prefix(self):
        code = make_code("TUE", "1000", "ER5")
        assert validate_slot_code(code).valid is True

    def test_room_ic_prefix(self):
        code = make_code("WED", "1100", "IC3")
        assert validate_slot_code(code).valid is True


# ---------------------------------------------------------------------------
# CHECKSUM errors
# ---------------------------------------------------------------------------

class TestChecksumErrors:
    def test_checksum_wrong_value(self):
        # Build a valid code then corrupt the checksum
        code = make_code("MON", "0900", "GP1")
        parts = code.split("-")
        # Flip the checksum
        wrong = str((int(parts[3]) + 1) % 100).zfill(2)
        bad_code = "-".join(parts[:3] + [wrong])
        r = validate_slot_code(bad_code)
        assert r.valid is False
        assert r.error_field == "checksum"
        assert "mismatch" in r.error_reason.lower()

    def test_checksum_single_digit(self):
        r = validate_slot_code("MON-0900-GP1-5")
        assert r.valid is False
        assert r.error_field == "checksum"

    def test_checksum_three_digits(self):
        r = validate_slot_code("MON-0900-GP1-042")
        assert r.valid is False
        assert r.error_field == "checksum"

    def test_checksum_letters(self):
        r = validate_slot_code("MON-0900-GP1-AB")
        assert r.valid is False
        assert r.error_field == "checksum"

    def test_checksum_zero_padded_correct(self):
        # FRI + GP1: FRI=33, 1 → 34 → "34"
        code = make_code("FRI", "0900", "GP1")
        assert validate_slot_code(code).valid is True

    def test_checksum_wraparound(self):
        # Construct a case where checksum wraps around mod 100
        # WED = W(23)+E(5)+D(4) = 32; GP99 = 99 → (32+99)%100 = 31
        code = make_code("WED", "0900", "GP99")
        assert validate_slot_code(code).valid is True


# ---------------------------------------------------------------------------
# Edge / integration cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_spec_example_mon_ot7(self):
        """Spec states MON→42, OT7→7, checksum=(42+7)%100=49."""
        r = validate_slot_code("MON-0900-OT7-49")
        assert r.valid is True

    def test_spec_example_wrong_checksum(self):
        r = validate_slot_code("MON-0900-OT7-50")
        assert r.valid is False
        assert r.error_field == "checksum"

    def test_all_boundaries_together(self):
        # 08:00 is valid, 17:30 is valid
        for time in ("0800", "1730"):
            code = make_code("MON", time, "GP1")
            assert validate_slot_code(code).valid is True

    def test_code_with_extra_whitespace(self):
        r = validate_slot_code(" MON-0900-GP1-42")
        assert r.valid is False  # Leading space breaks parsing

    def test_room_digit_zero(self):
        # Room like GP0 should be valid structurally
        code = make_code("MON", "0900", "GP0")
        assert validate_slot_code(code).valid is True
