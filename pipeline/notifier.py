import logging
from typing import Dict, Any, Optional, List
from notifications.manager import NotificationManager
from notifications.base import NotificationMessage
from shared.config import get_config

class GradeNotifier:
    """Handles alert coordination and notification delivery"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = get_config()
        self.notification_manager = self._initialize_notification_manager()
    
    def _initialize_notification_manager(self) -> Optional[NotificationManager]:
        """Initialize the notification manager with configuration"""
        try:
            # Build notification configuration from app config
            notification_config = {}
            
            # Pushover configuration
            if self.config.notifications.pushover_token and self.config.notifications.pushover_user_key:
                notification_config['pushover'] = {
                    'enabled': True,
                    'token': self.config.notifications.pushover_token,
                    'user_key': self.config.notifications.pushover_user_key
                }
            
            # Email configuration
            if self.config.notifications.email_enabled:
                notification_config['email'] = {
                    'enabled': True,
                    'smtp_server': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'sender_email': 'cyncial@gmail.com',
                    'sender_password': 'cwvostfpjsoqlkgo',  # App password
                    'receiver_email': 'cynical@gmail.com'
                }
            
            # Gemini configuration
            if self.config.notifications.gemini_api_key:
                notification_config['gemini'] = {
                    'enabled': True,
                    'api_key': self.config.notifications.gemini_api_key
                }
            
            if notification_config:
                manager = NotificationManager(notification_config)
                self.logger.info(f"Notification manager initialized with providers: {manager.get_available_providers()}")
                return manager
            else:
                self.logger.warning("No notification providers configured")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to initialize notification manager: {e}")
            return None
    
    def send_grade_change_notification(self, changes: Dict[str, Any], formatted_message: str) -> tuple[bool, Dict[str, bool]]:
        """
        Send notification about grade changes
        
        Args:
            changes: Raw change data from comparator
            formatted_message: Human-readable message

        Returns:
            tuple: (success_bool, results_dict) where success_bool is True if at least one
                   notification was sent successfully, and results_dict contains per-provider results
        """
        if not self.notification_manager:
            self.logger.warning("No notification manager available")
            return False, {}
        
        try:
            # Prepare metadata for AI analysis
            metadata = {
                'grade_changes': changes,
                'timestamp': changes.get('timestamp'),
                'change_type': changes.get('type', 'unknown')
            }
            
            # Create notification message
            message = NotificationMessage(
                title="Schoology Grade Changes Detected",
                content=formatted_message,
                priority=self._determine_priority(changes),
                metadata=metadata
            )
            
            # Send notification through all available providers
            results = self.notification_manager.send_notification(message)
            
            # Log results
            successful_providers = [provider for provider, success in results.items() if success]
            failed_providers = [provider for provider, success in results.items() if not success]
            
            if successful_providers:
                self.logger.info(f"Notifications sent successfully via: {', '.join(successful_providers)}")
            
            if failed_providers:
                self.logger.warning(f"Notifications failed via: {', '.join(failed_providers)}")
            
            return len(successful_providers) > 0, results

        except Exception as e:
            self.logger.error(f"Error sending grade change notification: {e}")
            return False, {}
    
    def send_error_notification(self, error_message: str, error_details: Optional[str] = None) -> bool:
        """
        Send notification about system errors
        
        Args:
            error_message: Brief error description
            error_details: Detailed error information
            
        Returns:
            bool: True if at least one notification was sent successfully
        """
        if not self.notification_manager:
            self.logger.warning("No notification manager available for error notification")
            return False
        
        try:
            content = f"Error in Schoology grade scraper: {error_message}"
            if error_details:
                content += f"\n\nDetails:\n{error_details}"
            
            message = NotificationMessage(
                title="Schoology Scraper Error",
                content=content,
                priority="high"
            )
            
            # Send only to critical notification providers (exclude Gemini for errors)
            critical_providers = [p for p in self.notification_manager.get_available_providers() 
                                if p != 'gemini']
            
            results = self.notification_manager.send_notification(message, providers=critical_providers)
            
            successful_providers = [provider for provider, success in results.items() if success]
            
            if successful_providers:
                self.logger.info(f"Error notifications sent via: {', '.join(successful_providers)}")
                return True
            else:
                self.logger.error("Failed to send error notifications via any provider")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending error notification: {e}")
            return False
    
    def send_status_notification(self, status_message: str, success: bool = True) -> bool:
        """
        Send notification about system status
        
        Args:
            status_message: Status message
            success: Whether this is a success or failure status
            
        Returns:
            bool: True if at least one notification was sent successfully
        """
        if not self.notification_manager:
            return False
        
        try:
            message = NotificationMessage(
                title=f"Schoology Scraper {'Success' if success else 'Status'}",
                content=status_message,
                priority="low" if success else "normal"
            )
            
            # For status notifications, use only basic providers
            basic_providers = [p for p in self.notification_manager.get_available_providers() 
                             if p in ['pushover', 'email']]
            
            results = self.notification_manager.send_notification(message, providers=basic_providers)
            
            return any(results.values())
            
        except Exception as e:
            self.logger.error(f"Error sending status notification: {e}")
            return False
    
    def _determine_priority(self, changes: Dict[str, Any]) -> str:
        """
        Determine notification priority based on the type and scale of changes
        
        Args:
            changes: Change data from comparator
            
        Returns:
            Priority level: 'low', 'normal', 'high', 'emergency'
        """
        if changes.get('type') == 'initial':
            return 'low'
        
        # Count the number of changes
        detailed_changes = changes.get('detailed_changes', [])
        change_count = len(detailed_changes)
        
        # Check for grade-related changes (more important)
        grade_related_changes = 0
        for change in detailed_changes:
            path = change.get('path', '')
            if any(keyword in path.lower() for keyword in ['grade', 'score', 'points']):
                grade_related_changes += 1
        
        # Determine priority
        if grade_related_changes > 5:
            return 'high'
        elif grade_related_changes > 0:
            return 'normal'
        elif change_count > 10:
            return 'normal'
        else:
            return 'low'
    
    def test_notifications(self) -> Dict[str, bool]:
        """
        Test all notification providers
        
        Returns:
            Dict mapping provider names to test results
        """
        if not self.notification_manager:
            return {}
        
        return self.notification_manager.test_providers()
    
    def get_available_providers(self) -> List[str]:
        """Get list of available notification providers"""
        if not self.notification_manager:
            return []
        
        return self.notification_manager.get_available_providers()