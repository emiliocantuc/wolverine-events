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
from wevents.utils import format_event

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
if GOOGLE_CLIENT_ID is None: print('WARNING: No google client ID found!')

app = Flask(__name__)

# Secret key to sign cookies and maintain sessions
if 'SESSION_SECRET' in os.environ:
    sk = os.environ['SESSION_SECRET']
else:
    print('WARNING: no secret key found, using default devkey')
    sk = 'devkey'
app.secret_key = sk

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

@app.before_request
def load_logged_in_user():
    # g.user = 1#'emilio'#
    g.user = session.get('user_id', None)
    print('user id', g.user)

# Auth
@app.route('/login', methods = ['POST'])
def login():
    print(request.form)

    # Validate the token
    try:
        idinfo = id_token.verify_oauth2_token(request.form['credential'], requests.Request(), os.getenv('GOOGLE_CLIENT_ID'))
        user_id = db_utils.signin_user(get_db(), idinfo['email'])
        session['user_id'] = user_id
        print('singed in ', idinfo['email'], user_id)
    except ValueError as e:
        print('error validating', e)
        return 'Error logging in'
    
    return redirect(url_for('main'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('main'))


@app.route('/', methods = ['GET'])
def main():
    db = get_db()
    events = db_utils.get_top_events(db, 1, 20)
    events = [format_event(e) for e in events]
    return render_template('index.html', google_client_id = GOOGLE_CLIENT_ID, featured_events = events)

@app.route('/prefs', methods = ['GET', 'PUT', 'DELETE'])
def prefs():
    if not g.user: return 'Error: not logged in'
    
    db = get_db()
    if request.method == 'GET':
        try:
            prefs = db_utils.get_preferences(db, g.user)
            return render_template('prefs.html', prefs = prefs)
        except Exception as e:
            print(f'Error getting preferences: {e}')
            return "An error occurred. Please try again later."
    
    if request.method == 'DELETE':
        try:
            db_utils.delete_user(db, g.user)
            return 'Successfully deleted account. Close tab to exit.'
        except Exception as e:
            print(f'Error deleting account: {e}')
            return "An error occurred. Please <a href=\"mailto:emilio@mywolverine.events\">email support</a>."
    
    key, value = next(request.form.items())
    db_utils.update_preference(db, g.user, key, value)
    return 'Saved'
