"""Tests for welcome email on registration."""
import pytest
from unittest.mock import patch, MagicMock


class TestWelcomeEmailOnRegistration:
    """Test that registration triggers welcome email."""

    @patch('email_service.send_welcome_email', return_value=True)
    def test_welcome_email_sent_on_registration(self, mock_email, client, db):
        resp = client.post('/api/users', json={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'TestPassword1',
        })
        assert resp.status_code == 201
        mock_email.assert_called_once_with('newuser@example.com', 'newuser')

    @patch('email_service.send_welcome_email', side_effect=Exception('SMTP error'))
    def test_registration_succeeds_if_email_fails(self, mock_email, client, db):
        resp = client.post('/api/users', json={
            'username': 'newuser2',
            'email': 'newuser2@example.com',
            'password': 'TestPassword1',
        })
        # Registration should still succeed even if email fails
        assert resp.status_code == 201
        assert 'created_data' in resp.json


class TestEmailService:
    """Tests for email_service module."""

    @patch('email_service.SENDGRID_API_KEY', None)
    def test_send_welcome_email_skips_without_api_key(self, db):
        from email_service import send_welcome_email
        result = send_welcome_email('test@example.com', 'testuser')
        assert result is False

    @patch('email_service.SENDGRID_API_KEY', 'fake-key')
    @patch('email_service.SendGridAPIClient')
    def test_send_welcome_email_calls_sendgrid(self, mock_sg_class, db):
        mock_client = MagicMock()
        mock_client.send.return_value = MagicMock(status_code=202)
        mock_sg_class.return_value = mock_client

        from email_service import send_welcome_email
        result = send_welcome_email('test@example.com', 'testuser')
        assert result is True
        mock_client.send.assert_called_once()

    @patch('email_service.SENDGRID_API_KEY', None)
    def test_send_password_reset_email_skips_without_api_key(self, db):
        from email_service import send_password_reset_email
        result = send_password_reset_email('test@example.com', 'fake-token')
        assert result is False
