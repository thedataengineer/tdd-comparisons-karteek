"""
Tests for the medical scheduling slot code validator.

Slot format: {DAY}-{TIME}-{ROOM}-{CHECKSUM}
"""

import pytest
from slot_validator import validate_slot_code, ValidationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def checksum_for(day: str, room: str) -> str:
    day_sum = sum(ord(ch) - ord('A') + 1 for ch in day)
    room_digits = int(''.join(c for c in room if c.isdigit()))
    return f"{(day_sum + room_digits) % 100:02d}"


def make_code(day="MON", time="0900", room="GP1", checksum=None) -> str:
    if checksum is None:
        checksum = checksum_for(day, room)
    return f"{day}-{time}-{room}-{checksum}"


# ---------------------------------------------------------------------------
# Sanity: known-good codes from the spec
# ---------------------------------------------------------------------------

class TestKnownGoodCodes:
    def test_spec_example_mon_ot7(self):
        # MON = 13+15+14 = 42, OT7 = 7, (42+7)%100 = 49
        result = validate_slot_code("MON-0900-OT7-49")
        assert result.valid is True

    def test_all_valid_days(self):
        for day in ("MON", "TUE", "WED", "THU", "FRI"):
            code = make_code(day=day)
            r = validate_slot_code(code)
            assert r.valid is True, f"Expected valid for day={day}, got {r}"

    def test_all_valid_room_prefixes(self):
        for prefix in ("ER", "IC", "GP", "OT"):
            room = f"{prefix}1"
            code = make_code(room=room)
            r = validate_slot_code(code)
            assert r.valid is True, f"Expected valid for room={room}, got {r}"

    def test_room_with_two_digits(self):
        room = "GP12"
        code = make_code(room=room)
        assert validate_slot_code(code).valid is True

    def test_boundary_time_0800(self):
        code = make_code(time="0800")
        assert validate_slot_code(code).valid is True

    def test_boundary_time_1730(self):
        code = make_code(time="1730")
        assert validate_slot_code(code).valid is True

    def test_half_hour_times(self):
        for hh in range(8, 18):
            t = f"{hh:02d}30"
            if (hh, 30) > (17, 30):
                continue
            code = make_code(time=t)
            r = validate_slot_code(code)
            assert r.valid is True, f"Expected valid for time={t}"

    def test_on_the_hour_times(self):
        for hh in range(8, 18):
            t = f"{hh:02d}00"
            code = make_code(time=t)
            r = validate_slot_code(code)
            assert r.valid is True, f"Expected valid for time={t}"

    def test_checksum_zero_padded(self):
        # Find a combo where checksum < 10 so zero-padding matters
        # FRI = 6+18+9 = 33, ER1 = 1, (33+1)%100 = 34
        code = "FRI-0900-ER1-34"
        assert validate_slot_code(code).valid is True

    def test_result_repr_valid(self):
        r = validate_slot_code(make_code())
        assert "valid=True" in repr(r)


# ---------------------------------------------------------------------------
# Format errors
# ---------------------------------------------------------------------------

class TestFormatErrors:
    def test_non_string_input(self):
        r = validate_slot_code(12345)
        assert r.valid is False
        assert r.error_field == "format"
        assert "string" in r.error_reason.lower()

    def test_none_input(self):
        r = validate_slot_code(None)
        assert r.valid is False
        assert r.error_field == "format"

    def test_too_few_parts(self):
        r = validate_slot_code("MON-0900-GP1")
        assert r.valid is False
        assert r.error_field == "format"
        assert "4" in r.error_reason

    def test_too_many_parts(self):
        r = validate_slot_code("MON-0900-GP1-49-EXTRA")
        assert r.valid is False
        assert r.error_field == "format"

    def test_empty_string(self):
        r = validate_slot_code("")
        assert r.valid is False
        assert r.error_field == "format"

    def test_result_repr_invalid(self):
        r = validate_slot_code("bad")
        assert "valid=False" in repr(r)
        assert "error_field" in repr(r)


# ---------------------------------------------------------------------------
# DAY validation
# ---------------------------------------------------------------------------

