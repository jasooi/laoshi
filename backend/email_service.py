"""Email service for Laoshi Coach using SendGrid."""

import logging
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, HtmlContent

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
FROM_EMAIL = os.getenv('FROM_EMAIL', 'noreply@laoshi.zeabur.app')
APP_BASE_URL = os.getenv('APP_BASE_URL', 'https://laoshi.zeabur.app')


def _send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send an email via SendGrid. Returns True on success, False on failure."""
    if not SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set, skipping email send")
        return False

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=HtmlContent(html_content),
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"Email sent to {to_email}, status={response.status_code}")
        return response.status_code in (200, 201, 202)
    except Exception:
        logger.exception(f"Failed to send email to {to_email}")
        return False


def send_welcome_email(to_email: str, username: str) -> bool:
    """Send a welcome email to a newly registered user."""
    subject = "Welcome to Laoshi Coach!"
    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px; color: #2D2D2D;">
        <h1 style="color: #6B8F71; margin-bottom: 8px;">Welcome to Laoshi Coach!</h1>

        <p style="font-size: 16px; line-height: 1.6;">
            Hey {username},
        </p>

        <p style="font-size: 16px; line-height: 1.6;">
            Glad you are here. Meet your personalised vocabulary coach, <strong>Laoshi</strong>!
            Laoshi is an interactive flashcard tool built for intermediate Mandarin learners like yourself
            to practice using the vocabulary you want to acquire with instant native speaker feedback.
        </p>

        <h2 style="color: #6B8F71; font-size: 18px; margin-top: 28px;">How to Get Started</h2>

        <div style="background: #F5F7F5; border-radius: 12px; padding: 20px; margin: 16px 0;">
            <p style="margin: 0 0 12px 0; font-size: 15px;">
                <strong>Step 1:</strong> Head to your <strong>Library</strong> and create a vocabulary deck,
                or start with the sample deck we've added for you.
            </p>
            <p style="margin: 0 0 12px 0; font-size: 15px;">
                <strong>Step 2:</strong> Start a <strong>Practice Session</strong> from the Home page.
                Laoshi will introduce each word and ask you to form sentences using it.
            </p>
            <p style="margin: 0; font-size: 15px;">
                <strong>Step 3:</strong> After each sentence, Laoshi gives you detailed feedback and scores.
                Rate your confidence to power the <strong>spaced repetition</strong> system that schedules your reviews.
            </p>
        </div>

        <p style="font-size: 15px; line-height: 1.6; color: #666;">
            For easy reference, your registered username is <strong>{username}</strong>.
            If you forget your username, come back to this email to check anytime.
        </p>

        <div style="text-align: center; margin: 32px 0;">
            <a href="{APP_BASE_URL}/home"
               style="display: inline-block; background-color: #6B8F71; color: white; padding: 14px 32px; border-radius: 999px; text-decoration: none; font-weight: 600; font-size: 16px;">
                Enter the Classroom
            </a>
        </div>

        <p style="font-size: 13px; color: #999; text-align: center; margin-top: 32px;">
            Laoshi Coach &mdash; Your Mandarin Practice Partner
        </p>
    </div>
    """
    return _send_email(to_email, subject, html_content)


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """Send a password reset email with a one-time link."""
    reset_link = f"{APP_BASE_URL}/reset-password?token={reset_token}"
    subject = "Reset Your Laoshi Password"
    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px; color: #2D2D2D;">
        <h1 style="color: #6B8F71; margin-bottom: 8px;">Password Reset</h1>

        <p style="font-size: 16px; line-height: 1.6;">
            We received a request to reset your Laoshi Coach password.
            Click the button below to set a new password.
        </p>

        <div style="text-align: center; margin: 32px 0;">
            <a href="{reset_link}"
               style="display: inline-block; background-color: #6B8F71; color: white; padding: 14px 32px; border-radius: 999px; text-decoration: none; font-weight: 600; font-size: 16px;">
                Reset Password
            </a>
        </div>

        <p style="font-size: 14px; color: #666; line-height: 1.6;">
            This link expires in <strong>1 hour</strong> and can only be used once.
            If you didn't request this, you can safely ignore this email.
        </p>

        <p style="font-size: 13px; color: #999; text-align: center; margin-top: 32px;">
            Laoshi Coach &mdash; Your Mandarin Practice Partner
        </p>
    </div>
    """
    return _send_email(to_email, subject, html_content)
