from datetime import datetime
import numpy as np

def format_event(event):

    truncate = lambda s, max_length: s[:max_length] + "..." if len(s) > max_length else s
    clean_string = lambda s, delimiter, to_remove: s.split(delimiter)[0].replace(to_remove, "").strip()

    def format_dt(date_time: str, include_day: bool) -> str:
        if not date_time: return ''
        try:
            date_time = date_time.replace("Z", "")
            format_string = "%Y-%m-%d %H:%M:%S"  # For your input format
            
            t = datetime.strptime(date_time, format_string)

            if include_day: return t.strftime("%A %-I:%M %p")
            else: return t.strftime("%-I:%M %p")
        except ValueError as e:
            print(f"Error formatting date: {date_time}")
            return ""


    # Truncate title and description
    event['Title'] = truncate(event['Title'], 75)
    event['Description'] = truncate(event['Description'], 300)

    # Format EventType and BuildingName
    event_type = clean_string(event['EventType'], "/", "")

    # Format Start Time
    start_time = format_dt(event['StartDate'], True)
    end_time = format_dt(event['EndDate'], False)
    if end_time: start_time += " - " + end_time

    # Construct Subtitle
    event['Subtitle'] = " | ".join([i for i in [event_type, start_time, event['BuildingName']] if i])
    return event

def inv_distance_weights(distances, eps = 1e-5):
    weights = (1 / (distances + eps))
    weights /= weights.sum(axis=1)[:, np.newaxis]
    return weights