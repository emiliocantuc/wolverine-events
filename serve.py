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
from wevents.utils import format_event, filter_events_by_keywords, str_err

# Rec. params
N_FEATURED = 10
N_PERSONAL = 35
EMB_DIM = 1536

# Other
MAX_INTERESTS = 10
MAX_INTEREST_LEN = 20
MAX_DAILY_INTEREST_UPDATES = 10

# Sign in stuff
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
if GOOGLE_CLIENT_ID is None: print('WARNING: No google client ID found!')

app = Flask(__name__)

# Secret key to sign cookies and maintain sessions
app.secret_key = os.environ.get('SESSION_SECRET', 'devkey')
if app.secret_key == 'devkey': print('WARNING: no secret key found, using default devkey')

# Emb key
EMB_KEY = os.getenv('OAI_KEY')
if EMB_KEY is None: print('WARNING: No embedding key!')

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
        user_id, is_new = db_utils.signin_user(get_db(), idinfo['email'], emb_dim = EMB_DIM)
        session['user_id'] = user_id
        session.permanent = True
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
    recs_info = {'N_PERSONAL': N_PERSONAL}
    try:
        if g.user:

            preferences = db_utils.get_preferences(db = db, user_id = g.user)
            events = db_utils.get_event_blobs_and_gen_info(db = db) # TODO should we just keep in memory?

            # Filter out by keywords
            recs_info['n_available'] = len(events)
            if preferences.get('keywordsToAvoid'):
                events = filter_events_by_keywords(events, preferences['keywordsToAvoid'])
            recs_info['n_filtered'] = recs_info['n_available'] - len(events)

            # Event embeddings
            E = np.array([e['emb'] for e in events])
            ids = np.array([e['id'] for e in events])

            user_emb = db_utils.get_user_emb(db = db, user_id = g.user)
            preds = E @ user_emb

            # Recommend events with highest predicted rating
            rec_ixs = (-preds).argsort()[:N_PERSONAL] # ix in current_events
            rec_ids = ids[rec_ixs].tolist()

            recommended_events = db_utils.get_events_by_ids(db = db, event_ids = rec_ids, user_id = g.user)
            recommended_events = sorted(recommended_events, key = lambda e: rec_ids.index(e['Id']))
            recommended_events = [format_event(e) for e in recommended_events]

            for e, og_ix in zip(recommended_events, rec_ixs):
                e['info'] = f'Ranked (starting at 0): {np.where(rec_ixs == og_ix)[0][0]}\\nCos similarity: {preds[og_ix]:.6f}'

    except Exception as e: print('error getting recs:', e)

    return render_template(
        'index.html', google_client_id = GOOGLE_CLIENT_ID,
        recommended_events = recommended_events, featured_events = featured_events, recs_info = recs_info
    )

@app.route('/vote', methods = ['PUT', 'POST'])
def vote():
    try:
        assert all([k in request.args for k in ('type', 'eventId', 'factor')])
        factor = float(request.args['factor'])
        assert factor in (-1., 1., 2.)
        db = get_db()
        db_utils.vote(db = db, user_id = g.user, event_id = request.args['eventId'], vote_type = request.args['type'])
        db_utils.update_user_interactions_emb(db = db, user_id = g.user, event_id = request.args['eventId'], rating = factor)
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
            return str_err("An error occurred. Please try again later.")
    
    if request.method == 'DELETE':
        try:
            db_utils.delete_user(db = db, user_id = g.user)
            session.pop('user_id', None)
            return 'Successfully deleted account. Close tab to exit.'
        except Exception as e:
            print(f'Error deleting account: {e}')
            return "An error occurred. Please <a href=\"mailto:emilio@mywolverine.events\">email support</a>."
    
    key, value = next(request.form.items())
    try:

        if key == 'interests':

            interest_list = lambda s: [i.strip().lower() for i in s.split(',')]
            interests = interest_list(value)

            if len(interests) > MAX_INTERESTS:
                return str_err(f'Error: Can only have {MAX_INTERESTS} or less interests')
            if max(map(len, interests)) > MAX_INTEREST_LEN:
                return str_err(f'Error: Interests must have length < {MAX_INTEREST_LEN}')
            
            prefs = db_utils.get_preferences(db = db, user_id = g.user)

            if prefs['daily_interest_updates'] >= MAX_DAILY_INTEREST_UPDATES:
                return str_err(f'Error: Reached max no. of daily interest updates. Please update tomorrow.')

            new_interests = set(interests) - set(interest_list(prefs['interests']) )  
            db_utils.update_interests_emb(
                db = db, user_id = g.user, new_interests = list(new_interests), interests_str = value,
                daily_interest_updates = prefs['daily_interest_updates'], emb_dim = EMB_DIM
            ) 
q
        db_utils.update_preference(db = db, user_id = g.user, pref_key = key, pref_value = value)
        return 'Saved'
    
    except Exception as e:
        print(f'Error updating interests: {e}')
        return str_err('An error occurred. Please try again or contact support.')


@app.route('/similar/<id>', methods = ['GET'])
def similar(id = None):

    if id is None: redirect(url_for('main'))

    db = get_db()
    if request.method == 'GET':
        try:

            events = db_utils.get_event_blobs_and_gen_info(db = db) # TODO should we just keep in memory?

            # Event embeddings
            E = np.array([e['emb'] for e in events])
            ids = np.array([e['id'] for e in events])

            event_ix = np.where(ids == int(id))[0][0] # in E
            event_emb = E[event_ix]

            preds = E @ event_emb

            # "Recommend" events with highest predicted rating
            rec_ixs = (-preds).argsort()[:N_PERSONAL] # ix in E
            rec_ids = ids[rec_ixs].tolist()
            
            events = db_utils.get_events_by_ids(db = db, event_ids = rec_ids, user_id = g.user)
            events = sorted(events, key = lambda e: rec_ids.index(e['Id']))
            events = [format_event(e) for e in events]

            for e, og_ix in zip(events, rec_ixs):
                if e['Id'] == int(id): e['highlight'] = True
                e['info'] = f'Ranked (starting at 0): {np.where(rec_ixs == og_ix)[0][0]}\\nCos similarity: {preds[og_ix]:.6f}'

            return render_template('similar.html', events = events)

        except Exception as e:
            print(f'Error getting simiar: {e}')
            return 'An error occurred. Please try again later.'
    
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
