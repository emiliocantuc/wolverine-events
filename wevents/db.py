import sqlite3, os
import numpy as np
from datetime import datetime

from scripts.utils import get_embedding

######################################### EVENTS #########################################
def get_events_where(db: sqlite3.Connection, where: str, user_id:int = None, trailing = '', *where_args):
    # Dynamically determine the UserVote part of the query
    user_vote_part = """,
        CASE 
            WHEN uv.vote_type = 'U' THEN 'U'
            WHEN uv.vote_type = 'D' THEN 'D'
            ELSE NULL
        END AS UserVote
    """ if user_id is not None else ""

    query = f"""
        SELECT 
            e.event_id AS Id,
            e.title AS Title,
            e.type AS EventType,
            e.event_description AS Description,
            e.event_start AS StartDate,
            e.event_end AS EndDate,
            COALESCE(SUM(CASE WHEN v.vote_type = 'U' THEN 1 ELSE 0 END), 0) - 
            COALESCE(SUM(CASE WHEN v.vote_type = 'D' THEN 1 ELSE 0 END), 0) AS VoteDiff,
            e.gcal_link AS CalendarLink,
            e.permalink AS PermaLink,
            e.building_name AS BuildingName{user_vote_part.rstrip()}
        FROM 
            events e
        LEFT JOIN 
            votes v ON e.event_id = v.event_id
        {"LEFT JOIN votes uv ON e.event_id = uv.event_id AND uv.user_id = ?" if user_id is not None else ""}
        WHERE
            {where}
        GROUP BY 
            e.event_id, e.title, e.event_description, e.event_start, e.event_end, e.gcal_link, e.permalink, e.building_name
        {trailing}
    """
    params = (*where_args,) if user_id is None else (user_id, *where_args)
    cursor = db.execute(query, params)
    results = cursor.fetchall()

    keys = ['Id', 'Title', 'EventType', 'Description', 'StartDate', 'EndDate', 'VoteDiff', 'CalendarLink', 'PermaLink', 'BuildingName']
    if user_id is not None: keys.append('UserVote')
    return [dict(zip(keys, row)) for row in results]

def get_events_by_ids(db: sqlite3.Connection, event_ids: list[int], user_id:int = None):
    return get_events_where(db, f"Id IN ({','.join('?' * len(event_ids))}) AND e.event_end > CURRENT_DATE", user_id, '', *event_ids)

def get_top_events(db, limit, user_id = None):
    trailing = """
        ORDER BY 
            VoteDiff DESC, RANDOM()
        LIMIT ?"""
    
    return get_events_where(db, "e.event_end > CURRENT_DATE", user_id, trailing, limit)

def get_event_blobs_and_gen_info(db: sqlite3.Connection):
    query = 'SELECT event_id, emb, title, event_description FROM events WHERE event_end > CURRENT_DATE'
    cursor = db.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    return [{'id': row[0], 'emb': np.frombuffer(row[1]), 'title': row[2], 'event_description': row[3]} for row in results]

########################################## USER ##########################################
def get_user_emb(db: sqlite3.Connection, user_id: int) -> dict:
    query = 'SELECT interests_emb, interactions_emb, alpha FROM users WHERE user_id = ?'
    cursor = db.execute(query, (user_id,))
    row = cursor.fetchone()
    interests_emb, interactions_emb, alpha = np.frombuffer(row[0]), np.frombuffer(row[1]), row[2]
    return (alpha) * interests_emb + (1-alpha) * interactions_emb

def update_user_interactions_emb(db: sqlite3.Connection, user_id: int, event_id: int, rating: float):
    """
    Update a user's interactions embedding based on an event's ratings.
    """
    assert rating in (1., -1., 2.)
    
    # Get event and weights
    event_row = db.execute('SELECT emb FROM events WHERE event_id = ?', (event_id,)).fetchone()
    if event_row is None: raise ValueError(f'Event ID {event_id} not found.')
    event_emb = np.frombuffer(event_row[0])

    # Get the user's interactions embedding and beta
    row = db.execute('SELECT interactions_emb, beta FROM users WHERE user_id = ?', (user_id,)).fetchone()
    if row is None: raise ValueError(f"User ID {user_id} not found.")
    interactions_emb, beta = np.frombuffer(row[0]), row[1]

    # Update emb
    interactions_emb = beta * interactions_emb + (1-beta) * (rating * event_emb)
    
    db.execute('UPDATE users SET interactions_emb = ? WHERE user_id = ?', (interactions_emb.tobytes(), user_id))
    db.commit()

    print(f'User {user_id}s ratings updated successfully.')


