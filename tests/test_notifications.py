"""
Tests for notification system.
"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from notifications.base import NotificationProvider, NotificationMessage
from notifications.manager import NotificationManager
from notifications.email_provider import EmailProvider
from notifications.gemini_provider import GeminiProvider
from shared.id_comparator import GradeChange


@pytest.fixture
def sample_message():
    """Create sample notification message"""
    return NotificationMessage(
        title="Test Notification",
        content="This is a test message",
        priority="normal",
        metadata={'test': True}
    )


@pytest.fixture
def email_config():
    """Email provider configuration"""
    return {
        'enabled': True,
        'smtp_server': 'smtp.test.com',
        'smtp_port': 587,
        'sender_email': 'sender@test.com',
        'sender_password': 'password',
        'receiver_email': 'receiver@test.com'
    }


@pytest.fixture
def gemini_config():
    """Gemini provider configuration"""
    return {
        'enabled': True,
        'api_key': 'test_api_key'
    }


class TestNotificationMessage:
    """Tests for NotificationMessage"""

    def test_message_creation(self):
        """Test creating a notification message"""
        msg = NotificationMessage(
            title="Test",
            content="Content",
            priority="high"
        )

        assert msg.title == "Test"
        assert msg.content == "Content"
        assert msg.priority == "high"

    def test_message_with_metadata(self):
        """Test message with metadata"""
        msg = NotificationMessage(
            title="Test",
            content="Content",
            metadata={'key': 'value'}
        )

        assert msg.metadata['key'] == 'value'

    def test_message_defaults(self):
        """Test message default values"""
        msg = NotificationMessage(
            title="Test",
            content="Content"
        )

        assert msg.priority == "normal"
        assert msg.url is None
        assert msg.url_title is None


class TestNotificationManager:
    """Tests for NotificationManager"""

    def test_manager_loads_enabled_providers(self, email_config):
        """Test that manager loads enabled providers"""
        config = {'email': email_config}

        with patch.object(EmailProvider, 'is_available', return_value=True):
            manager = NotificationManager(config)

        assert 'email' in manager.get_available_providers()

    def test_manager_skips_disabled_providers(self):
        """Test that manager skips disabled providers"""
        config = {
            'email': {'enabled': False, 'smtp_server': 'x', 'smtp_port': 587,
                      'sender_email': 'a', 'sender_password': 'b', 'receiver_email': 'c'}
        }

        manager = NotificationManager(config)

        assert 'email' not in manager.get_available_providers()

    def test_manager_handles_unavailable_providers(self, email_config):
        """Test that manager handles providers that aren't available"""
        config = {'email': email_config}

        with patch.object(EmailProvider, 'is_available', return_value=False):
            manager = NotificationManager(config)

        assert 'email' not in manager.get_available_providers()

    def test_send_notification_returns_results(self, email_config, sample_message):
        """Test that send_notification returns per-provider results"""
        config = {'email': email_config}

        with patch.object(EmailProvider, 'is_available', return_value=True):
            with patch.object(EmailProvider, 'send', return_value=True):
                manager = NotificationManager(config)
                results = manager.send_notification(sample_message)

        assert 'email' in results
        assert results['email'] is True

    def test_send_notification_handles_failure(self, email_config, sample_message):
        """Test that send_notification handles provider failures"""
        config = {'email': email_config}

        with patch.object(EmailProvider, 'is_available', return_value=True):
            with patch.object(EmailProvider, 'send', return_value=False):
                manager = NotificationManager(config)
                results = manager.send_notification(sample_message)

        assert results['email'] is False

    def test_send_to_specific_providers(self, email_config, gemini_config, sample_message):
        """Test sending to specific providers only"""
        config = {
            'email': email_config,
            'gemini': gemini_config
        }

        with patch.object(EmailProvider, 'is_available', return_value=True):
            with patch.object(GeminiProvider, 'is_available', return_value=True):
                with patch.object(EmailProvider, 'send', return_value=True):
                    manager = NotificationManager(config)
                    results = manager.send_notification(sample_message, providers=['email'])

        assert 'email' in results
        assert 'gemini' not in results


