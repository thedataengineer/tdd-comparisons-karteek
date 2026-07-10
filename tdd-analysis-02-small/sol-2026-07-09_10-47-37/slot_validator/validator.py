import re

VALID_DAYS = {"MON", "TUE", "WED", "THU", "FRI"}
VALID_ROOM_PREFIXES = {"ER", "IC", "GP", "OT"}
ROOM_PATTERN = re.compile(r'^([A-Z]{2})(\d{1,2})$')


def validate(code):
    parts = code.split("-")
    if len(parts) != 4:
        return {"valid": False, "error": "Invalid format: expected DAY-TIME-ROOM-CHECKSUM"}

    day, time_str, room, checksum_str = parts

    if day not in VALID_DAYS:
        return {"valid": False, "error": f"Invalid DAY '{day}': must be MON, TUE, WED, THU, or FRI"}

    if not (len(time_str) == 4 and time_str.isdigit()):
        return {"valid": False, "error": f"Invalid TIME '{time_str}': must be 4 digits (HHMM)"}

    hours = int(time_str[:2])
    minutes = int(time_str[2:])
    if minutes not in (0, 30):
        return {"valid": False, "error": f"Invalid TIME '{time_str}': must be on the hour or half hour"}

    total_minutes = hours * 60 + minutes
    if total_minutes < 8 * 60 or total_minutes > 17 * 60 + 30:
        return {"valid": False, "error": f"Invalid TIME '{time_str}': must be within 08:00-17:30"}

    room_match = ROOM_PATTERN.match(room)
    if not room_match:
        return {"valid": False, "error": f"Invalid ROOM '{room}': must be 2 uppercase letters followed by 1-2 digits"}
    room_letters = room_match.group(1)
    if room_letters not in VALID_ROOM_PREFIXES:
        return {"valid": False, "error": f"Invalid ROOM '{room}': letters must be one of ER, IC, GP, OT"}
    room_number = int(room_match.group(2))

    day_sum = sum(ord(c) - ord('A') + 1 for c in day)
    expected_checksum = (day_sum + room_number) % 100

    if not checksum_str.isdigit() or len(checksum_str) != 2:
        return {"valid": False, "error": f"Invalid CHECKSUM '{checksum_str}': must be a 2-digit number"}
    actual_checksum = int(checksum_str)
    if actual_checksum != expected_checksum:
        return {"valid": False, "error": f"Invalid CHECKSUM '{checksum_str}': expected {expected_checksum:02d}"}

    return {"valid": True}
