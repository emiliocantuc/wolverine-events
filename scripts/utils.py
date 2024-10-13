import requests
from datetime import datetime

def notify(channel, msg, url):

    headers = {"Tags": "warning,mywolverineevents"}
    if url: headers["Click"] = url

    print(f'Notifying {msg}')
    requests.post(f"https://ntfy.sh/{channel}", data = msg.encode('utf-8'))



day_of_week = lambda datetime_str: datetime.strptime(datetime_str, '%Y%m%dT%H%M%S').strftime('%A')
gget = lambda e, k, v: e.get(k, None) if e.get(k, None) is not None else v

def stringify(e):
    limit = lambda s, n: s if len(s) < n else s[:n-3] + '...'
    sponsors = [gget(s, 'group_name', '') for s in gget(e, 'sponsors', {})]
    o = [
        f"{e['event_type']}:{limit(gget(e, 'combined_title', ''), 200)}",
        f"{limit(gget(e, 'description', ''), 800)}",
        f"Where:{e['location_name']}",
        f"When:{day_of_week(e['datetime_start'])} {e['time_start'].split(':')[0]}",
    ]
    if sponsors: o.append(f"Sponsors:{', '.join(sponsors)}")
    return '\n'.join(o)