class TestDayValidation:
    def test_weekend_sat(self):
        r = validate_slot_code(make_code(day="SAT"))
        assert r.valid is False
        assert r.error_field == "DAY"
        assert "SAT" in r.error_reason

    def test_weekend_sun(self):
        r = validate_slot_code(make_code(day="SUN"))
        assert r.valid is False
        assert r.error_field == "DAY"

    def test_lowercase_day(self):
        r = validate_slot_code("mon-0900-GP1-14")
        assert r.valid is False
        assert r.error_field == "DAY"

    def test_day_too_short(self):
        r = validate_slot_code("MO-0900-GP1-14")
        assert r.valid is False
        assert r.error_field == "DAY"

    def test_day_too_long(self):
        r = validate_slot_code("MOND-0900-GP1-14")
        assert r.valid is False
        assert r.error_field == "DAY"

    def test_day_with_digits(self):
        r = validate_slot_code("M0N-0900-GP1-14")
        assert r.valid is False
        assert r.error_field == "DAY"

    def test_invalid_abbreviation(self):
        r = validate_slot_code("XYZ-0900-GP1-14")
        assert r.valid is False
        assert r.error_field == "DAY"


# ---------------------------------------------------------------------------
# TIME validation
# ---------------------------------------------------------------------------

class TestTimeValidation:
    def test_time_not_four_digits(self):
        r = validate_slot_code(make_code(time="900"))
        assert r.valid is False
        assert r.error_field == "TIME"

    def test_time_with_letters(self):
        r = validate_slot_code(make_code(time="09AM"))
        assert r.valid is False
        assert r.error_field == "TIME"

    def test_time_before_0800(self):
        r = validate_slot_code(make_code(time="0730"))
        assert r.valid is False
        assert r.error_field == "TIME"
        assert "08:00" in r.error_reason or "range" in r.error_reason.lower()

    def test_time_after_1730(self):
        r = validate_slot_code(make_code(time="1800"))
        assert r.valid is False
        assert r.error_field == "TIME"

    def test_time_at_1730_plus_30(self):
        r = validate_slot_code(make_code(time="1800"))
        assert r.valid is False
        assert r.error_field == "TIME"

    def test_time_not_on_hour_or_half(self):
        r = validate_slot_code(make_code(time="0915"))
        assert r.valid is False
        assert r.error_field == "TIME"
        assert "30" in r.error_reason or "half" in r.error_reason.lower()

    def test_time_invalid_hours(self):
        r = validate_slot_code(make_code(time="2530"))
        assert r.valid is False
        assert r.error_field == "TIME"

    def test_time_invalid_minutes(self):
        r = validate_slot_code(make_code(time="0960"))
        assert r.valid is False
        assert r.error_field == "TIME"

    def test_time_0000_out_of_range(self):
        r = validate_slot_code(make_code(time="0000"))
        assert r.valid is False
        assert r.error_field == "TIME"

    def test_time_1730_is_valid(self):
        code = make_code(time="1730")
        assert validate_slot_code(code).valid is True

    def test_time_1800_is_invalid(self):
        r = validate_slot_code(make_code(time="1800"))
        assert r.valid is False
        assert r.error_field == "TIME"


# ---------------------------------------------------------------------------
# ROOM validation
# ---------------------------------------------------------------------------

