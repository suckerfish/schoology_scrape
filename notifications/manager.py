import logging
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from shared.config import NotificationConfig

from .base import NotificationProvider, NotificationMessage
from .email_provider import EmailProvider
from .gemini_provider import GeminiProvider


class NotificationManager:
    """Central notification manager with plugin loading and orchestration"""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.providers: dict[str, NotificationProvider] = {}
        self._load_providers()

    @classmethod
    def from_app_config(cls, notification_config: "NotificationConfig") -> "NotificationManager":
        """
        Create NotificationManager from app NotificationConfig.

        This factory method handles the translation from the centralized
        config format to the provider-specific format.

        Args:
            notification_config: NotificationConfig from shared.config

        Returns:
            Configured NotificationManager instance
        """
        config: dict[str, Any] = {}

        # Email configuration
        if (notification_config.email_enabled and
            notification_config.email_sender and
            notification_config.email_password and
            notification_config.email_receiver):
            config['email'] = {
                'enabled': True,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'sender_email': notification_config.email_sender,
                'sender_password': notification_config.email_password,
                'receiver_email': notification_config.email_receiver
            }

        # Gemini configuration
        if notification_config.gemini_api_key:
            config['gemini'] = {
                'enabled': True,
                'api_key': notification_config.gemini_api_key
            }

        return cls(config)
    
    def _load_providers(self):
        """Load and initialize notification providers based on configuration"""
        provider_classes = {
            'email': EmailProvider,
            'gemini': GeminiProvider
        }
        
        for provider_name, provider_class in provider_classes.items():
            try:
                provider_config = self.config.get(provider_name, {})
                if provider_config.get('enabled', False):
                    provider = provider_class(provider_config)
                    if provider.is_available():
                        self.providers[provider_name] = provider
                        self.logger.info(f"Loaded notification provider: {provider_name}")
                    else:
                        self.logger.warning(f"Provider {provider_name} is not available (configuration issue)")
                else:
                    self.logger.debug(f"Provider {provider_name} is disabled")
            except Exception as e:
                self.logger.error(f"Failed to load provider {provider_name}: {e}")
    
    def send_notification(self, message: NotificationMessage, providers: Optional[list[str]] = None) -> dict[str, bool]:
        """
        Send notification through specified providers or all available providers

        Args:
            message: NotificationMessage to send
            providers: List of provider names to use (None = all available)

        Returns:
            dict mapping provider names to success status
        """
        if providers is None:
            providers = list(self.providers.keys())
        
        results = {}
        
        # Special handling for Gemini - run it first to generate analysis
        if 'gemini' in providers and 'gemini' in self.providers:
            try:
                gemini_success = self.providers['gemini'].send(message)
                results['gemini'] = gemini_success
                
                # If Gemini generated analysis, enhance the message for other providers
                if gemini_success and message.metadata and 'ai_analysis' in message.metadata:
                    enhanced_content = f"{message.content}\n\n--- AI Analysis ---\n{message.metadata['ai_analysis']}"
                    message = NotificationMessage(
                        title=message.title,
                        content=enhanced_content,
                        priority=message.priority,
                        url=message.url,
                        url_title=message.url_title,
                        attachment=message.attachment,
                        metadata=message.metadata
                    )
                
                # Remove gemini from the remaining providers list
                providers = [p for p in providers if p != 'gemini']
                
            except Exception as e:
                self.logger.error(f"Error with Gemini provider: {e}")
                results['gemini'] = False
        
        # Send through remaining providers
        for provider_name in providers:
            if provider_name in self.providers:
                try:
                    success = self.providers[provider_name].send(message)
                    results[provider_name] = success
                    self.logger.info(f"Notification sent via {provider_name}: {'Success' if success else 'Failed'}")
                except Exception as e:
                    self.logger.error(f"Error sending notification via {provider_name}: {e}")
                    results[provider_name] = False
            else:
                self.logger.warning(f"Provider {provider_name} not available")
                results[provider_name] = False
        
        return results
    
    def get_available_providers(self) -> list[str]:
        """Get list of available provider names"""
        return list(self.providers.keys())
