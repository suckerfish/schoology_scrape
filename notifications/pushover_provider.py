import requests
from typing import Dict, Any
from .base import NotificationProvider, NotificationMessage

class PushoverProvider(NotificationProvider):
    """Pushover notification provider"""
    
    @property
    def provider_name(self) -> str:
        return "pushover"
    
    def validate_config(self) -> bool:
        """Validate Pushover configuration"""
        required_keys = ['token', 'user_key']
        return all(key in self.config for key in required_keys)
    
    def is_available(self) -> bool:
        """Check if Pushover is available"""
        return self.validate_config() and bool(self.config.get('token')) and bool(self.config.get('user_key'))
    
    def send(self, message: NotificationMessage) -> bool:
        """Send notification via Pushover"""
        if not self.is_available():
            self.logger.error("Pushover provider not properly configured")
            return False
        
        try:
            url = 'https://api.pushover.net/1/messages.json'
            data = {
                'token': self.config['token'],
                'user': self.config['user_key'],
                'message': message.content,
            }
            
            # Optional parameters
            if message.title:
                data['title'] = message.title
            if message.url:
                data['url'] = message.url
            if message.url_title:
                data['url_title'] = message.url_title
            if message.priority:
                # Map our priority levels to Pushover's priority system
                priority_map = {
                    'low': -2,
                    'normal': 0,
                    'high': 1,
                    'emergency': 2
                }
                data['priority'] = priority_map.get(message.priority, 0)
            
            # File attachment handling
            files = {}
            if message.attachment:
                files['attachment'] = (message.attachment, open(message.attachment, 'rb'))
            
            response = requests.post(url, data=data, files=files if files else None)
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 1:
                self.logger.info("Pushover notification sent successfully")
                return True
            else:
                self.logger.error(f"Pushover notification failed: {result}")
                return False
                
        except requests.RequestException as e:
            self.logger.error(f"Failed to send Pushover notification: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending Pushover notification: {e}")
            return False
        finally:
            # Close file if it was opened
            if message.attachment and 'attachment' in files:
                files['attachment'][1].close()