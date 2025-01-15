import requests
import os


def send_pushover_message(message, title=None, url=None, url_title=None, attachment=None, priority=None, sound=None):
    url = 'https://api.pushover.net/1/messages.json'
    data = {
        'token': os.getenv('pushover_token'),
        'user': os.getenv('pushover_userkey'),
        'message': message,
    }

    # Optional parameters
    if title:
        data['title'] = title
    if url:
        data['url'] = url
    if url_title:
        data['url_title'] = url_title
    if priority:
        data['priority'] = priority
    if sound:
        data['sound'] = sound
    # File attachment handling
    files = {}
    if attachment:
        files['attachment'] = (attachment, open(attachment, 'rb'))
    response = requests.post(url, data=data, files=files if files else None)
    return response.json()




