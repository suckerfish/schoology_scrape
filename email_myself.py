import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_to_myself(receiver_email, subject, body):
    sender_email = "cyncial@gmail.com"
    receiver_email = "cynical@gmail.com"
    password = "cwvostfpjsoqlkgo"

    # Create the email
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Send the email
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender_email, password)
    server.sendmail(sender_email, receiver_email, msg.as_string())
    server.quit()

# Call the function to send the email
send_email_to_myself("cynical@gmail.com", "Test Email", "This is a test email sent to myself.")
