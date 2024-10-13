# Fetches events from umich API, saves then to events table and updates statistics table
# Mean to be ran weekly (fetches from weekly endpoint by default)

import sqlite3, requests, argparse, os
from datetime import datetime
import utils

def get_events(url):
    """Gets the events from the url and returns them as a list of dictionaries"""

    assert 'umich.edu' in url, 'The url must be from the umich events page'
    assert 'json' in url, 'The url must be the JSON version of the events page'

    r = requests.get(url)
    try:
        return r.json()
    except:
        raise Exception('Could not parse events from the url. Make sure its the JSON version of the events page.')

def get_cal_links(events_json):

    for event in events_json:
        try:
            permalink = event['permalink']
            html = requests.get(permalink).text
            gcal = html.split('googleCal_href": "')[1].split('"')[0]
            event['gcal_link'] = gcal
        except: pass

def insert_event(cursor, event):
    cursor.execute('''
    INSERT INTO events (nweek, title, event_description, event_start, event_end, type, permalink, building_name, building_id, gcal_link, umich_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        event.get('nweek'),
        event.get('combined_title'),
        event.get('description'),
        event.get('datetime_start'),
        event.get('datetime_end'),
        event.get('event_type'),
        event.get('permalink'),
        event.get('building_name'),
        event.get('building_official_id'),
        event.get('gcal_link'),
        event.get('id')
    ))

def convert_to_sql_datetime(custom_datetime_str):
    """Converts a custom datetime string of endpoint to a SQL datetime string"""
    input_format = "%Y%m%dT%H%M%S"
    dt = datetime.strptime(custom_datetime_str, input_format)
    output_format = "%Y-%m-%d %H:%M:%S"
    sql_datetime_str = dt.strftime(output_format)   
    return sql_datetime_str


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description = 'Fetches events from umich API, saves then to events table and updates statistics table')
    parser.add_argument('--eventsURL', type = str, help = 'Events json endpoint', default = 'https://events.umich.edu/week/json?v=2', required = False)
    parser.add_argument('--output', type = str, help = 'Output db file to save the events', default = 'data/main.db', required = False)
    parser.add_argument('--notify', type = str, help = 'ntfy to notify status to if not empty', default = '', required = False)
    args = parser.parse_args()

    # Check if output db exists
    assert os.path.exists(os.path.dirname(args.output)), 'The output db does not exist'
    
    events = get_events(args.eventsURL)
    print(f'Found {len(events)} events. Getting calendar links ... ', end = '')
    get_cal_links(events) # TODO what if this fails
    print('Done')

    print('Inserting events in db ... ', end = '')
    conn = sqlite3.connect(args.output)
    cursor = conn.cursor()

    try:
        cursor.execute('BEGIN TRANSACTION;')

        # Get the week number
        cursor.execute('SELECT MAX(nweek) FROM events;')
        max_nweek = cursor.fetchone()[0] or 0 
        nweek = max_nweek + 1
        print(f'nweek = {nweek} ', end = '')

        # Insert events
        for event in events:
            event['nweek'] = nweek
            event['datetime_start'] = convert_to_sql_datetime(event['datetime_start'])
            try:
                event['datetime_end'] = convert_to_sql_datetime(event['datetime_end'])
            except:
                event['datetime_end'] = ''

            insert_event(conn, event)

        # Get the number of users
        cursor.execute('SELECT COUNT(*) FROM users;')
        nusers = cursor.fetchone()[0]
        print(f'nusers = {nusers} ', end='')


        # Insert into the statistics table
        cursor.execute('''
            INSERT INTO statistics (nweek, nusers, nevents)
            VALUES (?, ?, ?);
        ''', (nweek, nusers, len(events)))

        conn.commit()
        print('Committed')
        if args.notify: utils.notify(args.notify, f'Successfully scrapped {len(events)} events for week {nweek}', args.eventsURL)

    except Exception as e:
        conn.rollback()
        print('Error saving events:', e)
        if args.notify: utils.notify(args.notify, f'Error scrapping events: {e}', args.eventsURL)
        exit(1)
    
    finally:
        conn.close()
    