import html
import smtplib
from collections import defaultdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Any
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
            # Parse multiple recipients (comma-separated)
            recipient_emails = [email.strip() for email in self.config['receiver_email'].split(',')]

            # Create the container email message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.config['sender_email']
            msg['To'] = ', '.join(recipient_emails)
            msg['Subject'] = message.title or "Notification"

            # Build HTML body
            html_body = self._build_html(message)

            # Add URL if provided
            plain_content = message.content
            if message.url:
                url_text = message.url_title or message.url
                html_body += f'<br><br><a href="{self._esc(message.url)}">{self._esc(url_text)}</a>'
                plain_content += f'\n\n{url_text}: {message.url}'

            # Create both plain text and HTML parts
            text_part = MIMEText(plain_content, 'plain')
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
            server.sendmail(self.config['sender_email'], recipient_emails, msg.as_string())
            server.quit()

            self.logger.info(f"Email notification sent successfully to {len(recipient_emails)} recipients")
            return True

        except smtplib.SMTPException as e:
            self.logger.error(f"SMTP error sending email notification: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending email notification: {e}")
            return False

    @staticmethod
    def _esc(text: str) -> str:
        """HTML-escape a string"""
        return html.escape(str(text)) if text else ""

    @staticmethod
    def _html_head() -> str:
        """Return HTML head with inline styles for email"""
        return (
            '<!DOCTYPE html><html><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '</head>'
            '<body style="margin:0;padding:16px;font-family:-apple-system,Helvetica,Arial,sans-serif;'
            'font-size:14px;line-height:1.5;color:#1a1a1a;background:#f9f9f9;">'
            '<div style="max-width:600px;margin:0 auto;background:#fff;'
            'border-radius:8px;padding:20px;border:1px solid #e0e0e0;">'
        )

    @staticmethod
    def _html_tail() -> str:
        """Return HTML closing tags"""
        return '</div></body></html>'

    def _render_change_html(self, change: Any) -> str:
        """Render a single GradeChange as an HTML line"""
        esc = self._esc
        if change.change_type == "new_assignment":
            grade = esc(change.new_grade)
            pct = change.percentage()
            pct_str = ""
            if pct is not None:
                letter = change.letter_grade(pct)
                pct_str = (
                    f' <span style="color:#888;">({pct:.0f}% {letter})</span>'
                )
            return (
                f'<div style="margin:2px 0 2px 48px;">'
                f'<span style="color:#2e7d32;">New:</span> '
                f'{esc(change.assignment_title)} = {grade}{pct_str}'
                f'</div>'
            )
        elif change.change_type == "grade_updated":
            old_grade = esc(change.old_grade)
            new_grade = esc(change.new_grade)
            old_pct = change.old_percentage()
            new_pct = change.percentage()
            old_pct_str = ""
            new_pct_str = ""
            if old_pct is not None:
                old_letter = change.letter_grade(old_pct)
                old_pct_str = f' ({old_pct:.0f}%)'
            if new_pct is not None:
                new_letter = change.letter_grade(new_pct)
                new_pct_str = (
                    f' <span style="color:#888;">({new_pct:.0f}% {new_letter})</span>'
                )
            return (
                f'<div style="margin:2px 0 2px 48px;">'
                f'{esc(change.assignment_title)}: '
                f'{old_grade}{old_pct_str} &rarr; {new_grade}{new_pct_str}'
                f'</div>'
            )
        elif change.change_type == "comment_updated":
            return (
                f'<div style="margin:2px 0 2px 48px;">'
                f'{esc(change.assignment_title)}: '
                f'<span style="color:#888;">Comment updated</span>'
                f'</div>'
            )
        return (
            f'<div style="margin:2px 0 2px 48px;">'
            f'{esc(change.assignment_title)}: Changed'
            f'</div>'
        )

    def _plain_to_html(self, content: str) -> str:
        """Convert plain text content to basic HTML"""
        return self._html_head() + self._esc(content).replace('\n', '<br>') + self._html_tail()

    def _build_html(self, message: NotificationMessage) -> str:
        """Build styled HTML email from notification message"""
        # Try to get GradeChange objects from metadata
        change_objects = None
        if message.metadata and 'grade_changes' in message.metadata:
            grade_changes = message.metadata['grade_changes']
            if isinstance(grade_changes, dict):
                change_objects = grade_changes.get('change_objects')

        if not change_objects:
            return self._plain_to_html(message.content)

        esc = self._esc
        parts = [self._html_head()]

        # Title
        parts.append(
            f'<h2 style="margin:0 0 12px;font-size:18px;font-weight:600;">'
            f'{esc(message.title or "Grade Changes Detected")}</h2>'
        )

        # Summary line
        summary_line = message.content.split('\n')[0] if message.content else ""
        if summary_line:
            parts.append(
                f'<p style="margin:0 0 16px;color:#555;">{esc(summary_line)}</p>'
            )

        # Group changes: section -> period -> category
        tree: dict[str, dict[str, dict[str, list]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
        for change in change_objects:
            tree[change.section_name][change.period_name][change.category_name].append(change)

        for section_name, periods in tree.items():
            # Section header
            parts.append(
                f'<div style="font-weight:700;font-size:15px;margin:14px 0 4px;'
                f'padding-bottom:4px;border-bottom:1px solid #e0e0e0;">'
                f'{esc(section_name)}</div>'
            )
            for period_name, categories in periods.items():
                # Period
                parts.append(
                    f'<div style="margin:4px 0 2px 12px;font-weight:500;color:#555;">'
                    f'{esc(period_name)}</div>'
                )
                for category_name, changes in categories.items():
                    # Category
                    parts.append(
                        f'<div style="margin:2px 0 2px 28px;font-size:12px;color:#888;'
                        f'text-transform:uppercase;letter-spacing:0.5px;">'
                        f'{esc(category_name)}</div>'
                    )
                    for change in changes:
                        parts.append(self._render_change_html(change))

        # AI Analysis section (appended to content by notification manager)
        ai_separator = "--- AI Analysis ---"
        if ai_separator in message.content:
            ai_text = message.content.split(ai_separator, 1)[1].strip()
            parts.append(
                f'<div style="margin-top:20px;padding-top:12px;border-top:1px solid #e0e0e0;">'
                f'<div style="font-weight:600;margin-bottom:6px;">AI Analysis</div>'
                f'<div style="color:#444;">{esc(ai_text).replace(chr(10), "<br>")}</div>'
                f'</div>'
            )

        parts.append(self._html_tail())
        return ''.join(parts)
