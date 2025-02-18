import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_to_myself(receiver_email, subject, body):
    sender_email = "cyncial@gmail.com"
    receiver_email = "cynical@gmail.com"
    password = "cwvostfpjsoqlkgo"

    # Create the container email message
    msg = MIMEMultipart('alternative')
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    # Create HTML version of the message
    html_body = body.replace('\n', '<br>')  # Convert newlines to HTML breaks
    
    # Create both plain text and HTML parts
    text_part = MIMEText(body, 'plain')
    html_part = MIMEText(html_body, 'html')
    
    # Attach parts in order: plain text first, then HTML
    msg.attach(text_part)
    msg.attach(html_part)

    # Send the email
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender_email, password)
    server.sendmail(sender_email, receiver_email, msg.as_string())
    server.quit()

if __name__ == "__main__":
    test_subject = "Test Email"
    test_body = """
    Hello,
    
    This is a test email.
    It should have proper formatting.
    
    Best regards,
    Test Script
    """
    
    send_email_to_myself("cynical@gmail.com", test_subject, test_body)


