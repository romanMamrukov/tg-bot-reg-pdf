import re
from datetime import datetime

# Validate Email Address
def is_valid_email(email: str) -> bool:
    email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    return bool(re.match(email_regex, email))

# Validate Attendee Count (should be > 0 and <= available spots)
def is_valid_attendee_count(attendees: int, spots_left: int) -> bool:
    try:
        attendees = int(attendees)  # Convert attendees to an integer
        spots_left = int(spots_left) # Convert spots_left to an integer
        return attendees > 0 and attendees <= spots_left
    except ValueError:
        return False  # In case attendees is not a valid number

# Validate Deeplink Data (Check for valid game_id)
def is_valid_deeplink(params: dict) -> bool:
    return 'game_id' in params and params['game_id']

def is_valid_date(date_str: str, date_format: str = "%Y-%m-%d") -> bool:
    """Validate date string format (default is YYYY-MM-DD)."""
    try:
        datetime.strptime(date_str, date_format)
        return True
    except ValueError:
        return False

def is_valid_invoice(user_data: dict, invoice_number: str) -> bool:
    """Check if the invoice number exists in user data."""
    for registrations in user_data.values():
        for reg in registrations:
            if reg.get('invoice_number') == invoice_number:
                return True
    return False