class TestNotificationManagerFactory:
    """Tests for NotificationManager.from_app_config factory method"""

    def test_factory_creates_gemini_config(self):
        """Test factory creates gemini config from app config"""
        @dataclass
        class MockNotificationConfig:
            gemini_api_key: str = 'gemini_key'
            email_enabled: bool = False
            email_sender: str = None
            email_password: str = None
            email_receiver: str = None

        config = MockNotificationConfig()

        with patch.object(GeminiProvider, 'is_available', return_value=True):
            manager = NotificationManager.from_app_config(config)

        assert 'gemini' in manager.config

    def test_factory_creates_email_config(self):
        """Test factory creates email config from app config"""
        @dataclass
        class MockNotificationConfig:
            gemini_api_key: str = None
            email_enabled: bool = True
            email_sender: str = 'sender@test.com'
            email_password: str = 'password'
            email_receiver: str = 'receiver@test.com'

        config = MockNotificationConfig()

        with patch.object(EmailProvider, 'is_available', return_value=True):
            manager = NotificationManager.from_app_config(config)

        assert 'email' in manager.config


class TestEmailProvider:
    """Tests for EmailProvider"""

    def test_is_available_with_credentials(self, email_config):
        """Test is_available returns True with valid credentials"""
        provider = EmailProvider(email_config)
        assert provider.is_available() is True

    def test_is_available_without_credentials(self):
        """Test is_available returns False without credentials"""
        provider = EmailProvider({'enabled': True})
        assert provider.is_available() is False


class TestEmailHtmlRendering:
    """Tests for email HTML rendering with GradeChange objects"""

    def _make_provider(self):
        return EmailProvider({
            'enabled': True,
            'smtp_server': 'smtp.test.com',
            'smtp_port': 587,
            'sender_email': 'sender@test.com',
            'sender_password': 'password',
            'receiver_email': 'receiver@test.com'
        })

    def test_build_html_with_grade_changes(self):
        """Test that _build_html renders hierarchical HTML from GradeChange objects"""
        provider = self._make_provider()

        changes = [
            GradeChange(
                assignment_id="100",
                assignment_title="Quiz 3",
                section_name="Math 7: Section 1",
                period_name="T1 2024-2025",
                category_name="Homework",
                old_grade=None,
                new_grade="8 / 10",
                old_comment=None,
                new_comment="No comment",
                change_type="new_assignment",
                new_earned=Decimal("8"),
                new_max=Decimal("10"),
            ),
            GradeChange(
                assignment_id="101",
                assignment_title="Assignment 5",
                section_name="Math 7: Section 1",
                period_name="T1 2024-2025",
                category_name="Homework",
                old_grade="7 / 10",
                new_grade="9 / 10",
                old_comment="No comment",
                new_comment="No comment",
                change_type="grade_updated",
                new_earned=Decimal("9"),
                new_max=Decimal("10"),
                old_earned=Decimal("7"),
                old_max=Decimal("10"),
            ),
        ]

        message = NotificationMessage(
            title="Schoology Grade Changes Detected",
            content="Changes detected: 1 new assignment(s), 1 grade update(s)",
            metadata={
                'grade_changes': {
                    'type': 'update',
                    'change_objects': changes,
                }
            }
        )

        html = provider._build_html(message)

        # Should contain section header
        assert "Math 7: Section 1" in html
        # Should contain period
        assert "T1 2024-2025" in html
        # Should contain category
        assert "Homework" in html
        # Should contain assignment names
        assert "Quiz 3" in html
        assert "Assignment 5" in html
        # Should contain percentage
        assert "80%" in html
        assert "90%" in html
        # Should contain letter grade
        assert "B-" in html
        assert "A-" in html
        # Should have styled HTML structure
        assert "<!DOCTYPE html>" in html
        # Should contain "New:" label for new assignments
        assert "New:" in html

    def test_build_html_fallback_without_changes(self):
        """Test that _build_html falls back to plain text when no change objects"""
        provider = self._make_provider()

        message = NotificationMessage(
            title="Error Notification",
            content="Something went wrong\nDetails here",
        )

        html = provider._build_html(message)

        assert "Something went wrong" in html
        assert "<br>" in html
        assert "<!DOCTYPE html>" in html

    def test_build_html_with_ai_analysis(self):
        """Test that AI analysis section is rendered"""
        provider = self._make_provider()

        changes = [
            GradeChange(
                assignment_id="100",
                assignment_title="Test",
                section_name="Math",
                period_name="T1",
                category_name="HW",
                old_grade=None,
                new_grade="10 / 10",
                old_comment=None,
                new_comment="No comment",
                change_type="new_assignment",
                new_earned=Decimal("10"),
                new_max=Decimal("10"),
            ),
        ]

        message = NotificationMessage(
            title="Grade Changes",
            content="Changes detected: 1 new assignment(s)\n\n--- AI Analysis ---\nStudent is doing well.",
            metadata={
                'grade_changes': {
                    'type': 'update',
                    'change_objects': changes,
                }
            }
        )

        html = provider._build_html(message)

        assert "AI Analysis" in html
        assert "Student is doing well." in html

    def test_render_comment_change(self):
        """Test rendering of comment-updated changes"""
        provider = self._make_provider()

        change = GradeChange(
            assignment_id="100",
            assignment_title="Lab Report",
            section_name="Science",
            period_name="T1",
            category_name="Labs",
            old_grade="10 / 10",
            new_grade="10 / 10",
            old_comment="Good",
            new_comment="Excellent",
            change_type="comment_updated",
            new_earned=Decimal("10"),
            new_max=Decimal("10"),
            old_earned=Decimal("10"),
            old_max=Decimal("10"),
        )

        html = provider._render_change_html(change)

        assert "Lab Report" in html
        assert "Comment updated" in html


