import sqlite3, json, time, argparse
import numpy as np
from sklearn.metrics.pairwise import euclidean_distances

import utils

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Fetches events from umich API, saves then to events table and updates statistics table')
    parser.add_argument('--notify', type = str, help = 'ntfy to notify status to if not empty', default = '', required = False)
    parser.add_argument('--oai_key', type = str, help = 'OpenAI key to get embeddings', required = True)
    parser.add_argument('--output_emb', type = str, help = 'Output npy file to save embeddings', default = 'data/current_embs.npy', required = False)
    args = parser.parse_args()

    # Get events from this week (nweek is maximum)
    conn = sqlite3.connect('data/main.db')
    query = '''
    SELECT event_id, umich_id  FROM events
    WHERE nweek = (SELECT MAX(nweek) FROM events)
    '''
    cursor = conn.cursor()
    cursor.execute(query)
    event_ids = cursor.fetchall()
    event_ids = {e[1]: e[0] for e in event_ids} # umich id -> our id
    print(f'Found {len(event_ids)} events')

    # Load current events
    with open('data/current_events.json', 'r') as f:
        events = json.load(f)
        print(f'Loaded {len(events)} events from current_events.json')
    

    # Load centroids
    centroids = np.load('data/centroids.npy')
    
    assert len(events) == len(event_ids), f'Number of events in current_events.json {len(events)} and events table {len(event_ids)} do not match'

    # Get embeddings
    print('Getting embeddings ... ', end = '')
    try:

        # Get embeddings
        to_embed = [utils.stringify_event(e) for e in events]
        embeddings = []
        for i in range(0, len(to_embed), 1000):
            embeddings.extend(utils.get_embedding(to_embed[i:i + 1000], args.oai_key))
            time.sleep(20)
        
        E = np.array([np.array(e) for e in embeddings])
        np.save(args.output_emb, E)
        E = np.load(args.output_emb)
        print('Got embeddings shaped', E.shape)

        # Get distances to centroids
        dists_to_centroids = euclidean_distances(E, centroids)
        print('Got distances to centroids shaped', dists_to_centroids.shape)

        # Clear curr_event_embeddings table
        cursor = conn.cursor()
        cursor.execute('DELETE FROM curr_event_embeddings;')
        print('Cleared curr_event_embeddings table')

        # Insert new embeddings into curr_event_embeddings table
        for event, emb, dists in zip(events, E, dists_to_centroids):
            our_id = event_ids[event['id']]
            cursor.execute('''
            INSERT INTO curr_event_embeddings (event_id, emb, dists_to_clusters)
            VALUES (?, ?, ?)
            ''', (our_id, emb.tobytes(), dists.tobytes()))

        conn.commit()
        print('Inserted new embeddings into curr_event_embeddings table')
    
    except Exception as e:
        print('Error getting embeddings:', e)
        if args.notify: utils.notify(args.notify, f'Error getting embeddings: {e}', args.eventsURL)
        exit(1)