import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any
import os
from .base import NotificationProvider, NotificationMessage

class EmailProvider(NotificationProvider):
    """Email notification provider"""
    
    @property
    def provider_name(self) -> str:
        return "email"
    
    def validate_config(self) -> bool:
        """Validate email configuration"""
        required_keys = ['smtp_server', 'smtp_port', 'sender_email', 'sender_password', 'receiver_email']
        return all(key in self.config for key in required_keys)
    
    def is_available(self) -> bool:
        """Check if email is available"""
        return self.validate_config()
    
    def send(self, message: NotificationMessage) -> bool:
        """Send notification via email"""
        if not self.is_available():
            self.logger.error("Email provider not properly configured")
            return False
        
        try:
            # Create the container email message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.config['sender_email']
            msg['To'] = self.config['receiver_email']
            msg['Subject'] = message.title or "Notification"
            
            # Create HTML version of the message
            html_body = message.content.replace('\n', '<br>')
            
            # Add URL if provided
            if message.url:
                url_text = message.url_title or message.url
                html_body += f'<br><br><a href="{message.url}">{url_text}</a>'
                message.content += f'\n\n{url_text}: {message.url}'
            
            # Create both plain text and HTML parts
            text_part = MIMEText(message.content, 'plain')
            html_part = MIMEText(html_body, 'html')
            
            # Attach parts in order: plain text first, then HTML
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Handle file attachment
            if message.attachment and os.path.exists(message.attachment):
                with open(message.attachment, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {os.path.basename(message.attachment)}',
                )
                msg.attach(part)
            
            # Send the email
            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            server.starttls()
            server.login(self.config['sender_email'], self.config['sender_password'])
            server.sendmail(self.config['sender_email'], self.config['receiver_email'], msg.as_string())
            server.quit()
            
            self.logger.info("Email notification sent successfully")
            return True
            
        except smtplib.SMTPException as e:
            self.logger.error(f"SMTP error sending email notification: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending email notification: {e}")
            return False