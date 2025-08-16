import requests


def send_pushover_message(app_token, user_key, message, title=None, url=None, url_title=None, attachment=None, priority=None, sound=None):
    url = 'https://api.pushover.net/1/messages.json'
    data = {
        'token': app_token,
        'user': user_key,
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

# Example usage
app_token = 'apptoken'  # Replace with your app's API token
user_key = 'userkey'   # Replace with your user/group key
message = 'Hello from Python!'    # Your message content
attachment = 'screenshot.png'

# Call the function with attachment
response = send_pushover_message(app_token, user_key, message, attachment=attachment)
print(response)