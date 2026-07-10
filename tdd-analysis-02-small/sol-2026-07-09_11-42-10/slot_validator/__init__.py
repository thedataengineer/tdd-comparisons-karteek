import re

VALID_DAYS = {"MON", "TUE", "WED", "THU", "FRI"}
VALID_ROOM_PREFIXES = {"ER", "IC", "GP", "OT"}
ROOM_PATTERN = re.compile(r"^(ER|IC|GP|OT)(\d{1,2})$")


def validate(code):
    parts = code.split("-")
    if len(parts) != 4:
        return {"valid": False, "reason": "Invalid format: expected DAY-TIME-ROOM-CHECKSUM"}

    day, time, room, checksum = parts

    if day not in VALID_DAYS:
        return {"valid": False, "reason": f"Invalid DAY '{day}': must be MON, TUE, WED, THU, or FRI"}

    if not re.fullmatch(r"\d{4}", time):
        return {"valid": False, "reason": f"Invalid TIME '{time}': must be 4 digits (HHMM)"}

    hh, mm = int(time[:2]), int(time[2:])
    if mm not in (0, 30):
        return {"valid": False, "reason": f"Invalid TIME '{time}': minutes must be 00 or 30"}

    # Check 08:00 <= time <= 17:30
    total_minutes = hh * 60 + mm
    if total_minutes < 8 * 60 or total_minutes > 17 * 60 + 30:
        return {"valid": False, "reason": f"Invalid TIME '{time}': must be between 08:00 and 17:30"}

    room_match = ROOM_PATTERN.fullmatch(room)
    if not room_match:
        return {"valid": False, "reason": f"Invalid ROOM '{room}': must be ER/IC/GP/OT followed by 1-2 digits"}

    # Validate checksum
    day_sum = sum(ord(c) - ord('A') + 1 for c in day)
    room_digits = int(room_match.group(2))
    expected_checksum = (day_sum + room_digits) % 100

    if not re.fullmatch(r"\d{2}", checksum):
        return {"valid": False, "reason": f"Invalid CHECKSUM '{checksum}': must be a 2-digit number"}

    if int(checksum) != expected_checksum:
        return {
            "valid": False,
            "reason": f"Invalid CHECKSUM '{checksum}': expected {expected_checksum:02d}"
        }

    return {"valid": True}
