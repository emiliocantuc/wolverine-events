import sqlite3, time, argparse, logging, os
import numpy as np
from sklearn.metrics.pairwise import euclidean_distances

import utils

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Fetches events from umich API, saves then to events table and updates statistics table')
    parser.add_argument('--db', type = str, help = 'Path to db file', default = 'data/main.db')
    parser.add_argument('--oai_key', type = str, help = 'OpenAI key to get embeddings')
    parser.add_argument('--output_emb', type = str, help = 'Output npy file to save embeddings', default = 'data/embeddings.npy', required = False)
    parser.add_argument('--notify', type = str, help = 'ntfy topic to notify status to if not empty', default = '', required = False)
    args = parser.parse_args()

    OAI_KEY = os.getenv('OAI_KEY', args.oai_key if args.oai_key else None)
    if not OAI_KEY:
        logging.error('OpenAI key is not set. Please provide it via --oai_key or set OAI_KEY environment variable.')
        exit(1)

    logging.basicConfig(level = logging.INFO, format = '%(asctime)s - %(levelname)s - %(message)s')

    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    cursor.execute('SELECT event_id, to_embed from events;')
    ids, to_embed = zip(*cursor.fetchall())
    logging.info(f'Embedding {len(to_embed)} events')

    try:
        # Get embeddings from OAI
        logging.info('Getting embeddings ... ')
        embeddings = []
        for i in range(0, len(to_embed), 1000):
            embeddings.extend(utils.get_embedding(to_embed[i:i + 1000], OAI_KEY))
            time.sleep(20)
        
        E = np.array([np.array(e) for e in embeddings])
        np.save(args.output_emb, E)
        E = np.load(args.output_emb)
        logging.info(f'Got embeddings shaped: {E.shape}')


        # Insert new embeddings into events table
        for id, emb in zip(ids, E):
            cursor.execute('UPDATE events SET emb = ? WHERE event_id = ?', (emb.tobytes(), id))

        conn.commit()
        logging.info('Inserted new embeddings into events table')
    
    except Exception as e:
        logging.error(f'Error getting embeddings: {e}')
        if args.notify: utils.notify(args.notify, f'Error getting embeddings: {e}', args.eventsURL)
        exit(1)