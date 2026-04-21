"""Email service for Laoshi Coach using SendGrid dynamic templates."""

import logging
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
FROM_EMAIL = os.getenv('FROM_EMAIL', 'hello@kotoba-nest.org')
APP_BASE_URL = os.getenv('APP_BASE_URL', 'https://laoshi.zeabur.app')
ONBOARDING_EMAIL_TEMPLATE = os.getenv('ONBOARDING_EMAIL_TEMPLATE')
PASSWORD_RESET_EMAIL_TEMPLATE = os.getenv('PASSWORD_RESET_EMAIL_TEMPLATE')


def _send_email(to_email: str, template_id: str, dynamic_data: dict) -> bool:
    """Send an email via SendGrid dynamic template. Returns True on success, False on failure."""
    if not SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set, skipping email send")
        return False

    if not template_id:
        logger.warning("Template ID not set, skipping email send")
        return False

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
    )
    message.template_id = template_id
    message.dynamic_template_data = dynamic_data

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"Email sent to {to_email}, status={response.status_code}")
        return response.status_code in (200, 201, 202)
    except Exception:
        logger.exception(f"Failed to send email to {to_email}")
        return False


def send_welcome_email(to_email: str, first_name: str, username: str) -> bool:
    """Send a welcome email to a newly registered user."""
    return _send_email(to_email, ONBOARDING_EMAIL_TEMPLATE, {
        'first_name': first_name,
        'username': username,
    })


def send_password_reset_email(to_email: str, first_name: str, reset_token: str) -> bool:
    """Send a password reset email with a one-time link."""
    reset_link = f"{APP_BASE_URL}/reset-password?token={reset_token}"
    return _send_email(to_email, PASSWORD_RESET_EMAIL_TEMPLATE, {
        'first_name': first_name,
        'password_reset_link': reset_link,
    })
