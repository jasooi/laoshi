# this file contains helper functions that are general and are used in multiple places throughout the project code
from passlib.hash import pbkdf2_sha256
from datetime import datetime
from sqlalchemy import and_



def hash_password(plain_text_password: str):
    # Passwword validation (abc + 123) should occur on frontend
    return pbkdf2_sha256.hash(plain_text_password)

def check_password(plain_text_password, hashed):
    # this function validates a plain-text password against the stored, hashed password to determine if they match
    return pbkdf2_sha256.verify(plain_text_password, hashed)


def construct_date_range_filter(start_field, end_field, range_start=None, range_end=None):
    if isinstance(range_start, datetime) and isinstance(range_end, datetime):
        return and_(start_field >= range_start, end_field <= range_end)
    elif isinstance(range_start, datetime):
        return start_field >= range_start
    elif isinstance(range_end, datetime):
        return end_field <= range_end
    else:
        raise ValueError("Invalid range parameters")