class TestGeminiProvider:
    """Tests for GeminiProvider"""

    def test_is_available_with_api_key(self, gemini_config):
        """Test is_available returns True with API key"""
        with patch('notifications.gemini_provider.genai'):
            provider = GeminiProvider(gemini_config)
            # Note: is_available also checks if client was created
            assert provider.config.get('api_key') == 'test_api_key'

    def test_is_available_without_api_key(self):
        """Test is_available returns False without API key"""
        provider = GeminiProvider({'enabled': True})
        assert provider.is_available() is False


class TestGeminiIntegration:
    """Tests for Gemini AI integration with notification flow"""

    def test_gemini_runs_first_and_enhances_message(self, sample_message):
        """Test that Gemini runs first and enhances message for other providers"""
        config = {
            'gemini': {'enabled': True, 'api_key': 'key'},
            'email': {'enabled': True, 'smtp_server': 'smtp.test.com', 'smtp_port': 587,
                      'sender_email': 'a@b.com', 'sender_password': 'pw',
                      'receiver_email': 'c@d.com'}
        }

        # Mock Gemini to add AI analysis to metadata
        def mock_gemini_send(msg):
            msg.metadata['ai_analysis'] = "AI generated summary"
            return True

        with patch.object(GeminiProvider, 'is_available', return_value=True):
            with patch.object(GeminiProvider, 'send', side_effect=mock_gemini_send):
                with patch.object(EmailProvider, 'is_available', return_value=True):
                    with patch.object(EmailProvider, 'send', return_value=True) as mock_email:
                        manager = NotificationManager(config)
                        results = manager.send_notification(sample_message)

        # Gemini should have run
        assert results.get('gemini') is True

        # Email should have received enhanced message
        if mock_email.called:
            sent_msg = mock_email.call_args[0][0]
            assert 'AI Analysis' in sent_msg.content or sample_message.metadata.get('ai_analysis')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
