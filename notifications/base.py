from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

@dataclass
class NotificationMessage:
    """Standardized notification message format"""
    title: str
    content: str
    priority: Optional[str] = "normal"  # low, normal, high, emergency
    url: Optional[str] = None
    url_title: Optional[str] = None
    attachment: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class NotificationProvider(ABC):
    """Abstract base class for notification providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def send(self, message: NotificationMessage) -> bool:
        """
        Send a notification message
        
        Args:
            message: NotificationMessage instance
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the notification provider is properly configured and available
        
        Returns:
            bool: True if available, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Name of the notification provider
        
        Returns:
            str: Provider name
        """
        pass
    
    def validate_config(self) -> bool:
        """
        Validate provider configuration
        
        Returns:
            bool: True if config is valid, False otherwise
        """
        return True
    
    def format_message(self, message: NotificationMessage) -> Dict[str, Any]:
        """
        Format message for this provider's specific requirements
        Override in subclasses if needed
        
        Args:
            message: NotificationMessage instance
            
        Returns:
            dict: Formatted message data
        """
        return {
            'title': message.title,
            'content': message.content,
            'priority': message.priority,
            'url': message.url,
            'url_title': message.url_title,
            'attachment': message.attachment
        }