def update_interests_emb(db: sqlite3.Connection, user_id: int, new_interests: list[str], interests_str: str, daily_interest_updates: int, emb_dim: int):
    try:
        db.execute("BEGIN TRANSACTION")

        # Check which interests are not in the interests table TODO very inefficient
        db_interests = db.execute("SELECT interest FROM interests").fetchall()
        db_interests = {row[0] for row in db_interests}
        missing_interests = [interest for interest in new_interests if interest not in db_interests]

        # Embed missing interests
        new_embeddings = dict(zip(missing_interests, get_embedding(missing_interests, key = os.getenv('OAI_KEY'))))

        # Insert missing interests into the interests table
        for interest, emb in new_embeddings.items():
            db.execute(
                "INSERT INTO interests (interest, emb) VALUES (?, ?)",
                (interest, np.array(emb).tobytes())
            )

        # Retrieve embeddings for all user interests
        query = f"""
            SELECT emb
            FROM interests
            WHERE interest IN ({",".join("?" for _ in new_interests)})
        """
        embeddings = db.execute(query, new_interests).fetchall()
        embeddings = [np.frombuffer(row[0], dtype=np.float64) for row in embeddings]

        # Compute the average embedding and update
        if embeddings:
            average_embedding = np.mean(embeddings, axis=0)
            db.execute(
                "UPDATE users SET interests = ? ,interests_emb = ?, daily_interest_updates = ? WHERE user_id = ?",
                (interests_str, average_embedding.tobytes(), daily_interest_updates + 1, user_id)
            )

        db.commit()

    except Exception as e:
        db.rollback()  # Roll back the transaction in case of any failure
        raise Exception(f'Failed to update interests embeddings: {e}')


def get_preferences(db: sqlite3.Connection, user_id: int) -> dict:

    query = 'SELECT interests, keywordsToAvoid, daily_interest_updates FROM users WHERE user_id = ?'
    row = db.execute(query, (user_id,)).fetchone()
    if row is None: raise Exception(f'No preferences found for user_id {user_id}')
    interests, keywords_to_avoid, daily_interest_updates = row
    return {'interests': interests, 'keywordsToAvoid': keywords_to_avoid, 'daily_interest_updates': int(daily_interest_updates)}

def update_preference(db: sqlite3.Connection, user_id: int, pref_key: str, pref_value: str) -> None:
    if pref_key not in ['interests', 'keywordsToAvoid']: raise Exception(f'invalid preference key: {pref_key}')
    try:
        db.execute(f'UPDATE users SET {pref_key} = ? WHERE user_id = ?', (pref_value, user_id))
        db.commit()
    except sqlite3.Error as e: raise Exception(f'could not update preference {pref_key}: {e}')

def signin_user(db: sqlite3.Connection, email: str, emb_dim: int, unif_range: float = 1e-5) -> tuple[int, bool]:
    """
    Returns user_id given email for a user. If the user is new, adds the user and their ratings.
    Returns the user_id and a boolean indicating if the user is new.
    """
    
    # Check if the user already exists
    row = db.execute('SELECT user_id FROM users WHERE email = ?', (email,)).fetchone()
    if row: return row[0], False
    
    # If user doesn't exist, insert the new user
    interests_emb    = np.random.uniform(-unif_range, unif_range, size = emb_dim)
    interactions_emb = np.random.uniform(-unif_range, unif_range, size = emb_dim)

    cursor = db.execute(
        'INSERT INTO users (email, interests_emb, interactions_emb) VALUES (?, ?, ?)',
        (email, interests_emb.tobytes(), interactions_emb.tobytes())
    )
    user_id = cursor.lastrowid
    db.commit()
    
    print(f'New user {user_id} {email}')
    return user_id, True


def delete_user(db: sqlite3.Connection, user_id: int) -> None:
    # Delete from user and votes tables
    try:
        cursor = db.cursor()
        cursor.execute("BEGIN")
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM votes WHERE user_id = ?", (user_id,))
        db.commit()
    except sqlite3.Error as e:
        db.rollback()
        raise Exception(f"could not delete user: {e}")
    

def vote(db: sqlite3.Connection, user_id: int, event_id: int, vote_type: str) -> None:

    assert vote_type in ("U", "D", "C", "N")

    query = """
        INSERT INTO votes (user_id, event_id, vote_type, voted_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, event_id)
        DO UPDATE SET vote_type = excluded.vote_type, voted_at = excluded.voted_at
    """

    # Execute the query with the current timestamp
    db.execute(query, (user_id, event_id, vote_type, datetime.now()))
    db.commit()


def get_stats(db: sqlite3.Connection) -> dict:
    results = db.execute('SELECT nweek, nusers, nevents FROM statistics ORDER BY nweek LIMIT 5;').fetchall()
    if results is None: raise Exception(f"No statistics found.")
    return [dict(zip(['nweek', 'nusers', 'nevents'], row)) for row in results]

