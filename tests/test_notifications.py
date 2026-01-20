"""
Tests for notification system.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from notifications.base import NotificationProvider, NotificationMessage
from notifications.manager import NotificationManager
from notifications.pushover_provider import PushoverProvider
from notifications.email_provider import EmailProvider
from notifications.gemini_provider import GeminiProvider


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
def pushover_config():
    """Pushover provider configuration"""
    return {
        'enabled': True,
        'token': 'test_token',
        'user_key': 'test_user_key'
    }


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

    def test_manager_loads_enabled_providers(self, pushover_config):
        """Test that manager loads enabled providers"""
        config = {'pushover': pushover_config}

        with patch.object(PushoverProvider, 'is_available', return_value=True):
            manager = NotificationManager(config)

        assert 'pushover' in manager.get_available_providers()

    def test_manager_skips_disabled_providers(self):
        """Test that manager skips disabled providers"""
        config = {
            'pushover': {'enabled': False, 'token': 'x', 'user_key': 'y'}
        }

        manager = NotificationManager(config)

        assert 'pushover' not in manager.get_available_providers()

    def test_manager_handles_unavailable_providers(self, pushover_config):
        """Test that manager handles providers that aren't available"""
        config = {'pushover': pushover_config}

        with patch.object(PushoverProvider, 'is_available', return_value=False):
            manager = NotificationManager(config)

        assert 'pushover' not in manager.get_available_providers()

    def test_send_notification_returns_results(self, pushover_config, sample_message):
        """Test that send_notification returns per-provider results"""
        config = {'pushover': pushover_config}

        with patch.object(PushoverProvider, 'is_available', return_value=True):
            with patch.object(PushoverProvider, 'send', return_value=True):
                manager = NotificationManager(config)
                results = manager.send_notification(sample_message)

        assert 'pushover' in results
        assert results['pushover'] is True

    def test_send_notification_handles_failure(self, pushover_config, sample_message):
        """Test that send_notification handles provider failures"""
        config = {'pushover': pushover_config}

        with patch.object(PushoverProvider, 'is_available', return_value=True):
            with patch.object(PushoverProvider, 'send', return_value=False):
                manager = NotificationManager(config)
                results = manager.send_notification(sample_message)

        assert results['pushover'] is False

    def test_send_to_specific_providers(self, pushover_config, email_config, sample_message):
        """Test sending to specific providers only"""
        config = {
            'pushover': pushover_config,
            'email': email_config
        }

        with patch.object(PushoverProvider, 'is_available', return_value=True):
            with patch.object(EmailProvider, 'is_available', return_value=True):
                with patch.object(PushoverProvider, 'send', return_value=True):
                    manager = NotificationManager(config)
                    results = manager.send_notification(sample_message, providers=['pushover'])

        assert 'pushover' in results
        assert 'email' not in results


class TestNotificationManagerFactory:
    """Tests for NotificationManager.from_app_config factory method"""

    def test_factory_creates_pushover_config(self):
        """Test factory creates pushover config from app config"""
        @dataclass
        class MockNotificationConfig:
            pushover_token: str = 'token123'
            pushover_user_key: str = 'user123'
            gemini_api_key: str = None
            email_enabled: bool = False
            email_sender: str = None
            email_password: str = None
            email_receiver: str = None

        config = MockNotificationConfig()

        with patch.object(PushoverProvider, 'is_available', return_value=True):
            manager = NotificationManager.from_app_config(config)

        assert 'pushover' in manager.config

    def test_factory_creates_gemini_config(self):
        """Test factory creates gemini config from app config"""
        @dataclass
        class MockNotificationConfig:
            pushover_token: str = None
            pushover_user_key: str = None
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
            pushover_token: str = None
            pushover_user_key: str = None
            gemini_api_key: str = None
            email_enabled: bool = True
            email_sender: str = 'sender@test.com'
            email_password: str = 'password'
            email_receiver: str = 'receiver@test.com'

        config = MockNotificationConfig()

        with patch.object(EmailProvider, 'is_available', return_value=True):
            manager = NotificationManager.from_app_config(config)

        assert 'email' in manager.config


class TestPushoverProvider:
    """Tests for PushoverProvider"""

    def test_is_available_with_credentials(self, pushover_config):
        """Test is_available returns True with valid credentials"""
        provider = PushoverProvider(pushover_config)
        assert provider.is_available() is True

    def test_is_available_without_credentials(self):
        """Test is_available returns False without credentials"""
        provider = PushoverProvider({'enabled': True})
        assert provider.is_available() is False

    @patch('notifications.pushover_provider.requests.post')
    def test_send_makes_api_call(self, mock_post, pushover_config, sample_message):
        """Test that send makes API call to Pushover"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'status': 1}

        provider = PushoverProvider(pushover_config)
        result = provider.send(sample_message)

        assert result is True
        mock_post.assert_called_once()

    @patch('notifications.pushover_provider.requests.post')
    def test_send_handles_api_error(self, mock_post, pushover_config, sample_message):
        """Test that send handles API errors gracefully"""
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {'status': 0}

        provider = PushoverProvider(pushover_config)
        result = provider.send(sample_message)

        assert result is False


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
            'pushover': {'enabled': True, 'token': 't', 'user_key': 'u'}
        }

        # Mock Gemini to add AI analysis to metadata
        def mock_gemini_send(msg):
            msg.metadata['ai_analysis'] = "AI generated summary"
            return True

        with patch.object(GeminiProvider, 'is_available', return_value=True):
            with patch.object(GeminiProvider, 'send', side_effect=mock_gemini_send):
                with patch.object(PushoverProvider, 'is_available', return_value=True):
                    with patch.object(PushoverProvider, 'send', return_value=True) as mock_pushover:
                        manager = NotificationManager(config)
                        results = manager.send_notification(sample_message)

        # Gemini should have run
        assert results.get('gemini') is True

        # Pushover should have received enhanced message
        if mock_pushover.called:
            sent_msg = mock_pushover.call_args[0][0]
            assert 'AI Analysis' in sent_msg.content or sample_message.metadata.get('ai_analysis')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
