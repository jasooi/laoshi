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


def paginate_query(query, page=1, per_page=20, max_per_page=100):
    """
    Apply pagination to a SQLAlchemy query.

    Args:
        query: A SQLAlchemy Query object (before .all() is called)
        page: Page number (1-indexed), defaults to 1
        per_page: Items per page, defaults to 20
        max_per_page: Maximum allowed per_page, defaults to 100

    Returns:
        tuple: (list_of_items, pagination_dict)
    """
    per_page = max(1, min(per_page, max_per_page))
    page = max(1, page)
    total = query.count()
    total_pages = max((total + per_page - 1) // per_page, 1)
    page = min(page, total_pages)
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
        "next_page": page + 1 if page < total_pages else None,
        "prev_page": page - 1 if page > 1 else None,
    }


def construct_date_range_filter(start_field, end_field, range_start=None, range_end=None):
    if isinstance(range_start, datetime) and isinstance(range_end, datetime):
        return and_(start_field >= range_start, end_field <= range_end)
    elif isinstance(range_start, datetime):
        return start_field >= range_start
    elif isinstance(range_end, datetime):
        return end_field <= range_end
    else:
        raise ValueError("Invalid range parameters")
