from slot_validator import validate


def test_validate_is_callable():
    assert callable(validate)


def test_validate_returns_structured_result():
    result = validate("MON-0800-GP1-49")
    assert isinstance(result, dict)
    assert "valid" in result


def test_wrong_number_of_segments_is_invalid():
    result = validate("MON-0800-GP1")
    assert result["valid"] is False
    assert "error" in result


def test_weekend_day_is_invalid():
    result = validate("SAT-0800-GP1-49")
    assert result["valid"] is False
    assert "DAY" in result["error"]


def test_lowercase_day_is_invalid():
    result = validate("mon-0800-GP1-49")
    assert result["valid"] is False
    assert "DAY" in result["error"]


def test_time_non_digits_is_invalid():
    result = validate("MON-08AB-GP1-49")
    assert result["valid"] is False
    assert "TIME" in result["error"]


def test_time_not_on_hour_or_half_is_invalid():
    result = validate("MON-0815-GP1-49")
    assert result["valid"] is False
    assert "TIME" in result["error"]


def test_time_before_0800_is_invalid():
    result = validate("MON-0730-GP1-49")
    assert result["valid"] is False
    assert "TIME" in result["error"]


def test_time_after_1730_is_invalid():
    result = validate("MON-1800-GP1-49")
    assert result["valid"] is False
    assert "TIME" in result["error"]


def test_room_with_invalid_letters_is_invalid():
    result = validate("MON-0800-AB1-49")
    assert result["valid"] is False
    assert "ROOM" in result["error"]


def test_room_without_digits_is_invalid():
    result = validate("MON-0800-GP-49")
    assert result["valid"] is False
    assert "ROOM" in result["error"]


def test_wrong_checksum_is_invalid():
    # MON = 13+15+14 = 42, GP1 room digits = 1, checksum = (42+1)%100 = 43
    result = validate("MON-0800-GP1-99")
    assert result["valid"] is False
    assert "CHECKSUM" in result["error"]


def test_correct_checksum_is_valid():
    # MON = 13+15+14 = 42, GP1 room digits = 1, checksum = (42+1)%100 = 43
    result = validate("MON-0800-GP1-43")
    assert result["valid"] is True
    assert "error" not in result


def test_spec_example_mon_ot7_checksum_49():
    # MON = 13+15+14 = 42, OT7 room digits = 7, checksum = (42+7)%100 = 49
    result = validate("MON-0800-OT7-49")
    assert result["valid"] is True


def test_checksum_single_digit_is_invalid():
    # checksum must be exactly 2 digits
    result = validate("MON-0800-GP1-3")
    assert result["valid"] is False
    assert "CHECKSUM" in result["error"]


def test_time_1730_is_valid():
    # MON=42, GP1=1, checksum=43
    result = validate("MON-1730-GP1-43")
    assert result["valid"] is True


def test_all_valid_days():
    # FRI=6+18+9=33, ER1=1, checksum=(33+1)%100=34
    for day, day_sum in [("TUE", 20+21+5), ("WED", 23+5+4), ("THU", 20+8+21), ("FRI", 6+18+9)]:
        expected = (day_sum + 1) % 100
        code = f"{day}-0800-ER1-{expected:02d}"
        result = validate(code)
        assert result["valid"] is True, f"{code} should be valid, got: {result}"


def test_all_valid_room_prefixes():
    # MON=42, room X1=1, checksum=(42+1)%100=43
    mon_sum = 13 + 15 + 14  # 42
    for prefix in ["ER", "IC", "GP", "OT"]:
        expected = (mon_sum + 1) % 100
        code = f"MON-0800-{prefix}1-{expected:02d}"
        result = validate(code)
        assert result["valid"] is True, f"{code} should be valid, got: {result}"


def test_room_with_two_digit_number_is_valid():
    # MON=42, GP12=12, checksum=(42+12)%100=54
    result = validate("MON-0800-GP12-54")
    assert result["valid"] is True


def test_checksum_wraps_mod_100():
    # WED = 23+5+4 = 32, GP99 = 99, checksum = (32+99)%100 = 31
    result = validate("WED-0800-GP99-31")
    assert result["valid"] is True
