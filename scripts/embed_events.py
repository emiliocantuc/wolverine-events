import sqlite3, time, argparse, logging
import numpy as np
from sklearn.metrics.pairwise import euclidean_distances

import utils

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Fetches events from umich API, saves then to events table and updates statistics table')
    parser.add_argument('--db', type = str, help = 'Path to db file', default = 'data/main.db')
    parser.add_argument('--centroids', type = str, help = 'Path centroids npy file', default = 'data/centroids.npy')
    parser.add_argument('--oai_key', type = str, help = 'OpenAI key to get embeddings', required = True)
    parser.add_argument('--output_emb', type = str, help = 'Output npy file to save embeddings', default = 'data/embeddings.npy', required = False)
    parser.add_argument('--notify', type = str, help = 'ntfy topic to notify status to if not empty', default = '', required = False)
    args = parser.parse_args()
    logging.basicConfig(level = logging.INFO, format = '%(asctime)s - %(levelname)s - %(message)s')

    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    cursor.execute('SELECT event_id, to_embed from events;')
    ids, to_embed = zip(*cursor.fetchall())
    logging.info(f'Embedding {len(to_embed)} events')

    # Load centroids
    centroids = np.load(args.centroids)
    
    try:
        # Get embeddings from OAI
        logging.info('Getting embeddings ... ')
        embeddings = []
        for i in range(0, len(to_embed), 1000):
            embeddings.extend(utils.get_embedding(to_embed[i:i + 1000], args.oai_key))
            time.sleep(20)
        
        E = np.array([np.array(e) for e in embeddings])
        np.save(args.output_emb, E)
        E = np.load(args.output_emb)
        logging.info(f'Got embeddings shaped: {E.shape}')

        # Get distances to centroids
        dists_to_centroids = euclidean_distances(E, centroids)
        logging.info(f'Got distances to centroids shaped: {dists_to_centroids.shape}')

        # Insert new embeddings into events table
        for id, emb, dists in zip(ids, E, dists_to_centroids):
            closest_cluster = int(dists.argmax())
            cursor.execute('UPDATE events SET emb = ?, dists_to_clusters = ?, cluster = ? WHERE event_id = ?', (emb.tobytes(), dists.tobytes(), closest_cluster, id))

        conn.commit()
        logging.info('Inserted new embeddings into curr_event_embeddings table')
    
    except Exception as e:
        logging.error(f'Error getting embeddings: {e}')
        if args.notify: utils.notify(args.notify, f'Error getting embeddings: {e}', args.eventsURL)
        exit(1)