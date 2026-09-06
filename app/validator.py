import re

def clean_and_validate_US_Phone_number(phone_number:str) -> str:
    """
    Cleans and validates a US phone number.
    Strips formatting, validates it's a proper 10-digit US number,
    returns normalized digits-only string.
    """
    digits=re.sub(r'\D', '', phone_number)

    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]

    if len(digits) != 10:
        raise ValueError("Invalid US phone number. Must be 10 digits.")
    if digits[0] in ("0","1"):
        raise ValueError("Invalid US phone number. Area code and exchange code cannot start with 0 or 1.") 

    return digits
