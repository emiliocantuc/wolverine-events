import os
import numpy as np

from flask import Flask, request, redirect, url_for
from flask import render_template
from flask import g # global session-level object
from flask import session
import sqlite3
from google.oauth2 import id_token
from google.auth.transport import requests

import wevents.db as db_utils
from wevents.utils import format_event, inv_distance_weights

# Rec. params
N_FEATURED = 25
N_PERSONAL = 35
INV_TEMP = 2.0  # inv. temperature of softmax weight calc. (0, inf). higher -> peakier weights
BETA = 0.8      # lerp weight on past user_ratings [0, 1]. higher -> weighs past ratings more

# Sign in stuff
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
if GOOGLE_CLIENT_ID is None: print('WARNING: No google client ID found!')

app = Flask(__name__)

# Secret key to sign cookies and maintain sessions
app.secret_key = os.environ.get('SESSION_SECRET', 'devkey')
if app.secret_key == 'devkey': print('WARNING: no secret key found, using default devkey')

# Database stuff
app.config['DATABASE'] = 'data/main.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types = sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db

def close_db(e = None):
    db = g.pop('db', None)
    if db is not None: db.close()

# Auth
@app.before_request
def load_logged_in_user(): g.user = session.get('user_id', None)

@app.route('/login', methods = ['POST'])
def login():
    try:
        idinfo = id_token.verify_oauth2_token(request.form['credential'], requests.Request(), os.getenv('GOOGLE_CLIENT_ID'))
        user_id, is_new = db_utils.signin_user(get_db(), idinfo['email'])
        session['user_id'] = user_id
        print('singed in ', idinfo['email'], user_id)
    except ValueError as e:
        print('error validating', e)
        return 'Error logging in' 
    return redirect(url_for('prefs' if is_new else 'main'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('main'))


# Main views
@app.route('/', methods = ['GET'])
def main():
    db = get_db()
    
    print('user', g.user)
    featured_events = db_utils.get_top_events(db = db, limit = N_FEATURED, user_id = g.user)
    featured_events = [format_event(e) for e in featured_events]

    # Compute recommended
    recommended_events = None
    try:
        if g.user:

            events = db_utils.get_event_blobs_and_gen_info(db = db)
            ids = np.array([e['id'] for e in events])
            dists_to_centroids = np.array([e['dist_to_clusters'] for e in events])
            weights = inv_distance_weights(dists_to_centroids, inv_temperature = INV_TEMP) # TODO recomputing weights here?

            user_ratings = db_utils.get_ratings(db = db, user_id = g.user)
            preds = weights @ user_ratings

            # Recommend events with highest predicted rating
            rec_ixs = (-preds).argsort()[:N_PERSONAL] # ix in current_events

            recommended_events = db_utils.get_events_by_ids(db = db, event_ids = ids[rec_ixs].tolist(), user_id = g.user)
            recommended_events = [format_event(e) for e in recommended_events]

            for e, og_ix in zip(recommended_events, rec_ixs):
                e['info'] = f'rank: {np.where(rec_ixs == og_ix)[0][0]} pred: {round(preds[og_ix], 6)}'

    except Exception as e: print('error getting recs:', e)

    return render_template(
        'index.html', google_client_id = GOOGLE_CLIENT_ID,
        recommended_events = recommended_events, featured_events = featured_events
    )

@app.route('/vote', methods = ['PUT', 'POST'])
def vote():
    try:
        assert all([k in request.args for k in ('type', 'eventId', 'factor')])
        factor = float(request.args['factor'])
        assert factor in (-1., 1., 2.)
        db = get_db()
        db_utils.vote(db = db, user_id = g.user, event_id = request.args['eventId'], vote_type = request.args['type'])
        db_utils.update_user_ratings(
            db = db, user_id = g.user, event_id = request.args['eventId'],
            update_factor = factor, inv_temperature = INV_TEMP, beta = BETA
        )
        return 'ok'
    except Exception as e:
        print('Error voting: ', e)
        return 'error'

@app.route('/prefs', methods = ['GET', 'PUT', 'DELETE'])
def prefs():
    if not g.user: return 'Please login first'
    
    db = get_db()
    if request.method == 'GET':
        try:
            prefs = db_utils.get_preferences(db = db, user_id = g.user)
            return render_template('prefs.html', prefs = prefs)
        except Exception as e:
            print(f'Error getting preferences: {e}')
            return "An error occurred. Please try again later."
    
    if request.method == 'DELETE':
        try:
            db_utils.delete_user(db = db, user_id = g.user)
            session.pop('user_id', None)
            return 'Successfully deleted account. Close tab to exit.'
        except Exception as e:
            print(f'Error deleting account: {e}')
            return "An error occurred. Please <a href=\"mailto:emilio@mywolverine.events\">email support</a>."
    
    key, value = next(request.form.items())
    db_utils.update_preference(db = db, user_id = g.user, pref_key = key, pref_value = value)
    return 'Saved'

@app.route('/cluster/<id>', methods = ['GET', 'PUT'])
def cluster(id = None):

    if id is None: redirect(url_for('main'))

    db = get_db()
    if request.method == 'GET':
        try:
            events = db_utils.get_events_by_cluster(db = db, cluster_id = id, user_id = g.user)
            events = [format_event(e) for e in events]
            print(len(events))
            return render_template('cluster.html', cluster = id, events = events)
        except Exception as e:
            print(f'Error getting preferences: {e}')
            return "An error occurred. Please try again later."
    
    if request.method == 'PUT':
        pass
    
    return 'ok'

@app.route('/stats', methods = ['GET'])
def stats():

    db = get_db()
    try:
        stats = db_utils.get_stats(db)
        print(stats)
        return render_template('stats.html', stats = stats)
    except Exception as e:
        print(f'Error getting preferences: {e}')
        return "An error occurred. Please try again later."
