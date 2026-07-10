Build a Python module that validates appointment slot codes used 
by a medical scheduling system.

A valid slot code must satisfy ALL of the following:
- Format is: {DAY}-{TIME}-{ROOM}-{CHECKSUM}
- DAY is a 3-letter uppercase weekday abbreviation: MON, TUE, WED, 
  THU, FRI only (no weekends)
- TIME is a 4-digit 24-hour clock value (HHMM), must be on the hour 
  or half hour, and must fall within 08:00–17:30 inclusive
- ROOM is 2 uppercase letters followed by 1–2 digits; the letters 
  must be one of: ER, IC, GP, OT
- CHECKSUM is a 2-digit number equal to the sum of the numeric 
  positions of the DAY's letters in the alphabet (A=1, Z=26), 
  plus the room number digits, modulo 100
  (e.g. MON = 13+15+14 = 42, room OT7 = 7, checksum = (42+7)%100 = 49)

Your module should expose a validation function that returns a 
structured result indicating whether the code is valid and, if not, 
which specific rule failed and why.