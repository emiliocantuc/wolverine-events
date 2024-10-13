import requests

def notify(channel, msg, url):

    headers = {"Tags": "warning,mywolverineevents"}
    if url: headers["Click"] = url

    print(f'Notifying {msg}')
    requests.post(f"https://ntfy.sh/{channel}", data = msg.encode('utf-8'))