class TestRoomValidation:
    def test_invalid_prefix(self):
        r = validate_slot_code(make_code(room="AB1"))
        assert r.valid is False
        assert r.error_field == "ROOM"
        assert "AB" in r.error_reason

    def test_lowercase_room(self):
        r = validate_slot_code(make_code(room="gp1"))
        assert r.valid is False
        assert r.error_field == "ROOM"

    def test_room_no_digits(self):
        # Can't use make_code helper (no digits in room), build code manually
        r = validate_slot_code("MON-0900-GP-43")
        assert r.valid is False
        assert r.error_field == "ROOM"

    def test_room_three_digits(self):
        r = validate_slot_code(make_code(room="GP123"))
        assert r.valid is False
        assert r.error_field == "ROOM"

    def test_room_only_digits(self):
        r = validate_slot_code(make_code(room="123"))
        assert r.valid is False
        assert r.error_field == "ROOM"

    def test_room_one_letter(self):
        r = validate_slot_code(make_code(room="G1"))
        assert r.valid is False
        assert r.error_field == "ROOM"

    def test_room_three_letters(self):
        r = validate_slot_code(make_code(room="GPA1"))
        assert r.valid is False
        assert r.error_field == "ROOM"

    def test_all_valid_prefixes_two_digits(self):
        for prefix in ("ER", "IC", "GP", "OT"):
            room = f"{prefix}99"
            code = make_code(room=room)
            assert validate_slot_code(code).valid is True

    def test_er_room(self):
        code = make_code(room="ER5")
        assert validate_slot_code(code).valid is True

    def test_ic_room(self):
        code = make_code(room="IC3")
        assert validate_slot_code(code).valid is True


# ---------------------------------------------------------------------------
# CHECKSUM validation
# ---------------------------------------------------------------------------

class TestChecksumValidation:
    def test_wrong_checksum(self):
        # MON-GP1 correct checksum = (42+1)%100 = 43
        r = validate_slot_code("MON-0900-GP1-00")
        assert r.valid is False
        assert r.error_field == "CHECKSUM"
        assert "43" in r.error_reason

    def test_checksum_one_digit(self):
        r = validate_slot_code("MON-0900-GP1-5")
        assert r.valid is False
        assert r.error_field == "CHECKSUM"

    def test_checksum_three_digits(self):
        r = validate_slot_code("MON-0900-GP1-043")
        assert r.valid is False
        assert r.error_field == "CHECKSUM"

    def test_checksum_non_numeric(self):
        r = validate_slot_code("MON-0900-GP1-AB")
        assert r.valid is False
        assert r.error_field == "CHECKSUM"

    def test_checksum_wraps_modulo_100(self):
        # Choose a combo where (day_sum + room_digits) >= 100
        # FRI=33, OT99=99, (33+99)%100 = 32
        code = "FRI-0900-OT99-32"
        assert validate_slot_code(code).valid is True

    def test_checksum_spec_example(self):
        # MON=42, OT7=7, checksum=49
        assert validate_slot_code("MON-0900-OT7-49").valid is True

    def test_off_by_one_checksum(self):
        # MON-GP1 correct=43; try 44
        r = validate_slot_code("MON-0900-GP1-44")
        assert r.valid is False
        assert r.error_field == "CHECKSUM"

    def test_checksum_uses_room_digits_only(self):
        # GP12: day_sum(MON)=42, room_digits=12, (42+12)%100=54
        code = "MON-0900-GP12-54"
        assert validate_slot_code(code).valid is True


# ---------------------------------------------------------------------------
# Integration / edge cases
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_full_valid_code_tue_ic2(self):
        # TUE = 20+21+5 = 46, IC2 = 2, (46+2)%100 = 48
        code = "TUE-1030-IC2-48"
        assert validate_slot_code(code).valid is True

    def test_full_valid_code_wed_er10(self):
        # WED = 23+5+4 = 32, ER10 = 10, (32+10)%100 = 42
        code = "WED-1400-ER10-42"
        assert validate_slot_code(code).valid is True

    def test_full_valid_code_thu_gp7(self):
        # THU = 20+8+21 = 49, GP7 = 7, (49+7)%100 = 56
        code = "THU-0830-GP7-56"
        assert validate_slot_code(code).valid is True

    def test_full_valid_code_fri_ot1(self):
        # FRI = 6+18+9 = 33, OT1 = 1, (33+1)%100 = 34
        code = "FRI-1700-OT1-34"
        assert validate_slot_code(code).valid is True

    def test_validation_result_fields_on_success(self):
        r = validate_slot_code(make_code())
        assert r.valid is True
        assert r.error_field is None
        assert r.error_reason is None

    def test_validation_result_fields_on_failure(self):
        r = validate_slot_code("BAD-CODE-HERE-NOW")
        assert r.valid is False
        assert r.error_field is not None
        assert r.error_reason is not None
