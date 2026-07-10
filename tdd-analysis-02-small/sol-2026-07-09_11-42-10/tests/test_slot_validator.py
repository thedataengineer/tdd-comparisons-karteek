import pytest
from slot_validator import validate


# --- Test 1: Returns a structured result dict with a 'valid' key ---
def test_returns_structured_result():
    result = validate("MON-0800-GP1-55")
    assert isinstance(result, dict)
    assert "valid" in result


# --- Test 2: Wrong number of segments fails with format error ---
def test_wrong_segment_count_is_invalid():
    result = validate("MON-0800-GP1")
    assert result["valid"] is False
    assert "reason" in result
    assert "format" in result["reason"].lower()


# --- Test 3: Invalid DAY abbreviation ---
def test_invalid_day_abbreviation():
    result = validate("SAT-0800-GP1-55")
    assert result["valid"] is False
    assert "day" in result["reason"].lower()


# --- Test 4: TIME must be 4-digit string ---
def test_time_must_be_4_digits():
    result = validate("MON-800-GP1-55")
    assert result["valid"] is False
    assert "time" in result["reason"].lower()


# --- Test 6: TIME must be within 08:00-17:30 ---
def test_time_must_be_within_business_hours():
    result = validate("MON-1900-GP1-55")
    assert result["valid"] is False
    assert "time" in result["reason"].lower()


# --- Test 5: TIME minutes must be 00 or 30 ---
def test_time_must_be_on_hour_or_half_hour():
    result = validate("MON-0815-GP1-55")
    assert result["valid"] is False
    assert "time" in result["reason"].lower()


# --- Test 7: ROOM must have valid 2-letter prefix ---
def test_room_invalid_prefix():
    result = validate("MON-0900-XX1-55")
    assert result["valid"] is False
    assert "room" in result["reason"].lower()


# --- Test 9: Wrong checksum returns invalid ---
# MON=13+15+14=42, GP1=1, correct checksum=(42+1)%100=43, not 99
def test_wrong_checksum_is_invalid():
    result = validate("MON-0900-GP1-99")
    assert result["valid"] is False
    assert "checksum" in result["reason"].lower()


# --- Test 10: Fully valid code passes ---
# MON=42, OT7=7, checksum=(42+7)%100=49 (spec example)
def test_fully_valid_code():
    result = validate("MON-0900-OT7-49")
    assert result["valid"] is True


# --- Test 11: Checksum must be 2 digits ---
def test_checksum_must_be_2_digits():
    result = validate("MON-0900-OT7-X")
    assert result["valid"] is False
    assert "checksum" in result["reason"].lower()


# --- Test 8: ROOM must have 1-2 digit suffix ---
def test_room_missing_digits():
    result = validate("MON-0900-GP-55")
    assert result["valid"] is False
    assert "room" in result["reason"].lower()


# --- Test 12: Boundary time 08:00 is valid ---
# MON=42, ER1=1, checksum=(42+1)%100=43
def test_boundary_time_0800_is_valid():
    result = validate("MON-0800-ER1-43")
    assert result["valid"] is True


# --- Test 13: Boundary time 17:30 is valid ---
# FRI=6+18+9=33, IC12=12, checksum=(33+12)%100=45
def test_boundary_time_1730_is_valid():
    result = validate("FRI-1730-IC12-45")
    assert result["valid"] is True


# --- Test 14: Time just before 08:00 is invalid ---
def test_time_before_0800_is_invalid():
    result = validate("MON-0730-ER1-43")
    assert result["valid"] is False
    assert "time" in result["reason"].lower()


# --- Test 15: Time just after 17:30 is invalid ---
def test_time_after_1730_is_invalid():
    result = validate("MON-1800-ER1-43")
    assert result["valid"] is False
    assert "time" in result["reason"].lower()


# --- Test 16: Each valid day abbreviation is accepted ---
def test_tue_is_valid():
    # TUE=20+21+5=46, ER1=1, checksum=(46+1)%100=47
    result = validate("TUE-0900-ER1-47")
    assert result["valid"] is True


def test_wed_is_valid():
    # WED=23+5+4=32, ER1=1, checksum=(32+1)%100=33
    result = validate("WED-0900-ER1-33")
    assert result["valid"] is True


def test_thu_is_valid():
    # THU=20+8+21=49, ER1=1, checksum=(49+1)%100=50
    result = validate("THU-0900-ER1-50")
    assert result["valid"] is True


def test_fri_is_valid():
    # FRI=6+18+9=33, ER1=1, checksum=(33+1)%100=34
    result = validate("FRI-0900-ER1-34")
    assert result["valid"] is True


# --- Test 17: 2-digit room number is accepted ---
# MON=42, GP12=12, checksum=(42+12)%100=54
def test_room_with_2_digit_number():
    result = validate("MON-0900-GP12-54")
    assert result["valid"] is True


# --- Test 18: Checksum wraps around mod 100 ---
# FRI=33, OT99=99, checksum=(33+99)%100=32
def test_checksum_wraps_modulo_100():
    result = validate("FRI-0900-OT99-32")
    assert result["valid"] is True
